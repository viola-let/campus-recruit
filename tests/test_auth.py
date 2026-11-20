"""认证测试：注册、登录、停用账号、角色校验。"""

import pytest

from core import auth
from core.db import get_connection, query_one
from core.errors import BusinessError


def test_register_and_login_student(db_path):
    user_id = auth.register_student("Student@Example.com", "Student123!", "张三")

    user = auth.login("student@example.com", "Student123!")

    assert user["id"] == user_id
    assert user["role"] == "student"
    assert user["display_name"] == "张三"
    assert "password_hash" not in user


def test_duplicate_email_is_rejected(db_path):
    auth.register_student("student@example.com", "Student123!", "张三")

    with pytest.raises(BusinessError) as exc_info:
        auth.register_student("student@example.com", "Student123!", "李四")

    assert exc_info.value.code == "EMAIL_EXISTS"


def test_wrong_password_is_rejected(db_path):
    auth.register_student("student@example.com", "Student123!", "张三")

    with pytest.raises(BusinessError) as exc_info:
        auth.login("student@example.com", "Wrong123!")

    assert exc_info.value.code == "AUTH_INVALID_CREDENTIALS"


def test_inactive_account_is_rejected(db_path):
    user_id = auth.register_student("student@example.com", "Student123!", "张三")
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))

    with pytest.raises(BusinessError) as exc_info:
        auth.login("student@example.com", "Student123!")

    assert exc_info.value.code == "AUTH_INACTIVE"


def test_register_company_creates_pending_profile(db_path):
    user_id = auth.register_company("company@example.com", "Company123!", "示例科技")

    with get_connection() as conn:
        company = query_one(
            conn, "SELECT * FROM companies WHERE user_id = ?", (user_id,)
        )

    assert company is not None
    assert company["name"] == "示例科技"
    assert company["status"] == "PENDING"
    assert company["hr_status"] == "PENDING"


def test_require_role_rejects_wrong_role(db_path):
    user_id = auth.register_student("student@example.com", "Student123!", "张三")

    with pytest.raises(BusinessError) as exc_info:
        auth.require_role(user_id, "admin")

    assert exc_info.value.code == "FORBIDDEN"


def test_require_role_returns_user(db_path):
    user_id = auth.register_student("student@example.com", "Student123!", "张三")

    user = auth.require_role(user_id, "student")

    assert user["id"] == user_id
    assert user["role"] == "student"


def test_create_admin(db_path):
    user_id = auth.create_admin("admin@example.com", "ChangeMe123", "平台管理员")

    user = auth.login("admin@example.com", "ChangeMe123")

    assert user["id"] == user_id
    assert user["role"] == "admin"
