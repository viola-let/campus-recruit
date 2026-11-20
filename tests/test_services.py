"""服务层测试：投递规则、越权、状态流转、审核权限（T-05 至 T-09）。"""

import json

import pytest

from core import auth
from core.config import now_iso
from core.db import get_connection
from core.errors import BusinessError
from services import admin, applications, companies, jobs, students

STUDENT_PASSWORD = "Student123!"
COMPANY_PASSWORD = "Company123!"
ADMIN_PASSWORD = "ChangeMe123"


def create_student(email="student@example.com", name="张三") -> int:
    return auth.register_student(email, STUDENT_PASSWORD, name)


def create_company(email="company@example.com", name="示例科技") -> int:
    user_id = auth.register_company(email, COMPANY_PASSWORD, name)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE companies
            SET name = ?, license_no = '91310000TEST0001X', hr_name = '李招聘',
                hr_email = 'hr@example.com', status = 'APPROVED',
                hr_status = 'APPROVED', updated_at = ?
            WHERE user_id = ?
            """,
            (name, now_iso(), user_id),
        )
    return user_id


def create_admin() -> int:
    return auth.create_admin("admin@example.com", ADMIN_PASSWORD, "平台管理员")


def create_job(company_user_id: int, status="APPROVED", title="Python 后端实习生"):
    with get_connection() as conn:
        company = conn.execute(
            "SELECT id FROM companies WHERE user_id = ?", (company_user_id,)
        ).fetchone()
        timestamp = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO jobs
                (company_id, title, job_type, city, salary, description,
                 requirements, status, is_featured, created_at, updated_at)
            VALUES (?, ?, 'INTERN', '上海', '200 元/天', ?, ?, ?, 0, ?, ?)
            """,
            (
                company["id"],
                title,
                "参与内部平台后端接口开发与测试，学习业务流程。",
                "熟悉 Python 基础，了解 SQL。",
                status,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.lastrowid)


def verify_resume(student_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE resumes SET status = 'VERIFIED', updated_at = ? "
            "WHERE student_id = ?",
            (now_iso(), student_id),
        )


def test_save_resume_sets_pending(db_path):
    student_id = create_student()

    resume = students.save_resume(
        student_id,
        {
            "real_name": "张三",
            "phone": "13800000000",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2027,
            "skills": "Python",
            "summary": "热爱后端开发",
        },
    )

    assert resume["status"] == "PENDING"
    assert resume["school"] == "示例大学"


def test_apply_rejected_when_resume_not_verified(db_path):
    """T-05：未核查简历投递必须被拒绝。"""
    student_id = create_student()
    students.save_resume(
        student_id,
        {
            "real_name": "张三",
            "phone": "13800000000",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2027,
        },
    )
    company_id = create_company()
    job_id = create_job(company_id)

    with pytest.raises(BusinessError) as exc_info:
        applications.apply_to_job(student_id, job_id)

    assert exc_info.value.code == "RESUME_NOT_VERIFIED"


def test_apply_saves_snapshot_and_rejects_duplicate(db_path):
    """T-06：正常投递保存快照，重复投递被拒绝。"""
    student_id = create_student()
    students.save_resume(
        student_id,
        {
            "real_name": "张三",
            "phone": "13800000000",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2027,
            "skills": "Python",
        },
    )
    verify_resume(student_id)
    company_id = create_company()
    job_id = create_job(company_id)

    application = applications.apply_to_job(student_id, job_id)

    assert application["status"] == "SUBMITTED"
    snapshot = json.loads(application["resume_snapshot"])
    assert snapshot["school"] == "示例大学"
    assert snapshot["phone"] == "13800000000"

    with pytest.raises(BusinessError) as exc_info:
        applications.apply_to_job(student_id, job_id)

    assert exc_info.value.code == "DUPLICATE_APPLICATION"


def _prepare_application(student_id: int, company_id: int) -> int:
    """准备一条已投递记录，返回投递 ID。"""
    students.save_resume(
        student_id,
        {
            "real_name": "张三",
            "phone": "13800000000",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2027,
        },
    )
    verify_resume(student_id)
    job_id = create_job(company_id)
    application = applications.apply_to_job(student_id, job_id)
    return int(application["id"])


def test_company_cannot_access_other_company_application(db_path):
    """T-07：企业不能查看或处理其他公司职位的投递。"""
    student_id = create_student()
    company_a = create_company("company_a@example.com", "A 公司")
    company_b = create_company("company_b@example.com", "B 公司")
    application_id = _prepare_application(student_id, company_a)

    with pytest.raises(BusinessError) as exc_info:
        applications.update_status(company_b, application_id, "VIEWED", "尝试越权")
    assert exc_info.value.code == "FORBIDDEN"

    assert applications.list_job_candidates(company_b) == []
    assert len(applications.list_job_candidates(company_a)) == 1


def test_invalid_application_status_transition(db_path):
    """T-08：不允许跳过中间状态或修改终态。"""
    student_id = create_student()
    company_id = create_company()
    application_id = _prepare_application(student_id, company_id)

    with pytest.raises(BusinessError) as exc_info:
        applications.update_status(company_id, application_id, "HIRED", "直接录用")
    assert exc_info.value.code == "INVALID_STATE"

    applications.update_status(company_id, application_id, "VIEWED")
    applications.update_status(company_id, application_id, "SHORTLISTED")
    applications.update_status(company_id, application_id, "HIRED")

    with pytest.raises(BusinessError) as exc_info:
        applications.update_status(company_id, application_id, "REJECTED", "反悔")
    assert exc_info.value.code == "INVALID_STATE"


def test_reject_requires_feedback(db_path):
    student_id = create_student()
    company_id = create_company()
    application_id = _prepare_application(student_id, company_id)

    with pytest.raises(BusinessError) as exc_info:
        applications.update_status(company_id, application_id, "REJECTED", "")

    assert exc_info.value.code == "VALIDATION_ERROR"


def test_non_admin_cannot_review(db_path):
    """T-09：非管理员调用审核一律拒绝。"""
    student_id = create_student()
    company_id = create_company()
    job_id = create_job(company_id, status="PENDING")
    students.save_resume(
        student_id,
        {
            "real_name": "张三",
            "phone": "13800000000",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2027,
        },
    )
    resume = students.get_resume(student_id)
    profile = companies.get_profile(company_id)

    with pytest.raises(BusinessError) as exc_info:
        jobs.review_job(student_id, job_id, "APPROVED")
    assert exc_info.value.code == "FORBIDDEN"

    with pytest.raises(BusinessError) as exc_info:
        companies.review_license(student_id, profile["id"], "APPROVED")
    assert exc_info.value.code == "FORBIDDEN"

    with pytest.raises(BusinessError) as exc_info:
        students.review_resume(student_id, resume["id"], "VERIFIED")
    assert exc_info.value.code == "FORBIDDEN"


def test_review_only_handles_pending(db_path):
    """T-09：已处理的记录不能被二次审核覆盖。"""
    admin_id = create_admin()
    company_id = create_company()
    job_id = create_job(company_id, status="PENDING")

    reviewed = jobs.review_job(admin_id, job_id, "APPROVED")
    assert reviewed["status"] == "APPROVED"

    with pytest.raises(BusinessError) as exc_info:
        jobs.review_job(admin_id, job_id, "REJECTED", "重复审核")
    assert exc_info.value.code == "INVALID_STATE"


def test_company_license_review_requires_note_on_reject(db_path):
    admin_id = create_admin()
    company_user_id = auth.register_company(
        "pending@example.com", COMPANY_PASSWORD, "待审公司"
    )
    profile = companies.get_profile(admin_id, company_user_id)

    with pytest.raises(BusinessError) as exc_info:
        companies.review_license(admin_id, profile["id"], "REJECTED", "")
    assert exc_info.value.code == "VALIDATION_ERROR"

    reviewed = companies.review_license(admin_id, profile["id"], "APPROVED")
    assert reviewed["status"] == "APPROVED"
    assert reviewed["hr_status"] == "PENDING"


def test_dashboard_counts(db_path):
    admin_id = create_admin()
    create_student()
    company_id = create_company()
    create_job(company_id, status="PENDING")

    counts = admin.dashboard_counts(admin_id)

    assert counts["pending_jobs"] == 1
    assert counts["pending_company_license"] == 0
    assert counts["total_applications"] == 0


def _job_payload(title="Python 后端工程师"):
    return {
        "title": title,
        "job_type": "CAMPUS",
        "city": "杭州",
        "salary": "20-30K",
        "description": "负责校招平台后端接口开发、测试与日常维护工作。",
        "requirements": "熟悉 Python 与 SQL",
    }


def test_search_jobs_only_approved_and_featured_first(db_path):
    company_id = create_company()
    normal_id = create_job(company_id, status="APPROVED", title="普通职位")
    featured_id = create_job(company_id, status="APPROVED", title="推荐职位")
    create_job(company_id, status="PENDING", title="待审职位")
    admin_id = create_admin()
    jobs.set_featured(admin_id, featured_id, True)

    results = jobs.search_jobs()

    titles = [item["title"] for item in results]
    assert "待审职位" not in titles
    assert titles[0] == "推荐职位"
    assert {item["id"] for item in results} == {normal_id, featured_id}


def test_save_resume_resets_verified_to_pending(db_path):
    student_id = create_student()
    payload = {
        "real_name": "张三",
        "phone": "13800000000",
        "school": "示例大学",
        "major": "计算机科学与技术",
        "graduation_year": 2027,
    }
    students.save_resume(student_id, payload)
    verify_resume(student_id)

    resume = students.save_resume(student_id, {**payload, "skills": "Python"})

    assert resume["status"] == "PENDING"


def test_attach_resume_file_saves_and_resets_status(db_path, tmp_path, monkeypatch):
    student_id = create_student()
    students.save_resume(
        student_id,
        {
            "real_name": "张三",
            "phone": "13800000000",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2027,
        },
    )
    verify_resume(student_id)
    monkeypatch.setattr("core.security.BASE_DIR", tmp_path)
    monkeypatch.setattr("services.students.RESUME_UPLOAD_DIR", tmp_path / "resumes")

    relative = students.attach_resume_file(student_id, "我的简历.PDF", b"pdf")

    assert relative.startswith("resumes/")
    assert relative.endswith(".pdf")
    assert (tmp_path / relative).is_file()
    assert students.get_resume(student_id)["status"] == "PENDING"


def test_create_job_requires_approved_company(db_path):
    company_user_id = auth.register_company(
        "unapproved@example.com", COMPANY_PASSWORD, "未审核公司"
    )

    with pytest.raises(BusinessError) as exc_info:
        jobs.create_job(company_user_id, _job_payload())

    assert exc_info.value.code == "FORBIDDEN"


def test_company_job_lifecycle(db_path):
    admin_id = create_admin()
    company_id = create_company()
    other_company = create_company("other_company@example.com", "其他公司")

    job = jobs.create_job(company_id, _job_payload())
    assert job["status"] == "PENDING"

    jobs.review_job(admin_id, job["id"], "APPROVED")
    updated = jobs.update_job(
        company_id, job["id"], _job_payload("Python 后端工程师（更新）")
    )
    assert updated["status"] == "PENDING"

    jobs.review_job(admin_id, job["id"], "APPROVED")
    jobs.close_job(company_id, job["id"])
    assert jobs.list_company_jobs(company_id)[0]["status"] == "CLOSED"

    reopened = jobs.reopen_job(company_id, job["id"])
    assert reopened["status"] == "PENDING"

    with pytest.raises(BusinessError) as exc_info:
        jobs.close_job(other_company, job["id"])
    assert exc_info.value.code == "FORBIDDEN"


def test_set_featured_requires_approved_job(db_path):
    admin_id = create_admin()
    company_id = create_company()
    pending_job = create_job(company_id, status="PENDING")

    with pytest.raises(BusinessError) as exc_info:
        jobs.set_featured(admin_id, pending_job, True)

    assert exc_info.value.code == "INVALID_STATE"


def test_review_resume_verified(db_path):
    admin_id = create_admin()
    student_id = create_student()
    resume = students.save_resume(
        student_id,
        {
            "real_name": "张三",
            "phone": "13800000000",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2027,
        },
    )

    reviewed = students.review_resume(admin_id, resume["id"], "VERIFIED")

    assert reviewed["status"] == "VERIFIED"
    assert len(students.list_pending_resumes(admin_id)) == 0
