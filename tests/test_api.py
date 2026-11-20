"""REST API 测试：健康检查、登录、鉴权与越权（T-13 至 T-15）。"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

STUDENT = {
    "email": "api_student@example.com",
    "password": "Student123!",
    "display_name": "接口学生",
}


def _register_and_login() -> str:
    response = client.post("/api/v1/auth/register/student", json=STUDENT)
    assert response.status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": STUDENT["email"], "password": STUDENT["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health(db_path):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_and_me(db_path):
    """T-15：登录后 /auth/me 返回当前用户且不含密码哈希。"""
    token = _register_and_login()

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == STUDENT["email"]
    assert body["role"] == "student"
    assert "password_hash" not in body


def test_protected_endpoint_requires_token(db_path):
    """T-13：无 Token 访问受保护接口返回 401。"""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_student_cannot_access_admin_api(db_path):
    """T-14：学生 Token 调用管理端接口返回 403。"""
    token = _register_and_login()

    response = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_login_sets_token_expiry(db_path):
    _register_and_login()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": STUDENT["email"], "password": STUDENT["password"]},
    )

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 8 * 3600
