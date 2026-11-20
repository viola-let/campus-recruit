"""企业服务：资料维护、双审核、发布资格与账号启停。"""

from core import auth
from core.config import (
    LICENSE_UPLOAD_DIR,
    LOGO_UPLOAD_DIR,
    ReviewStatus,
    Role,
    now_iso,
)
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError
from core.security import resolve_upload_path, save_image_upload, save_upload

COMPANY_SELECT_SQL = """
    SELECT c.id, c.user_id, c.name, c.license_no, c.license_file,
           c.hr_name, c.hr_email, c.hr_proof_file, c.status, c.hr_status,
           c.logo_path, c.intro, c.culture, c.industry, c.company_size,
           c.funding_stage, c.city, c.benefits,
           c.created_at, c.updated_at, u.email,
           (SELECT note FROM review_logs
            WHERE entity_type = 'company_license' AND entity_id = c.id
            ORDER BY id DESC LIMIT 1) AS license_note,
           (SELECT note FROM review_logs
            WHERE entity_type = 'company_hr' AND entity_id = c.id
            ORDER BY id DESC LIMIT 1) AS hr_note
    FROM companies c
    JOIN users u ON u.id = c.user_id
"""


def get_profile(actor_id: int, user_id: int | None = None) -> dict | None:
    """企业查看本企业资料；管理员可指定企业账号。"""
    actor = auth.get_user(actor_id)
    if actor is None:
        raise BusinessError("AUTH_INVALID_CREDENTIALS", "登录状态失效，请重新登录")

    if actor["role"] == Role.COMPANY.value:
        if user_id is not None and user_id != actor_id:
            raise BusinessError("FORBIDDEN", "无权限查看其他企业资料")
        target_id = actor_id
    elif actor["role"] == Role.ADMIN.value:
        if user_id is None:
            raise BusinessError("VALIDATION_ERROR", "请指定企业")
        target_id = user_id
    else:
        raise BusinessError("FORBIDDEN", "无权限执行该操作")

    with get_connection() as conn:
        return query_one(
            conn, f"{COMPANY_SELECT_SQL} WHERE c.user_id = ?", (target_id,)
        )


def upsert_profile(actor_id: int, payload: dict) -> dict:
    """企业更新资料；保存后资质与 HR 状态都回到 PENDING。"""
    auth.require_role(actor_id, Role.COMPANY)

    name = (payload.get("name") or "").strip()
    license_no = (payload.get("license_no") or "").strip()
    hr_name = (payload.get("hr_name") or "").strip()
    hr_email = (payload.get("hr_email") or "").strip()

    if not name:
        raise BusinessError("VALIDATION_ERROR", "请填写企业名称")
    if not license_no:
        raise BusinessError("VALIDATION_ERROR", "请填写统一社会信用代码")
    if not hr_name:
        raise BusinessError("VALIDATION_ERROR", "请填写 HR 姓名")
    if "@" not in hr_email:
        raise BusinessError("VALIDATION_ERROR", "请填写有效的 HR 企业邮箱")

    timestamp = now_iso()
    with get_connection() as conn:
        profile = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if profile is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")

        conn.execute(
            """
            UPDATE companies
            SET name = ?, license_no = ?, hr_name = ?, hr_email = ?,
                status = ?, hr_status = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (
                name,
                license_no,
                hr_name,
                hr_email,
                ReviewStatus.PENDING.value,
                ReviewStatus.PENDING.value,
                timestamp,
                actor_id,
            ),
        )

    return get_profile(actor_id)


def attach_company_file(actor_id: int, kind: str, filename: str, content: bytes) -> str:
    """上传营业执照或 HR 在职证明，对应审核状态回到 PENDING。"""
    auth.require_role(actor_id, Role.COMPANY)

    if kind == "license":
        update_sql = (
            "UPDATE companies SET license_file = ?, status = ?, updated_at = ? "
            "WHERE user_id = ?"
        )
    elif kind == "hr_proof":
        update_sql = (
            "UPDATE companies SET hr_proof_file = ?, hr_status = ?, updated_at = ? "
            "WHERE user_id = ?"
        )
    else:
        raise BusinessError("VALIDATION_ERROR", "文件类型不合法")

    relative_path = save_upload(filename, content, LICENSE_UPLOAD_DIR)
    with get_connection() as conn:
        profile = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if profile is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")

        conn.execute(
            update_sql,
            (relative_path, ReviewStatus.PENDING.value, now_iso(), actor_id),
        )
    return relative_path


def update_branding(actor_id: int, payload: dict) -> dict:
    """更新企业品牌展示信息，不触发资质或 HR 重新审核。"""
    auth.require_role(actor_id, Role.COMPANY)

    fields = {}
    limits = {
        "intro": 1000,
        "culture": 1000,
        "industry": 50,
        "company_size": 50,
        "funding_stage": 50,
        "city": 50,
        "benefits": 300,
    }
    for key, max_length in limits.items():
        value = (payload.get(key) or "").strip()
        if len(value) > max_length:
            raise BusinessError(
                "VALIDATION_ERROR", f"{key} 不能超过 {max_length} 个字符"
            )
        fields[key] = value or None

    with get_connection() as conn:
        profile = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if profile is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")

        conn.execute(
            """
            UPDATE companies
            SET intro = ?, culture = ?, industry = ?, company_size = ?,
                funding_stage = ?, city = ?, benefits = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (
                fields["intro"],
                fields["culture"],
                fields["industry"],
                fields["company_size"],
                fields["funding_stage"],
                fields["city"],
                fields["benefits"],
                now_iso(),
                actor_id,
            ),
        )
    return get_profile(actor_id)


def attach_logo(actor_id: int, filename: str, content: bytes) -> str:
    """上传企业 logo，仅更新品牌信息，不影响审核状态。"""
    auth.require_role(actor_id, Role.COMPANY)
    relative_path = save_image_upload(filename, content, LOGO_UPLOAD_DIR)

    with get_connection() as conn:
        profile = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if profile is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")
        conn.execute(
            "UPDATE companies SET logo_path = ?, updated_at = ? WHERE user_id = ?",
            (relative_path, now_iso(), actor_id),
        )
    return relative_path


def get_company_logo(company_id: int) -> tuple[str, bytes]:
    """读取企业 logo（用于 REST 下载）。"""
    with get_connection() as conn:
        profile = query_one(
            conn, "SELECT logo_path FROM companies WHERE id = ?", (company_id,)
        )
    if profile is None:
        raise BusinessError("NOT_FOUND", "企业不存在")
    relative_path = profile["logo_path"]
    if not relative_path:
        raise BusinessError("NOT_FOUND", "企业未上传 logo")

    path = resolve_upload_path(relative_path)
    if not path.is_file():
        raise BusinessError("NOT_FOUND", "企业 logo 文件不存在")
    return path.name, path.read_bytes()


def can_publish_job(actor_id: int) -> bool:
    """企业资质与 HR 审核都通过时才可发布职位。"""
    profile = get_profile(actor_id)
    if profile is None:
        return False
    return (
        profile["status"] == ReviewStatus.APPROVED.value
        and profile["hr_status"] == ReviewStatus.APPROVED.value
    )


def _review(
    admin_id: int,
    company_id: int,
    column: str,
    entity_type: str,
    decision: str,
    note: str | None,
) -> dict:
    """审核企业资料公共流程：只处理 PENDING，拒绝必须写理由。"""
    auth.require_role(admin_id, Role.ADMIN)

    decision = (decision or "").strip().upper()
    if decision not in {ReviewStatus.APPROVED.value, ReviewStatus.REJECTED.value}:
        raise BusinessError("VALIDATION_ERROR", "审核结论不合法")
    note = (note or "").strip()
    if decision == ReviewStatus.REJECTED.value and not note:
        raise BusinessError("VALIDATION_ERROR", "拒绝时必须填写理由")

    if column == "status":
        select_sql = "SELECT id, status FROM companies WHERE id = ?"
        update_sql = (
            "UPDATE companies SET status = ?, updated_at = ? "
            "WHERE id = ? AND status = ?"
        )
    elif column == "hr_status":
        select_sql = "SELECT id, hr_status FROM companies WHERE id = ?"
        update_sql = (
            "UPDATE companies SET hr_status = ?, updated_at = ? "
            "WHERE id = ? AND hr_status = ?"
        )
    else:
        raise BusinessError("VALIDATION_ERROR", "审核类型不合法")

    with get_connection() as conn:
        profile = query_one(conn, select_sql, (company_id,))
        if profile is None:
            raise BusinessError("NOT_FOUND", "企业不存在")

        cursor = conn.execute(
            update_sql,
            (
                decision,
                now_iso(),
                company_id,
                ReviewStatus.PENDING.value,
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "该记录已处理")
        conn.execute(
            """
            INSERT INTO review_logs
                (entity_type, entity_id, decision, note, reviewer_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entity_type, company_id, decision, note or None, admin_id, now_iso()),
        )

        return query_one(conn, f"{COMPANY_SELECT_SQL} WHERE c.id = ?", (company_id,))


def review_license(
    admin_id: int, company_id: int, decision: str, note: str | None = None
) -> dict:
    """第 1 层：企业资质审核。"""
    return _review(admin_id, company_id, "status", "company_license", decision, note)


def review_hr(
    admin_id: int, company_id: int, decision: str, note: str | None = None
) -> dict:
    """第 2 层：企业 HR 身份审核。"""
    return _review(admin_id, company_id, "hr_status", "company_hr", decision, note)


def set_company_active(admin_id: int, company_id: int, active: bool) -> None:
    """管理员启用 / 停用企业账号。"""
    auth.require_role(admin_id, Role.ADMIN)

    with get_connection() as conn:
        profile = query_one(
            conn, "SELECT user_id FROM companies WHERE id = ?", (company_id,)
        )
        if profile is None:
            raise BusinessError("NOT_FOUND", "企业不存在")
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if active else 0, profile["user_id"]),
        )


def list_pending_companies(admin_id: int, limit: int = 100) -> list[dict]:
    """管理员查看资质或 HR 待审核的企业。"""
    auth.require_role(admin_id, Role.ADMIN)
    with get_connection() as conn:
        return query_all(
            conn,
            f"""
            {COMPANY_SELECT_SQL}
            WHERE c.status = ? OR c.hr_status = ?
            ORDER BY c.created_at ASC
            LIMIT ?
            """,
            (
                ReviewStatus.PENDING.value,
                ReviewStatus.PENDING.value,
                limit,
            ),
        )


PUBLIC_COMPANY_SELECT_SQL = """
    SELECT c.id, c.name, c.logo_path, c.intro, c.culture, c.industry,
           c.company_size, c.funding_stage, c.city, c.benefits
    FROM companies c
    WHERE c.status = 'APPROVED'
"""


def list_public_companies(limit: int = 200) -> list[dict]:
    """学生端可见的已通过企业，用于企业主页与社区选择。"""
    with get_connection() as conn:
        return query_all(
            conn,
            f"{PUBLIC_COMPANY_SELECT_SQL} ORDER BY c.name ASC LIMIT ?",
            (limit,),
        )


def get_public_company(company_id: int) -> dict | None:
    """按 ID 获取已通过企业的公开品牌信息。"""
    with get_connection() as conn:
        return query_one(
            conn,
            f"{PUBLIC_COMPANY_SELECT_SQL} AND c.id = ?",
            (company_id,),
        )
