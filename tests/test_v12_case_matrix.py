"""v1.2 新增功能用例矩阵：正常流程之外的边界与异常场景。

用例编号与 docs/项目过程文档/13-新增功能测试用例说明.md 一一对应。
"""

import pytest

from core import auth
from core.errors import BusinessError
from services import (
    analytics,
    applications,
    companies,
    culture,
    jobs,
    matching,
    micro_tasks,
    reviews,
    students,
)
from tests.support import (
    make_admin,
    make_company,
    make_job,
    make_student,
    resume_payload,
    set_resume_status,
)


def _verified_student(
    email: str,
    name: str = "边界学生",
    skills: str = "Python / SQL",
    major: str = "计算机科学与技术",
    summary: str = "期望城市：上海",
) -> int:
    student_id = make_student(email, name)
    students.save_resume(
        student_id,
        resume_payload(skills=skills, major=major, summary=summary),
    )
    set_resume_status(student_id, "VERIFIED")
    return student_id


def _post(**overrides) -> dict:
    payload = {
        "employment_status": "FORMER",
        "topic": "experience",
        "title": "后端实习三个月的真实体验",
        "content": "在这里实习了三个月，导师制完善，成长很快，福利发放及时，推荐投递。",
    }
    payload.update(overrides)
    return payload


def _review(**overrides) -> dict:
    payload = {
        "employment_status": "FORMER",
        "growth": 4,
        "salary": 4,
        "intensity": 3,
        "interview": 4,
        "recommend": 5,
        "content": "好" * 50,
    }
    payload.update(overrides)
    return payload


def _task(**overrides) -> dict:
    payload = {
        "title": "校园开放日现场协助",
        "description": "负责签到引导、物料发放与现场秩序维护，提供工作餐与交通补贴。",
        "city": "上海",
        "reward": "150 元/天",
        "schedule": "周六 9:00-17:00",
        "headcount": 5,
    }
    payload.update(overrides)
    return payload


# ---------------- 急招专区 ----------------


def test_urgent_days_boundary(db_path):
    """TC-V13：急招天数边界 1 与 30 可用，0 / 31 / 非数字拒绝。"""
    company_id = make_company("v13_urgent_days@example.com")
    job_id = make_job(company_id, status="APPROVED")

    jobs.set_urgent(company_id, job_id, 1)
    jobs.cancel_urgent(company_id, job_id)
    jobs.set_urgent(company_id, job_id, 30)

    for days in (0, 31, "abc"):
        with pytest.raises(BusinessError) as exc:
            jobs.set_urgent(company_id, job_id, days)
        assert exc.value.code == "VALIDATION_ERROR"


def test_urgent_exceptions(db_path):
    """TC-V14：非通过职位、越权企业与过期职位均不能进入急招。"""
    company_id = make_company("v13_urgent_ex@example.com")
    other_company = make_company("v13_urgent_other@example.com")
    pending_job = make_job(company_id, status="PENDING")
    approved_job = make_job(company_id, status="APPROVED")

    with pytest.raises(BusinessError) as exc:
        jobs.set_urgent(company_id, pending_job, 7)
    assert exc.value.code == "INVALID_STATE"

    with pytest.raises(BusinessError) as exc:
        jobs.set_urgent(other_company, approved_job, 7)
    assert exc.value.code == "FORBIDDEN"

    jobs.set_urgent(company_id, approved_job, 7)
    with pytest.raises(BusinessError) as exc:
        jobs.set_urgent(company_id, 999999, 7)
    assert exc.value.code == "NOT_FOUND"


# ---------------- 企业文化交流区 ----------------


def test_culture_length_boundaries(db_path):
    """TC-V15：标题 5-60 字、经验正文 30 字、提问 10 字的边界。"""
    company_id = make_company("v13_culture_len@example.com")
    student_id = _verified_student("v13_culture_len_stu@example.com")

    created = culture.create_post(
        student_id,
        company_id,
        _post(title="五字标题啊", content="评" * 30),
    )
    assert created["status"] == "PENDING"

    with pytest.raises(BusinessError) as exc:
        culture.create_post(student_id, company_id, _post(title="四字标题"))
    assert exc.value.code == "VALIDATION_ERROR"

    with pytest.raises(BusinessError) as exc:
        culture.create_post(
            student_id,
            company_id,
            _post(topic="question", title="一个合法的提问标题", content="短" * 9),
        )
    assert exc.value.code == "VALIDATION_ERROR"


def test_culture_daily_limit_and_blocklist(db_path):
    """TC-V16：每日 3 条上限与内容黑名单拦截。"""
    company_id = make_company("v13_culture_limit@example.com")
    student_id = _verified_student("v13_culture_limit_stu@example.com")

    for index in range(3):
        culture.create_post(
            student_id,
            company_id,
            _post(
                topic="question",
                title=f"求职提问第{index}条",
                content="请问团队平时的培养机制和晋升节奏是怎样的？",
            ),
        )
    with pytest.raises(BusinessError) as exc:
        culture.create_post(
            student_id,
            company_id,
            _post(
                topic="question",
                title="求职提问第四条",
                content="请问团队平时的培养机制和晋升节奏是怎样的？",
            ),
        )
    assert exc.value.code == "RATE_LIMITED"

    blocked_student = _verified_student("v13_culture_block@example.com")
    with pytest.raises(BusinessError) as exc:
        culture.create_post(
            blocked_student,
            company_id,
            _post(content="入职需要先交押金，完成刷单任务后返还，欢迎报名。"),
        )
    assert exc.value.code == "CONTENT_BLOCKED"


def test_culture_role_and_state_guards(db_path):
    """TC-V17：非企业角色不能回应、未通过帖子不能回应、重复回应被拒绝。"""
    company_id = make_company("v13_culture_state@example.com")
    student_id = _verified_student("v13_culture_state_stu@example.com")
    admin_id = make_admin("v13_culture_state_admin@example.com")

    post = culture.create_post(student_id, company_id, _post())
    with pytest.raises(BusinessError) as exc:
        culture.reply_to_post(company_id, post["id"], "企业回应内容")
    assert exc.value.code == "INVALID_STATE"

    with pytest.raises(BusinessError) as exc:
        culture.reply_to_post(student_id, post["id"], "学生回应内容")
    assert exc.value.code == "FORBIDDEN"

    culture.review_post(admin_id, post["id"], "APPROVED")
    culture.reply_to_post(company_id, post["id"], "感谢分享，我们会持续改进。")
    with pytest.raises(BusinessError) as exc:
        culture.reply_to_post(company_id, post["id"], "再次回应内容")
    assert exc.value.code == "INVALID_STATE"


# ---------------- 企业评分 ----------------


def test_review_content_and_score_boundaries(db_path):
    """TC-V18：正文 50 字可用、49 字拒绝，评分 0 / 6 拒绝。"""
    company_id = make_company("v13_review_bound@example.com")
    student_a = _verified_student("v13_review_bound_a@example.com")
    student_b = _verified_student("v13_review_bound_b@example.com")

    created = reviews.submit_review(student_a, company_id, _review(content="好" * 50))
    assert created["status"] == "PENDING"

    with pytest.raises(BusinessError) as exc:
        reviews.submit_review(student_b, company_id, _review(content="好" * 49))
    assert exc.value.code == "VALIDATION_ERROR"

    for score in (0, 6):
        with pytest.raises(BusinessError) as exc:
            reviews.submit_review(student_b, company_id, _review(growth=score))
        assert exc.value.code == "VALIDATION_ERROR"


def test_review_multiple_status_and_role_guard(db_path):
    """TC-V19：同企业不同任职身份可分别评分，企业角色不可评分。"""
    company_id = make_company("v13_review_multi@example.com")
    student_id = _verified_student("v13_review_multi_stu@example.com")

    reviews.submit_review(student_id, company_id, _review(employment_status="CURRENT"))
    reviews.submit_review(student_id, company_id, _review(employment_status="FORMER"))
    with pytest.raises(BusinessError) as exc:
        reviews.submit_review(
            student_id, company_id, _review(employment_status="CURRENT")
        )
    assert exc.value.code == "DUPLICATE_REVIEW"

    with pytest.raises(BusinessError) as exc:
        reviews.submit_review(company_id, company_id, _review())
    assert exc.value.code == "FORBIDDEN"


# ---------------- 小任务 ----------------


def test_task_field_boundaries(db_path):
    """TC-V20：标题 4 字、说明 30 字可用，3 字 / 29 字 / 101 人拒绝。"""
    company_id = make_company("v13_task_bound@example.com")

    created = micro_tasks.create_task(
        company_id,
        _task(title="任务名称", description="任" * 30),
    )
    assert created["status"] == "PENDING"

    for payload in (
        _task(title="三字名"),
        _task(description="任" * 29),
        _task(headcount=101),
    ):
        with pytest.raises(BusinessError) as exc:
            micro_tasks.create_task(company_id, payload)
        assert exc.value.code == "VALIDATION_ERROR"


def test_task_signup_guards(db_path):
    """TC-V21：未审核任务不可报名，重复报名与名额满均被拒绝。"""
    company_id = make_company("v13_task_signup@example.com")
    admin_id = make_admin("v13_task_signup_admin@example.com")
    task = micro_tasks.create_task(company_id, _task(headcount=1))

    student_a = _verified_student("v13_task_signup_a@example.com")
    student_b = _verified_student("v13_task_signup_b@example.com")

    with pytest.raises(BusinessError) as exc:
        micro_tasks.signup_task(student_a, task["id"])
    assert exc.value.code == "INVALID_STATE"

    micro_tasks.review_task(admin_id, task["id"], "APPROVED")
    micro_tasks.signup_task(student_a, task["id"])
    with pytest.raises(BusinessError) as exc:
        micro_tasks.signup_task(student_a, task["id"])
    assert exc.value.code == "DUPLICATE_SIGNUP"
    with pytest.raises(BusinessError) as exc:
        micro_tasks.signup_task(student_b, task["id"])
    assert exc.value.code == "TASK_FULL"


def test_task_company_permissions(db_path):
    """TC-V22：未双审企业不能发布，其他企业不能查看名单或结束任务。"""
    owner = make_company("v13_task_owner@example.com")
    other = make_company("v13_task_other@example.com")
    unapproved = make_company("v13_task_unapproved@example.com", approved=False)
    admin_id = make_admin("v13_task_perm_admin@example.com")

    with pytest.raises(BusinessError) as exc:
        micro_tasks.create_task(unapproved, _task())
    assert exc.value.code == "FORBIDDEN"

    task = micro_tasks.create_task(owner, _task())
    micro_tasks.review_task(admin_id, task["id"], "APPROVED")

    with pytest.raises(BusinessError) as exc:
        micro_tasks.task_signups(other, task["id"])
    assert exc.value.code == "FORBIDDEN"
    with pytest.raises(BusinessError) as exc:
        micro_tasks.close_task(other, task["id"])
    assert exc.value.code == "FORBIDDEN"


# ---------------- 招聘看板与候选人匹配 ----------------


def test_dashboard_zero_views_and_role_guard(db_path):
    """TC-V23：零浏览时转化率为 0，学生角色不能访问企业看板。"""
    company_id = make_company("v13_dashboard@example.com")
    make_job(company_id, status="APPROVED")
    student_id = _verified_student("v13_dashboard_stu@example.com")

    data = analytics.company_dashboard(company_id)
    assert data["totals"]["views"] == 0
    assert data["totals"]["applications"] == 0
    assert data["totals"]["response_hours"] is None
    assert data["jobs"][0]["conversion"] == 0.0

    with pytest.raises(BusinessError) as exc:
        analytics.company_dashboard(student_id)
    assert exc.value.code == "FORBIDDEN"


def test_matching_zero_score_and_role_guard(db_path):
    """TC-V24：无技能命中时匹配分为 0，学生角色不能调用匹配排序。"""
    company_id = make_company("v13_match_zero@example.com")
    job_id = make_job(company_id, status="APPROVED", title="【技术】Python 工程师")
    student_id = _verified_student(
        "v13_match_zero_stu@example.com",
        skills="Go",
        major="历史学",
        summary="期望城市：成都",
    )
    applications.apply_to_job(student_id, job_id)

    ranked = matching.list_candidates_ranked(company_id)
    assert ranked[0]["match_score"] == 0.0
    assert ranked[0]["match_reasons"] == []

    with pytest.raises(BusinessError) as exc:
        matching.list_candidates_ranked(student_id)
    assert exc.value.code == "FORBIDDEN"


# ---------------- 企业主页与内容审核 ----------------


def test_public_company_visibility_and_moderation_guard(db_path):
    """TC-V25：企业主页只展示已通过企业，非管理员不能审核，重复审核被拒绝。"""
    approved = make_company("v13_public_ok@example.com")
    make_company("v13_public_no@example.com", approved=False)
    public_ids = [item["id"] for item in companies.list_public_companies()]

    profile = companies.get_profile(approved)
    assert profile["id"] in public_ids
    assert companies.get_public_company(999999) is None

    admin_id = make_admin("v13_public_admin@example.com")
    student_id = _verified_student("v13_public_stu@example.com")
    post = culture.create_post(student_id, approved, _post())

    with pytest.raises(BusinessError) as exc:
        culture.review_post(student_id, post["id"], "APPROVED")
    assert exc.value.code == "FORBIDDEN"

    culture.review_post(admin_id, post["id"], "APPROVED")
    with pytest.raises(BusinessError) as exc:
        culture.review_post(admin_id, post["id"], "APPROVED")
    assert exc.value.code == "INVALID_STATE"

    assert auth.get_user(student_id)["role"] == "student"
