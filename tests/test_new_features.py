"""新增功能测试：企业品牌、精准搜索、相似推荐、批量投递、收藏与智能推荐。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api.main import app
from core import auth
from core.config import BASE_DIR, now_iso
from core.db import get_connection
from core.errors import BusinessError
from services import applications, companies, favorites, jobs, recommendations, students
from tests.support import (
    COMPANY_PASSWORD,
    STUDENT_PASSWORD,
    make_company,
    make_student,
    resume_payload,
    set_resume_status,
)

client = TestClient(app)


def _insert_job(
    company_user_id: int,
    title: str,
    description: str,
    status: str = "APPROVED",
    city: str = "上海",
    is_featured: int = 0,
    requirements: str = "熟悉 Python 与 SQL",
) -> int:
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
            VALUES (?, ?, 'CAMPUS', ?, '20-30K', ?, ?,
                    ?, ?, ?, ?)
            """,
            (
                company["id"],
                title,
                city,
                description,
                requirements,
                status,
                is_featured,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.lastrowid)


def _verified_student(email: str, name: str = "测试学生", **resume_overrides) -> int:
    student_id = make_student(email, name)
    students.save_resume(student_id, resume_payload(**resume_overrides))
    set_resume_status(student_id, "VERIFIED")
    return student_id


def test_company_branding_roundtrip(db_path):
    """TC-N01：品牌信息可保存读取，logo 可上传且校验文件类型。"""
    company_id = make_company("brand_company@example.com")

    profile = companies.update_branding(
        company_id,
        {
            "intro": "专注企业级招聘服务",
            "culture": "用户第一 · 坦诚协作",
            "industry": "企业服务",
            "company_size": "100-499人",
            "funding_stage": "B轮",
            "city": "杭州",
            "benefits": "六险一金、弹性工作",
        },
    )
    assert profile["intro"] == "专注企业级招聘服务"
    assert profile["industry"] == "企业服务"
    assert profile["benefits"] == "六险一金、弹性工作"

    with pytest.raises(BusinessError) as exc:
        companies.update_branding(company_id, {"intro": "长" * 1001})
    assert exc.value.code == "VALIDATION_ERROR"

    relative_path = companies.attach_logo(
        company_id, "logo.png", b"\x89PNG\r\n\x1a\n" + b"0" * 128
    )
    assert companies.get_profile(company_id)["logo_path"] == relative_path
    try:
        name, content = companies.get_company_logo(_company_row_id(company_id))
        assert name.endswith(".png") and content
    finally:
        (BASE_DIR / relative_path).unlink(missing_ok=True)

    with pytest.raises(BusinessError) as exc:
        companies.attach_logo(company_id, "logo.gif", b"GIF89a")
    assert exc.value.code == "FILE_INVALID"


def _company_row_id(company_user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM companies WHERE user_id = ?", (company_user_id,)
        ).fetchone()
    return int(row["id"])


def test_keyword_search_supports_and_category_and_field(db_path):
    """TC-N02：多关键词 AND、仅标题搜索与岗位类别筛选。"""
    company_id = make_company("search_company@example.com")
    python_job = _insert_job(
        company_id, "【技术】Python 后端工程师", "负责 Python 服务端开发与 SQL 优化。"
    )
    java_job = _insert_job(
        company_id,
        "【技术】Java 后端工程师",
        "负责 Java 服务端开发与稳定性保障。",
        requirements="熟悉 Java 与 Spring Boot",
    )
    product_job = _insert_job(
        company_id,
        "【产品】产品经理",
        "负责产品规划、用户研究与需求分析。",
        requirements="具备需求分析与原型设计能力",
    )

    both_words = jobs.search_jobs(keyword="Python 后端")
    assert [job["id"] for job in both_words] == [python_job]

    title_only = jobs.search_jobs(keyword="服务端", search_field="title")
    assert title_only == []

    all_fields = jobs.search_jobs(keyword="服务端")
    assert {job["id"] for job in all_fields} == {python_job, java_job}

    by_category = jobs.search_jobs(category="产品")
    assert [job["id"] for job in by_category] == [product_job]


def test_similar_jobs_rank_same_category_and_city(db_path):
    """TC-N03：相似职位优先同类目、同城市，且不包含自身。"""
    company_id = make_company("similar_company@example.com")
    base_job = _insert_job(
        company_id, "【技术】Python 后端工程师", "负责 Python 服务端开发。"
    )
    same_category = _insert_job(
        company_id, "【技术】Java 后端工程师", "负责 Java 服务端开发。"
    )
    other_city = _insert_job(
        company_id,
        "【技术】Go 后端工程师",
        "负责 Go 服务端开发。",
        city="北京",
    )
    unrelated = _insert_job(
        company_id,
        "【市场】品牌专员",
        "负责品牌传播与活动执行。",
        city="成都",
        requirements="具备文案与活动策划能力",
    )

    similar = jobs.similar_jobs(base_job, limit=5)
    ids = [job["id"] for job in similar]

    assert base_job not in ids
    assert ids[0] == same_category
    assert other_city in ids
    assert unrelated not in ids
    assert similar[0]["match_score"] >= similar[1]["match_score"]


def test_recommendations_match_resume_and_exclude_applied(db_path):
    """TC-N04：智能推荐命中技能并给出理由，已投递职位不再推荐。"""
    company_id = make_company("reco_company@example.com")
    matched = _insert_job(
        company_id, "【技术】Python 后端工程师", "负责 Python 服务端开发与 SQL 优化。"
    )
    also_matched = _insert_job(
        company_id, "【技术】Python 数据工程师", "使用 Python 与 SQL 构建数据管道。"
    )
    unrelated = _insert_job(
        company_id,
        "【市场】品牌市场专员",
        "负责品牌传播、渠道投放与活动执行。",
        city="成都",
        requirements="具备文案与活动策划能力",
    )
    student_id = _verified_student(
        "reco_student@example.com",
        skills="Python / SQL",
        summary="期望城市：上海，希望从事后端开发",
    )

    results = recommendations.recommend_jobs(student_id)
    result_ids = [job["id"] for job in results]
    assert set(result_ids) == {matched, also_matched}
    assert unrelated not in result_ids
    assert any("技能匹配" in reason for reason in results[0]["match_reasons"])

    applications.apply_to_job(student_id, matched)
    after_apply = recommendations.recommend_jobs(student_id)
    assert matched not in [job["id"] for job in after_apply]
    assert also_matched in [job["id"] for job in after_apply]


def test_batch_apply_reports_partial_success(db_path):
    """TC-N05：批量投递汇总成功与失败，且限制单次 20 个职位。"""
    company_id = make_company("batch_company@example.com")
    first_job = _insert_job(
        company_id, "【技术】Python 后端工程师", "负责 Python 服务端开发。"
    )
    second_job = _insert_job(
        company_id, "【技术】Java 后端工程师", "负责 Java 服务端开发。"
    )
    student_id = _verified_student("batch_student@example.com")

    applications.apply_to_job(student_id, first_job)
    result = applications.batch_apply_to_job(
        student_id, [first_job, second_job, 999999]
    )

    assert result["requested"] == 3
    assert [item["job_id"] for item in result["succeeded"]] == [second_job]
    failed_codes = {item["code"] for item in result["failed"]}
    assert {"DUPLICATE_APPLICATION", "NOT_FOUND"} <= failed_codes
    assert applications.applied_job_ids(student_id) == {first_job, second_job}

    with pytest.raises(BusinessError) as exc:
        applications.batch_apply_to_job(student_id, list(range(1, 22)))
    assert exc.value.code == "VALIDATION_ERROR"


def test_favorites_toggle_and_list(db_path):
    """TC-N06：收藏切换、列表查询与关闭职位不可收藏。"""
    company_id = make_company("fav_company@example.com")
    approved_job = _insert_job(
        company_id, "【技术】Python 后端工程师", "负责 Python 服务端开发。"
    )
    closed_job = _insert_job(
        company_id, "【技术】Java 后端工程师", "负责 Java 服务端开发。", status="CLOSED"
    )
    student_id = _verified_student("fav_student@example.com")

    assert favorites.toggle_favorite(student_id, approved_job) is True
    assert favorites.favorite_job_ids(student_id) == {approved_job}
    assert [job["id"] for job in favorites.list_favorites(student_id)] == [approved_job]

    assert favorites.toggle_favorite(student_id, approved_job) is False
    assert favorites.list_favorites(student_id) == []

    with pytest.raises(BusinessError) as exc:
        favorites.toggle_favorite(student_id, closed_job)
    assert exc.value.code == "JOB_NOT_OPEN"


def _login(email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_api_exposes_new_job_features(db_path):
    """TC-N07：REST 接口覆盖品牌、搜索、详情、批量投递、收藏与推荐。"""
    company_id = make_company("api_brand@example.com")
    company_headers = _login("api_brand@example.com", COMPANY_PASSWORD)
    branding = client.put(
        "/api/v1/companies/me/branding",
        json={
            "intro": "专注招聘技术服务",
            "culture": "开放协作",
            "industry": "企业服务",
            "company_size": "100-499人",
            "funding_stage": "B轮",
            "city": "上海",
            "benefits": "六险一金、弹性工作",
        },
        headers=company_headers,
    )
    assert branding.status_code == 200
    assert branding.json()["industry"] == "企业服务"

    job_id = _insert_job(
        company_id, "【技术】Python 后端工程师", "负责 Python 服务端开发。"
    )
    _verified_student("api_feature_student@example.com")
    student_headers = _login("api_feature_student@example.com", STUDENT_PASSWORD)

    search = client.get(
        "/api/v1/jobs",
        params={"keyword": "Python", "category": "技术", "sort": "latest"},
        headers=student_headers,
    )
    assert search.status_code == 200
    assert [item["id"] for item in search.json()] == [job_id]

    detail = client.get(f"/api/v1/jobs/{job_id}", headers=student_headers)
    assert detail.status_code == 200
    assert detail.json()["company_industry"] == "企业服务"

    similar = client.get(f"/api/v1/jobs/{job_id}/similar", headers=student_headers)
    assert similar.status_code == 200

    favorite = client.post(f"/api/v1/jobs/{job_id}/favorite", headers=student_headers)
    assert favorite.json() == {"job_id": job_id, "favorited": True}
    favorites_list = client.get("/api/v1/jobs/favorites", headers=student_headers)
    assert [item["id"] for item in favorites_list.json()] == [job_id]

    batch = client.post(
        "/api/v1/jobs/batch-applications",
        json={"job_ids": [job_id]},
        headers=student_headers,
    )
    assert batch.status_code == 201
    assert len(batch.json()["succeeded"]) == 1

    reco = client.get("/api/v1/jobs/recommendations", headers=student_headers)
    assert reco.status_code == 200


def test_new_student_pages_render(db_path):
    """TC-N08：智能推荐、收藏与职位详情页面可正常渲染。"""
    company_id = make_company("page_company@example.com")
    job_id = _insert_job(
        company_id, "【技术】Python 后端工程师", "负责 Python 服务端开发。"
    )
    student_id = _verified_student("page_student@example.com")
    favorites.toggle_favorite(student_id, job_id)

    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"))
    at.session_state["auth_user"] = auth.get_user(student_id)
    at.run()
    assert not at.exception

    for page in (
        "views/student/jobs.py",
        "views/student/recommendations.py",
        "views/student/favorites.py",
    ):
        at.switch_page(page).run()
        assert not at.exception, page

    at.session_state["selected_job_id"] = job_id
    at.switch_page("views/student/job_detail.py").run()
    assert not at.exception
    assert any("Python" in item.value for item in at.html)
