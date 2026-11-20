"""异常与权限测试：不存在、无权限、非法状态与停用账号。"""

import pytest

from core import auth
from core.db import get_connection
from core.errors import BusinessError
from services import applications, companies, jobs, students
from tests.support import (
    make_admin,
    make_company,
    make_job,
    make_student,
    resume_payload,
)


def _verified_student(email="student@example.com") -> int:
    student_id = make_student(email)
    students.save_resume(student_id, resume_payload())
    applications_id = students.get_resume(student_id)["id"]
    students.review_resume(make_admin("admin@example.com"), applications_id, "VERIFIED")
    return student_id


def test_student_cannot_read_other_student_resume(db_path):
    """TC-E01：学生查看他人简历被拒绝。"""
    first = make_student("first@example.com")
    second = make_student("second@example.com")

    with pytest.raises(BusinessError) as exc_info:
        students.get_resume(first, student_id=second)

    assert exc_info.value.code == "FORBIDDEN"


def test_company_cannot_read_other_company_profile(db_path):
    """TC-E02：企业查看其他企业资料被拒绝。"""
    first = make_company("first@example.com", "A 公司")
    second = make_company("second@example.com", "B 公司")

    with pytest.raises(BusinessError) as exc_info:
        companies.get_profile(first, user_id=second)

    assert exc_info.value.code == "FORBIDDEN"


def test_review_nonexistent_records(db_path):
    """TC-E03：审核不存在的职位 / 企业 / 简历返回 NOT_FOUND。"""
    admin_id = make_admin()

    with pytest.raises(BusinessError) as exc_info:
        jobs.review_job(admin_id, 9999, "APPROVED")
    assert exc_info.value.code == "NOT_FOUND"

    with pytest.raises(BusinessError) as exc_info:
        companies.review_license(admin_id, 9999, "APPROVED")
    assert exc_info.value.code == "NOT_FOUND"

    with pytest.raises(BusinessError) as exc_info:
        students.review_resume(admin_id, 9999, "VERIFIED")
    assert exc_info.value.code == "NOT_FOUND"


def test_update_nonexistent_application(db_path):
    """TC-E04：处理不存在的投递返回 NOT_FOUND。"""
    company_id = make_company()

    with pytest.raises(BusinessError) as exc_info:
        applications.update_status(company_id, 9999, "VIEWED")

    assert exc_info.value.code == "NOT_FOUND"


def test_download_without_attachment(db_path):
    """TC-E05：无附件时下载返回 NOT_FOUND；学生无权下载返回 FORBIDDEN。"""
    student_id = _verified_student()
    company_id = make_company()
    job_id = make_job(company_id)
    application = applications.apply_to_job(student_id, job_id)

    with pytest.raises(BusinessError) as exc_info:
        applications.get_resume_file(company_id, application["id"])
    assert exc_info.value.code == "NOT_FOUND"

    with pytest.raises(BusinessError) as exc_info:
        applications.get_resume_file(student_id, application["id"])
    assert exc_info.value.code == "FORBIDDEN"


def test_apply_nonexistent_or_closed_job(db_path):
    """TC-E06：投递不存在或已关闭职位被拒绝。"""
    student_id = _verified_student()
    company_id = make_company()

    with pytest.raises(BusinessError) as exc_info:
        applications.apply_to_job(student_id, 9999)
    assert exc_info.value.code == "NOT_FOUND"

    closed_job = make_job(company_id, status="CLOSED")
    with pytest.raises(BusinessError) as exc_info:
        applications.apply_to_job(student_id, closed_job)
    assert exc_info.value.code == "JOB_NOT_OPEN"


def test_close_closed_job_is_invalid_state(db_path):
    """TC-E07：重复关闭职位返回 INVALID_STATE。"""
    company_id = make_company()
    job_id = make_job(company_id)

    jobs.close_job(company_id, job_id)

    with pytest.raises(BusinessError) as exc_info:
        jobs.close_job(company_id, job_id)
    assert exc_info.value.code == "INVALID_STATE"


def test_role_mismatch_is_forbidden(db_path):
    """TC-E08：跨角色调用服务被拒绝。"""
    student_id = make_student()
    company_id = make_company()

    with pytest.raises(BusinessError) as exc_info:
        jobs.create_job(student_id, {"title": "x"})
    assert exc_info.value.code == "FORBIDDEN"

    with pytest.raises(BusinessError) as exc_info:
        students.save_resume(company_id, resume_payload())
    assert exc_info.value.code == "FORBIDDEN"


def test_inactive_account_cannot_login(db_path):
    """TC-E09：账号停用后无法登录。"""
    student_id = make_student()
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (student_id,))

    with pytest.raises(BusinessError) as exc_info:
        auth.login("student@example.com", "Student123!")

    assert exc_info.value.code == "AUTH_INACTIVE"


def test_login_error_message_does_not_leak_account(db_path):
    """TC-E10：密码错误与账号不存在返回完全相同的提示。"""
    make_student()

    with pytest.raises(BusinessError) as wrong_password:
        auth.login("student@example.com", "WrongPass123!")
    with pytest.raises(BusinessError) as missing_account:
        auth.login("nobody@example.com", "WrongPass123!")

    assert wrong_password.value.message == missing_account.value.message
    assert wrong_password.value.code == missing_account.value.code
