"""REST 接口扩展测试：错误映射、上传下载、角色权限与契约。"""

import json
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from api.main import app
from core import auth
from core.db import get_connection
from core.security import JWT_ALGORITHM, get_jwt_secret
from services import jobs as job_service
from tests.support import (
    ADMIN_PASSWORD,
    COMPANY_PASSWORD,
    STUDENT_PASSWORD,
    job_payload,
    make_admin,
    make_company,
    resume_payload,
)

client = TestClient(app)


def _register_login_student(email="api_student@example.com") -> dict:
    client.post(
        "/api/v1/auth/register/student",
        json={
            "email": email,
            "password": STUDENT_PASSWORD,
            "display_name": "接口学生",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": STUDENT_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _register_login_company(email="api_company@example.com") -> dict:
    client.post(
        "/api/v1/auth/register/company",
        json={
            "email": email,
            "password": COMPANY_PASSWORD,
            "company_name": "接口公司",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": COMPANY_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(email="api_admin@example.com") -> dict:
    make_admin(email)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_and_contract(db_path):
    """TC-A01：健康检查可用，契约版本为 OpenAPI 3.1。"""
    assert client.get("/health").json() == {"status": "ok"}

    schema = client.get("/openapi.json").json()
    assert schema["openapi"] == "3.1.0"
    assert len(schema["paths"]) >= 20


def test_register_validation_and_duplicate(db_path):
    """TC-A02：注册短密码返回 400；重复邮箱返回 409。"""
    short = client.post(
        "/api/v1/auth/register/student",
        json={"email": "a@example.com", "password": "1234567", "display_name": "张三"},
    )
    assert short.status_code == 400
    assert short.json()["code"] == "VALIDATION_ERROR"

    payload = {
        "email": "dup@example.com",
        "password": STUDENT_PASSWORD,
        "display_name": "张三",
    }
    assert client.post("/api/v1/auth/register/student", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register/student", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "EMAIL_EXISTS"


def test_login_failure_mapping(db_path):
    """TC-A03：登录失败统一 400，不泄露账号存在性。"""
    make_company()

    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "company@example.com", "password": "WrongPass123!"},
    )
    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass123!"},
    )

    assert wrong.status_code == missing.status_code == 400
    assert wrong.json() == missing.json()


def test_token_failures_return_401(db_path):
    """TC-A04：缺失、伪造、过期 Token 与停用账号均返回 401。"""
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"}
        ).status_code
        == 401
    )

    student_id = auth.register_student(
        "expired@example.com", STUDENT_PASSWORD, "过期用户"
    )
    expired = jwt.encode(
        {
            "sub": str(student_id),
            "role": "student",
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        },
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
        ).status_code
        == 401
    )

    headers = _register_login_student("inactive@example.com")
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET is_active = 0 WHERE email = ?", ("inactive@example.com",)
        )
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_role_permissions_on_api(db_path):
    """TC-A05：跨角色访问接口返回 403。"""
    student = _register_login_student()
    company = _register_login_company()

    assert client.get("/api/v1/admin/dashboard", headers=student).status_code == 403
    assert client.get("/api/v1/students/me/resume", headers=company).status_code == 403
    assert client.get("/api/v1/companies/me", headers=student).status_code == 403


def test_student_resume_api_flow(db_path, tmp_path, monkeypatch):
    """TC-A06：保存简历 → 查询 → 上传合法/非法附件。"""
    headers = _register_login_student()

    missing = client.get("/api/v1/students/me/resume", headers=headers)
    assert missing.status_code == 404

    payload = resume_payload()
    saved = client.put("/api/v1/students/me/resume", headers=headers, json=payload)
    assert saved.status_code == 200
    assert saved.json()["status"] == "PENDING"

    invalid = client.post(
        "/api/v1/students/me/resume/file",
        headers=headers,
        files={"file": ("virus.exe", b"x", "application/octet-stream")},
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "FILE_INVALID"

    monkeypatch.setattr("core.security.BASE_DIR", tmp_path)
    monkeypatch.setattr("services.students.RESUME_UPLOAD_DIR", tmp_path / "resumes")
    uploaded = client.post(
        "/api/v1/students/me/resume/file",
        headers=headers,
        files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["file_path"].startswith("resumes/")


def test_company_profile_and_job_api_flow(db_path):
    """TC-A07：企业资料保存、未双审发布被拒、审核通过后发布/关闭/重开。"""
    company = _register_login_company()
    admin = _admin_headers()

    profile = client.get("/api/v1/companies/me", headers=company).json()
    updated = client.put(
        "/api/v1/companies/me",
        headers=company,
        json={
            "name": "接口公司",
            "license_no": "91310000API00001X",
            "hr_name": "接口 HR",
            "hr_email": "hr@example.com",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "PENDING"

    blocked = client.post(
        "/api/v1/companies/me/jobs", headers=company, json=job_payload()
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "FORBIDDEN"

    client.post(
        f"/api/v1/admin/companies/{profile['id']}/license/review",
        headers=admin,
        json={"decision": "APPROVED"},
    )
    hr = client.post(
        f"/api/v1/admin/companies/{profile['id']}/hr/review",
        headers=admin,
        json={"decision": "APPROVED"},
    )
    assert hr.status_code == 200

    created = client.post(
        "/api/v1/companies/me/jobs", headers=company, json=job_payload()
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    assert created.json()["status"] == "PENDING"

    closed = client.patch(
        f"/api/v1/companies/me/jobs/{job_id}",
        headers=company,
        json={"action": "close"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    reopened = client.patch(
        f"/api/v1/companies/me/jobs/{job_id}",
        headers=company,
        json={"action": "reopen"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "PENDING"

    edited = client.patch(
        f"/api/v1/companies/me/jobs/{job_id}",
        headers=company,
        json={"action": "edit", "job": job_payload(title="接口职位（已编辑）")},
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "接口职位（已编辑）"


def test_job_review_and_visibility(db_path):
    """TC-A08：待审职位学生不可见；通过并推荐后可见且置顶。"""
    company = _register_login_company()
    admin = _admin_headers()
    student = _register_login_student()
    profile = client.get("/api/v1/companies/me", headers=company).json()
    client.put(
        "/api/v1/companies/me",
        headers=company,
        json={
            "name": "接口公司",
            "license_no": "91310000API00001X",
            "hr_name": "接口 HR",
            "hr_email": "hr@example.com",
        },
    )
    for kind in ("license", "hr"):
        client.post(
            f"/api/v1/admin/companies/{profile['id']}/{kind}/review",
            headers=admin,
            json={"decision": "APPROVED"},
        )
    job_id = client.post(
        "/api/v1/companies/me/jobs", headers=company, json=job_payload()
    ).json()["id"]

    before = client.get("/api/v1/jobs", headers=student).json()
    assert all(item["id"] != job_id for item in before)

    reviewed = client.post(
        f"/api/v1/admin/jobs/{job_id}/review",
        headers=admin,
        json={"decision": "APPROVED", "featured": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["is_featured"] == 1

    after = client.get("/api/v1/jobs", headers=student).json()
    assert after[0]["id"] == job_id


def test_application_api_flow_and_conflicts(db_path):
    """TC-A09：投递成功、重复投递 409、非法流转 400。"""
    company_id = make_company()

    client_student = _register_login_student()
    client.put(
        "/api/v1/students/me/resume", headers=client_student, json=resume_payload()
    )
    resume_id = client.get("/api/v1/students/me/resume", headers=client_student).json()[
        "id"
    ]
    admin = _admin_headers("reviewer@example.com")
    client.post(
        f"/api/v1/admin/resumes/{resume_id}/review",
        headers=admin,
        json={"decision": "VERIFIED"},
    )

    job_id = job_service.create_job(company_id, job_payload(title="接口投递职位"))["id"]
    client.post(
        f"/api/v1/admin/jobs/{job_id}/review",
        headers=admin,
        json={"decision": "APPROVED"},
    )

    created = client.post(f"/api/v1/jobs/{job_id}/applications", headers=client_student)
    assert created.status_code == 201
    application_id = created.json()["id"]

    duplicate = client.post(
        f"/api/v1/jobs/{job_id}/applications", headers=client_student
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DUPLICATE_APPLICATION"

    company = client.post(
        "/api/v1/auth/login",
        json={"email": "company@example.com", "password": COMPANY_PASSWORD},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {company}"}

    invalid = client.patch(
        f"/api/v1/applications/{application_id}/status",
        headers=headers,
        json={"new_status": "HIRED"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "INVALID_STATE"

    rejected = client.patch(
        f"/api/v1/applications/{application_id}/status",
        headers=headers,
        json={"new_status": "REJECTED"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "VALIDATION_ERROR"


def test_resume_file_download_permissions(db_path, tmp_path, monkeypatch):
    """TC-A10：企业只能下载本公司投递的简历附件。"""
    monkeypatch.setattr("core.security.BASE_DIR", tmp_path)
    monkeypatch.setattr("core.security.UPLOADS_DIR", tmp_path)
    monkeypatch.setattr("services.students.RESUME_UPLOAD_DIR", tmp_path / "resumes")

    student_headers = _register_login_student()
    client.put(
        "/api/v1/students/me/resume", headers=student_headers, json=resume_payload()
    )
    client.post(
        "/api/v1/students/me/resume/file",
        headers=student_headers,
        files={"file": ("resume.pdf", b"%PDF data", "application/pdf")},
    )
    resume_id = client.get(
        "/api/v1/students/me/resume", headers=student_headers
    ).json()["id"]
    admin = _admin_headers()
    client.post(
        f"/api/v1/admin/resumes/{resume_id}/review",
        headers=admin,
        json={"decision": "VERIFIED"},
    )

    owner_id = make_company("owner@example.com", "本公司")
    make_company("other@example.com", "其他公司")
    job_id = job_service.create_job(owner_id, job_payload())["id"]
    client.post(
        f"/api/v1/admin/jobs/{job_id}/review",
        headers=admin,
        json={"decision": "APPROVED"},
    )
    application_id = client.post(
        f"/api/v1/jobs/{job_id}/applications", headers=student_headers
    ).json()["id"]

    def login_company(email):
        token = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": COMPANY_PASSWORD},
        ).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    owner_headers = login_company("owner@example.com")
    other_headers = login_company("other@example.com")

    downloaded = client.get(
        f"/api/v1/applications/{application_id}/resume-file", headers=owner_headers
    )
    assert downloaded.status_code == 200
    assert downloaded.content == b"%PDF data"

    assert (
        client.get(
            f"/api/v1/applications/{application_id}/resume-file",
            headers=other_headers,
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/applications/{application_id}/resume-file",
            headers=student_headers,
        ).status_code
        == 403
    )


def test_admin_api_queues_and_dashboard(db_path):
    """TC-A11：管理端统计与待办结构完整。"""
    admin = _admin_headers()
    make_company()

    dashboard = client.get("/api/v1/admin/dashboard", headers=admin)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert set(body) == {
        "pending_company_license",
        "pending_company_hr",
        "pending_jobs",
        "pending_resumes",
        "total_applications",
        "hired_applications",
    }

    pending = client.get("/api/v1/admin/pending", headers=admin)
    assert pending.status_code == 200
    assert set(pending.json()) == {"companies", "jobs", "resumes"}


def test_api_validation_and_routing_errors(db_path):
    """TC-A12：404/405/422 与分页参数边界。"""
    student = _register_login_student()

    assert client.get("/api/v1/not-exists").status_code == 404
    assert client.delete("/health").status_code == 405
    assert (
        client.post(
            "/api/v1/auth/login",
            content="{bad json",
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert client.get("/api/v1/jobs?limit=0", headers=student).status_code == 422
    assert client.get("/api/v1/jobs?limit=201", headers=student).status_code == 422
    assert client.get("/api/v1/jobs").status_code == 401


def test_cors_allows_streamlit_origin_only(db_path):
    """TC-A13：CORS 仅放行 localhost:8501。"""
    allowed = client.options(
        "/api/v1/jobs",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:8501"

    denied = client.options(
        "/api/v1/jobs",
        headers={
            "Origin": "http://127.0.0.1:8501",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in denied.headers


def test_saved_openapi_matches_live(db_path):
    """TC-A14：仓库中的 openapi.json 与运行中的应用一致。"""
    from pathlib import Path

    saved = json.loads(
        (Path(__file__).resolve().parent.parent / "api" / "openapi.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved == client.get("/openapi.json").json()


def test_invalid_review_decision_mapping(db_path):
    """TC-A15：非法审核结论返回 400。"""
    admin = _admin_headers()
    make_company(approved=False)
    company_token = client.post(
        "/api/v1/auth/login",
        json={"email": "company@example.com", "password": COMPANY_PASSWORD},
    ).json()["access_token"]
    profile = client.get(
        "/api/v1/companies/me",
        headers={"Authorization": f"Bearer {company_token}"},
    ).json()

    response = client.post(
        f"/api/v1/admin/companies/{profile['id']}/license/review",
        headers=admin,
        json={"decision": "MAYBE"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
