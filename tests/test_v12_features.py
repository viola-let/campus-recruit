"""v1.2 新增功能测试：急招、文化社区、企业评分、小任务、看板与候选人匹配。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api.main import app
from core import auth
from core.db import get_connection
from core.errors import BusinessError
from services import (
    analytics,
    applications,
    culture,
    jobs,
    matching,
    micro_tasks,
    recommendations,
    reviews,
    students,
)
from tests.support import (
    STUDENT_PASSWORD,
    make_admin,
    make_company,
    make_job,
    make_student,
    resume_payload,
    set_resume_status,
)

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _verified_student(
    email: str,
    name: str = "测试学生",
    skills: str = "Python / SQL",
    major: str = "计算机科学与技术",
    summary: str = "期望城市：上海，热爱后端开发",
) -> int:
    student_id = make_student(email, name)
    students.save_resume(
        student_id,
        resume_payload(skills=skills, major=major, summary=summary),
    )
    set_resume_status(student_id, "VERIFIED")
    return student_id


def _post_payload(**overrides) -> dict:
    payload = {
        "employment_status": "FORMER",
        "topic": "experience",
        "title": "后端实习三个月的真实体验",
        "content": (
            "在这里实习了三个月，导师制完善，成长很快，福利发放也很及时。"
            "团队氛围开放，日常沟通顺畅，推荐学弟学妹投递。"
        ),
    }
    payload.update(overrides)
    return payload


def _review_payload(**overrides) -> dict:
    payload = {
        "employment_status": "FORMER",
        "growth": 4,
        "salary": 4,
        "intensity": 3,
        "interview": 4,
        "recommend": 5,
        "content": (
            "实习三个月，导师负责、项目节奏合理，福利发放及时，面试流程清晰。"
            "团队沟通顺畅，转正机制透明，整体体验不错，推荐同学投递简历。"
        ),
    }
    payload.update(overrides)
    return payload


def test_urgent_job_flow_and_expiry(db_path):
    """TC-V01：急招设置后可被专区检索，过期后自动失效。"""
    company_id = make_company("v12_urgent@example.com")
    job_id = make_job(company_id, status="APPROVED")

    jobs.set_urgent(company_id, job_id, 7)
    result = jobs.search_jobs(only_urgent=True)
    assert [item["id"] for item in result] == [job_id]
    assert result[0]["urgent_until"]

    with get_connection() as conn:
        conn.execute(
            "UPDATE jobs SET urgent_until = '2000-01-01' WHERE id = ?", (job_id,)
        )
    assert jobs.search_jobs(only_urgent=True) == []


def test_urgent_ratio_is_capped(db_path):
    """TC-V02：急招岗位不超过在招岗位的 30%。"""
    company_id = make_company("v12_urgent_cap@example.com")
    job_ids = [
        make_job(company_id, title=f"急招候选岗位 {index}", status="APPROVED")
        for index in range(4)
    ]
    jobs.set_urgent(company_id, job_ids[0], 7)
    with pytest.raises(BusinessError) as exc:
        jobs.set_urgent(company_id, job_ids[1], 7)
    assert exc.value.code == "URGENT_LIMIT"


def test_culture_post_review_and_company_reply(db_path):
    """TC-V03：文化帖先审后发、匿名脱敏，企业可官方回应一次。"""
    company_id = make_company("v12_culture@example.com")
    student_id = _verified_student("v12_culture_stu@example.com")
    admin_id = make_admin("v12_culture_admin@example.com")

    post = culture.create_post(student_id, company_id, _post_payload())
    assert post["status"] == "PENDING"
    assert post["is_verified"] == 1
    assert culture.list_company_posts(company_id) == []

    culture.review_post(admin_id, post["id"], "APPROVED")
    posts = culture.list_company_posts(company_id)
    assert len(posts) == 1
    assert posts[0]["author_name"] == "匿名用户"

    culture.reply_to_post(company_id, post["id"], "感谢分享，我们会持续完善导师制。")
    posts = culture.list_company_posts(company_id)
    assert "感谢分享" in posts[0]["official_reply"]
    with pytest.raises(BusinessError) as exc:
        culture.reply_to_post(company_id, post["id"], "再次回应内容")
    assert exc.value.code == "INVALID_STATE"


def test_culture_rules_for_unverified_and_repeat_posts(db_path):
    """TC-V04：未任职只能提问；同企业 7 天内经验帖去重。"""
    company_id = make_company("v12_culture_rules@example.com")
    unverified = make_student("v12_culture_unverified@example.com")

    with pytest.raises(BusinessError) as exc:
        culture.create_post(
            unverified,
            company_id,
            _post_payload(employment_status="NONE", topic="experience"),
        )
    assert exc.value.code == "FORBIDDEN"

    question = culture.create_post(
        unverified,
        company_id,
        _post_payload(
            employment_status="NONE",
            topic="question",
            title="想了解团队日常氛围",
            content="请问团队平时加班多吗？新人培养机制是怎样的？",
        ),
    )
    assert question["topic"] == "question"
    assert question["is_verified"] == 0

    verified = _verified_student("v12_culture_repeat@example.com")
    culture.create_post(verified, company_id, _post_payload())
    with pytest.raises(BusinessError) as exc:
        culture.create_post(verified, company_id, _post_payload())
    assert exc.value.code == "DUPLICATE_CONTENT"


def test_review_sample_threshold_and_duplicate(db_path):
    """TC-V05：评分先审后发，样本满 3 条才展示数值，同身份不可重复。"""
    company_id = make_company("v12_review@example.com")
    admin_id = make_admin("v12_review_admin@example.com")
    first_student = _verified_student("v12_review_1@example.com")
    summary = reviews.rating_summary(company_id)
    assert summary["count"] == 0 and summary["reliable"] is False

    first_review = reviews.submit_review(first_student, company_id, _review_payload())
    reviews.review_review(admin_id, first_review["id"], "APPROVED")
    summary = reviews.rating_summary(company_id)
    assert summary["count"] == 1 and summary["reliable"] is False

    for index in (2, 3):
        student_id = _verified_student(f"v12_review_{index}@example.com")
        item = reviews.submit_review(student_id, company_id, _review_payload())
        reviews.review_review(admin_id, item["id"], "APPROVED")
        summary = reviews.rating_summary(company_id)
        if index < 3:
            assert summary["reliable"] is False

    assert summary["count"] == 3
    assert summary["reliable"] is True
    assert summary["average"] is not None
    assert 0 <= summary["recommend_rate"] <= 100

    with pytest.raises(BusinessError) as exc:
        reviews.submit_review(first_student, company_id, _review_payload())
    assert exc.value.code == "DUPLICATE_REVIEW"


def test_review_requires_verified_resume(db_path):
    """TC-V06：未核查简历不能评分，任职身份必须合法。"""
    company_id = make_company("v12_review_gate@example.com")
    student_id = make_student("v12_review_gate_stu@example.com")

    with pytest.raises(BusinessError) as exc:
        reviews.submit_review(student_id, company_id, _review_payload())
    assert exc.value.code == "RESUME_REQUIRED"

    verified = _verified_student("v12_review_gate_ok@example.com")
    with pytest.raises(BusinessError) as exc:
        reviews.submit_review(
            verified, company_id, _review_payload(employment_status="NONE")
        )
    assert exc.value.code == "FORBIDDEN"

    with pytest.raises(BusinessError) as exc:
        reviews.submit_review(verified, company_id, _review_payload(content="太短"))
    assert exc.value.code == "VALIDATION_ERROR"


def test_micro_task_flow_and_content_guard(db_path):
    """TC-V07：小任务关键词拦截、先审后发、报名去重与名额限制。"""
    company_id = make_company("v12_task@example.com")
    admin_id = make_admin("v12_task_admin@example.com")

    with pytest.raises(BusinessError) as exc:
        micro_tasks.create_task(
            company_id,
            {
                "title": "轻松兼职",
                "description": "刷单任务，日结高薪，无需经验，欢迎报名参加。",
                "city": "上海",
                "headcount": 5,
            },
        )
    assert exc.value.code == "CONTENT_BLOCKED"

    task = micro_tasks.create_task(
        company_id,
        {
            "title": "校园开放日现场协助",
            "description": (
                "负责签到引导、物料发放与现场秩序维护，提供工作餐与交通补贴，"
                "需提前半小时到场参加简短培训。"
            ),
            "city": "上海",
            "reward": "150 元/天",
            "schedule": "11 月 25 日 9:00-17:00",
            "headcount": 1,
        },
    )
    assert task["status"] == "PENDING"
    assert micro_tasks.list_open_tasks() == []

    micro_tasks.review_task(admin_id, task["id"], "APPROVED")
    assert len(micro_tasks.list_open_tasks()) == 1

    student_id = _verified_student("v12_task_stu@example.com")
    micro_tasks.signup_task(student_id, task["id"])
    with pytest.raises(BusinessError) as exc:
        micro_tasks.signup_task(student_id, task["id"])
    assert exc.value.code == "DUPLICATE_SIGNUP"

    second_student = _verified_student("v12_task_stu2@example.com")
    with pytest.raises(BusinessError) as exc:
        micro_tasks.signup_task(second_student, task["id"])
    assert exc.value.code == "TASK_FULL"


def test_company_dashboard_counts_views_and_applications(db_path):
    """TC-V08：看板统计去重浏览、投递数与转化率。"""
    company_id = make_company("v12_analytics@example.com")
    job_id = make_job(company_id, status="APPROVED")
    student_id = _verified_student("v12_analytics_stu@example.com")

    assert analytics.record_job_view(student_id, job_id) is True
    assert analytics.record_job_view(student_id, job_id) is False
    applications.apply_to_job(student_id, job_id)

    data = analytics.company_dashboard(company_id)
    assert data["totals"]["views"] == 1
    assert data["totals"]["applications"] == 1
    row = data["jobs"][0]
    assert row["conversion"] == 100.0


def test_candidates_ranked_by_skill_match(db_path):
    """TC-V09：候选人按技能命中排序，并返回可解释理由。"""
    company_id = make_company("v12_match@example.com")
    job_id = make_job(company_id, title="【技术】Python 后端工程师", status="APPROVED")
    python_student = _verified_student("v12_match_py@example.com", "Python同学")
    java_student = _verified_student(
        "v12_match_java@example.com",
        "Java同学",
        skills="Java / Spring",
    )
    applications.apply_to_job(python_student, job_id)
    applications.apply_to_job(java_student, job_id)

    ranked = matching.list_candidates_ranked(company_id)
    assert ranked[0]["student_id"] == python_student
    assert ranked[0]["match_score"] > ranked[1]["match_score"]
    assert any("技能匹配" in reason for reason in ranked[0]["match_reasons"])


def test_recommendation_uses_company_rating(db_path):
    """TC-V10：企业口碑达到样本门槛后进入推荐理由。"""
    company_id = make_company("v12_reco@example.com")
    job_id = make_job(company_id, title="【技术】Python 后端工程师", status="APPROVED")
    admin_id = make_admin("v12_reco_admin@example.com")
    for index in range(3):
        reviewer = _verified_student(f"v12_reco_reviewer{index}@example.com")
        item = reviews.submit_review(reviewer, company_id, _review_payload())
        reviews.review_review(admin_id, item["id"], "APPROVED")

    student_id = _verified_student("v12_reco_student@example.com")
    results = recommendations.recommend_jobs(student_id, limit=10)
    target = next(item for item in results if item["id"] == job_id)
    assert any("企业口碑" in reason for reason in target["match_reasons"])


def test_new_pages_render(db_path):
    """TC-V11：急招、社区、评分、小任务、企业主页与内容审核页可渲染。"""
    company_id = make_company("v12_page_company@example.com")
    make_job(company_id, status="APPROVED")
    student_id = _verified_student("v12_page_student@example.com")

    at = AppTest.from_file(str(PROJECT_ROOT / "app.py"))
    at.session_state["auth_user"] = auth.get_user(student_id)
    at.run()
    assert not at.exception

    for page in (
        "views/student/urgent.py",
        "views/student/community.py",
        "views/student/company_reviews.py",
        "views/student/micro_tasks.py",
    ):
        at.switch_page(page).run()
        assert not at.exception, page

    at.session_state["selected_company_id"] = company_id
    at.switch_page("views/student/company.py").run()
    assert not at.exception

    admin_id = make_admin("v12_page_admin@example.com")
    admin_at = AppTest.from_file(str(PROJECT_ROOT / "app.py"))
    admin_at.session_state["auth_user"] = auth.get_user(admin_id)
    admin_at.run()
    admin_at.switch_page("views/admin/moderation.py").run()
    assert not admin_at.exception


def _login(email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_api_community_endpoints(db_path):
    """TC-V12：REST 覆盖文化帖、企业评分与小任务。"""
    company_id = make_company("v12_api_company@example.com")
    admin_id = make_admin("v12_api_admin@example.com")
    student_id = _verified_student("v12_api_student@example.com")
    headers = _login("v12_api_student@example.com", STUDENT_PASSWORD)

    created = client.post(
        "/api/v1/culture-posts",
        json={
            "company_id": company_id,
            **_post_payload(),
        },
        headers=headers,
    )
    assert created.status_code == 201
    post_id = created.json()["id"]
    culture.review_post(admin_id, post_id, "APPROVED")

    posts = client.get(
        "/api/v1/culture-posts",
        params={"company_id": company_id},
        headers=headers,
    )
    assert posts.status_code == 200
    assert len(posts.json()) == 1

    review = client.post(
        f"/api/v1/companies/{company_id}/reviews",
        json=_review_payload(),
        headers=headers,
    )
    assert review.status_code == 201

    tasks = client.get("/api/v1/micro-tasks", headers=headers)
    assert tasks.status_code == 200
    assert tasks.json() == []

    assert student_id
