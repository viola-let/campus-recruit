"""认证与用户：注册、登录、当前用户、角色校验。

返回的用户字典只包含公开字段，绝不返回 password_hash。
"""

import re
import sqlite3

from core.config import PASSWORD_MIN_LENGTH, Role, now_iso
from core.db import get_connection, query_one
from core.errors import BusinessError
from core.security import hash_password, verify_password

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PUBLIC_USER_FIELDS = "id, email, role, display_name, is_active, created_at"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _validate_email(email: str) -> None:
    if not EMAIL_PATTERN.match(email):
        raise BusinessError("VALIDATION_ERROR", "请输入有效的邮箱地址")


def _validate_password(password: str) -> None:
    if len(password or "") < PASSWORD_MIN_LENGTH:
        raise BusinessError("VALIDATION_ERROR", f"密码至少 {PASSWORD_MIN_LENGTH} 位")


def _validate_display_name(name: str) -> None:
    if not name:
        raise BusinessError("VALIDATION_ERROR", "请填写名称")


def _create_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    role: str,
    display_name: str,
) -> int:
    """在给定连接中创建用户，邮箱重复时转换为业务错误。"""
    try:
        cursor = conn.execute(
            """
            INSERT INTO users
                (email, password_hash, role, display_name, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                email,
                hash_password(password),
                role,
                display_name,
                now_iso(),
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise BusinessError("EMAIL_EXISTS", "该邮箱已注册，请直接登录") from exc
    return int(cursor.lastrowid)


def register_student(email: str, password: str, display_name: str) -> int:
    """注册学生账号，返回用户 ID。"""
    email = _normalize_email(email)
    display_name = (display_name or "").strip()
    _validate_email(email)
    _validate_password(password)
    _validate_display_name(display_name)

    with get_connection() as conn:
        return _create_user(conn, email, password, Role.STUDENT.value, display_name)


def register_company(email: str, password: str, company_name: str) -> int:
    """注册企业账号，并创建一条待审核的企业资料。"""
    email = _normalize_email(email)
    company_name = (company_name or "").strip()
    _validate_email(email)
    _validate_password(password)
    _validate_display_name(company_name)

    with get_connection() as conn:
        user_id = _create_user(conn, email, password, Role.COMPANY.value, company_name)
        timestamp = now_iso()
        conn.execute(
            """
            INSERT INTO companies
                (user_id, name, license_no, license_file, hr_name, hr_email,
                 hr_proof_file, status, hr_status, created_at, updated_at)
            VALUES (?, ?, '', NULL, '', '', NULL, 'PENDING', 'PENDING', ?, ?)
            """,
            (user_id, company_name, timestamp, timestamp),
        )
    return user_id


def create_admin(email: str, password: str, display_name: str = "平台管理员") -> int:
    """创建管理员账号，仅由 scripts/init_db.py 使用。"""
    email = _normalize_email(email)
    display_name = (display_name or "").strip() or "平台管理员"
    _validate_email(email)
    _validate_password(password)

    with get_connection() as conn:
        return _create_user(conn, email, password, Role.ADMIN.value, display_name)


def login(email: str, password: str) -> dict:
    """登录成功返回公开用户信息；失败统一提示，不泄露账号是否存在。"""
    email = _normalize_email(email)

    with get_connection() as conn:
        row = query_one(
            conn,
            """
            SELECT id, email, role, display_name, is_active, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,),
        )

    if row is None or not verify_password(password, row["password_hash"]):
        raise BusinessError("AUTH_INVALID_CREDENTIALS", "邮箱或密码错误")
    if not row["is_active"]:
        raise BusinessError("AUTH_INACTIVE", "账号已停用，请联系管理员")

    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "display_name": row["display_name"],
        "is_active": row["is_active"],
    }


def get_user(user_id: int) -> dict | None:
    """按用户 ID 查询公开信息。"""
    with get_connection() as conn:
        return query_one(
            conn,
            f"SELECT {PUBLIC_USER_FIELDS} FROM users WHERE id = ?",
            (user_id,),
        )


def require_role(actor_id: int, role: Role | str) -> dict:
    """校验当前用户存在、启用且角色匹配，返回用户字典。"""
    user = get_user(actor_id)
    if user is None:
        raise BusinessError("AUTH_INVALID_CREDENTIALS", "登录状态失效，请重新登录")
    if not user["is_active"]:
        raise BusinessError("AUTH_INACTIVE", "账号已停用，请联系管理员")

    expected = role.value if isinstance(role, Role) else role
    if user["role"] != expected:
        raise BusinessError("FORBIDDEN", "无权限执行该操作")
    return user
