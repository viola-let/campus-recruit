"""企业文化交流区：经验分享、提问、管理员审核与企业官方回应。

规则：
- 只有「在职 / 曾任职 / 实习过」用户可以发布经验分享；
- 「未任职」用户只能提问，避免道听途说被当作内部信息；
- 匿名仅对前台生效，后台保留账号映射，便于违规追责；
- 所有帖子先审后发，企业可对已通过帖子做一次官方回应。

功能展示信息
------------
开发人员：CampusRecruit 平台研发组（负责人：待补充）
功能背景：官方品牌介绍无法覆盖团队氛围、福利兑现等真实体验，求职者信息不足。
适用场景：求职前调研企业、离职员工反馈经历、企业澄清不实信息。
演示要点：任职状态区分 → 匿名发布 → 管理员审核 → 企业官方回应。
"""

from datetime import datetime, timedelta

from core import auth
from core.config import (
    CN_TZ,
    EMPLOYMENT_STATUS_LABELS,
    EXPERIENCE_POST_INTERVAL_DAYS,
    POST_DAILY_LIMIT,
    POST_MIN_CONTENT,
    QUESTION_MIN_CONTENT,
    ContentStatus,
    EmploymentStatus,
    ReviewStatus,
    Role,
    now_iso,
)
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError
from services.content_guard import ensure_clean, is_verified_student

POST_SELECT_SQL = """
    SELECT p.id, p.company_id, p.user_id, p.employment_status, p.is_verified,
           p.is_anonymous, p.topic, p.title, p.content, p.status,
           p.official_reply, p.created_at, p.updated_at,
           c.name AS company_name, u.display_name AS author_name
    FROM culture_posts p
    JOIN companies c ON c.id = p.company_id
    JOIN users u ON u.id = p.user_id
"""

EXPERIENCE = "experience"
QUESTION = "question"


def _mask_author(row: dict) -> dict:
    """匿名帖不向前台暴露作者名称。"""
    if row.get("is_anonymous"):
        row["author_name"] = "匿名用户"
    return row


def _validate(company_id: int, payload: dict) -> dict:
    employment = (payload.get("employment_status") or "").strip().upper()
    topic = (payload.get("topic") or "").strip().lower()
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()

    if employment not in EMPLOYMENT_STATUS_LABELS:
        raise BusinessError("VALIDATION_ERROR", "请选择有效的任职状态")
    if topic not in {EXPERIENCE, QUESTION}:
        raise BusinessError("VALIDATION_ERROR", "内容类型不合法")
    ensure_clean(title, content)
    if employment == EmploymentStatus.NONE.value and topic == EXPERIENCE:
        raise BusinessError("FORBIDDEN", "未任职用户只能提问，不能发布内部经验")
    if not 5 <= len(title) <= 60:
        raise BusinessError("VALIDATION_ERROR", "标题需在 5-60 字之间")
    min_length = POST_MIN_CONTENT if topic == EXPERIENCE else QUESTION_MIN_CONTENT
    if len(content) < min_length:
        raise BusinessError("VALIDATION_ERROR", f"正文不能少于 {min_length} 字")

    return {
        "company_id": int(company_id),
        "employment_status": employment,
        "topic": topic,
        "title": title,
        "content": content,
        "is_anonymous": 1 if payload.get("anonymous", True) else 0,
    }


def create_post(actor_id: int, company_id: int, payload: dict) -> dict:
    """学生发布企业文化帖子，进入待审核队列。"""
    auth.require_role(actor_id, Role.STUDENT)
    data = _validate(company_id, payload)
    timestamp = now_iso()
    day_prefix = timestamp[:10]
    verified = data[
        "employment_status"
    ] != EmploymentStatus.NONE.value and is_verified_student(actor_id)

    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id, status FROM companies WHERE id = ?", (company_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业不存在")
        if company["status"] != ReviewStatus.APPROVED.value:
            raise BusinessError("INVALID_STATE", "该企业暂未开放交流")

        if data["topic"] == EXPERIENCE:
            cutoff = (
                datetime.now(CN_TZ) - timedelta(days=EXPERIENCE_POST_INTERVAL_DAYS)
            ).isoformat(timespec="seconds")
            recent = query_one(
                conn,
                """
                SELECT id FROM culture_posts
                WHERE user_id = ? AND company_id = ? AND topic = ?
                  AND created_at >= ?
                """,
                (actor_id, company_id, EXPERIENCE, cutoff),
            )
            if recent is not None:
                raise BusinessError(
                    "DUPLICATE_CONTENT",
                    f"同一企业 {EXPERIENCE_POST_INTERVAL_DAYS} 天内只能发布一次经验",
                )

        daily = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM culture_posts "
            "WHERE user_id = ? AND substr(created_at, 1, 10) = ?",
            (actor_id, day_prefix),
        )["total"]
        if daily >= POST_DAILY_LIMIT:
            raise BusinessError(
                "RATE_LIMITED", f"每天最多发布 {POST_DAILY_LIMIT} 条内容"
            )

        cursor = conn.execute(
            """
            INSERT INTO culture_posts
                (company_id, user_id, employment_status, is_verified,
                 is_anonymous, topic, title, content, status,
                 official_reply, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                company_id,
                actor_id,
                data["employment_status"],
                1 if verified else 0,
                data["is_anonymous"],
                data["topic"],
                data["title"],
                data["content"],
                ContentStatus.PENDING.value,
                timestamp,
                timestamp,
            ),
        )
        row = query_one(
            conn, f"{POST_SELECT_SQL} WHERE p.id = ?", (int(cursor.lastrowid),)
        )
    return _mask_author(row)


def list_company_posts(company_id: int, limit: int = 50) -> list[dict]:
    """企业主页展示的已通过帖子。"""
    with get_connection() as conn:
        rows = query_all(
            conn,
            f"{POST_SELECT_SQL} WHERE p.company_id = ? AND p.status = ? "
            "ORDER BY p.created_at DESC, p.id DESC LIMIT ?",
            (company_id, ContentStatus.APPROVED.value, limit),
        )
    return [_mask_author(row) for row in rows]


def list_my_posts(actor_id: int, limit: int = 50) -> list[dict]:
    """学生查看自己发布的内容与审核状态。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        return query_all(
            conn,
            f"{POST_SELECT_SQL} WHERE p.user_id = ? "
            "ORDER BY p.created_at DESC, p.id DESC LIMIT ?",
            (actor_id, limit),
        )


def list_company_posts_for_owner(actor_id: int, limit: int = 50) -> list[dict]:
    """企业查看与本企业相关的已通过帖子，用于官方回应。"""
    auth.require_role(actor_id, Role.COMPANY)
    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")
        rows = query_all(
            conn,
            f"{POST_SELECT_SQL} WHERE p.company_id = ? AND p.status = ? "
            "ORDER BY p.created_at DESC LIMIT ?",
            (company["id"], ContentStatus.APPROVED.value, limit),
        )
    return [_mask_author(row) for row in rows]


def list_pending_posts(admin_id: int, limit: int = 100) -> list[dict]:
    """管理员待审核文化帖。"""
    auth.require_role(admin_id, Role.ADMIN)
    with get_connection() as conn:
        rows = query_all(
            conn,
            f"{POST_SELECT_SQL} WHERE p.status = ? ORDER BY p.created_at ASC LIMIT ?",
            (ContentStatus.PENDING.value, limit),
        )
    return rows


def review_post(admin_id: int, post_id: int, decision: str) -> dict:
    """管理员审核文化帖：通过或拒绝，只处理待审核内容。"""
    auth.require_role(admin_id, Role.ADMIN)
    decision = (decision or "").strip().upper()
    if decision not in {ContentStatus.APPROVED.value, ContentStatus.REJECTED.value}:
        raise BusinessError("VALIDATION_ERROR", "审核结论不合法")

    with get_connection() as conn:
        post = query_one(conn, "SELECT id FROM culture_posts WHERE id = ?", (post_id,))
        if post is None:
            raise BusinessError("NOT_FOUND", "帖子不存在")
        cursor = conn.execute(
            """
            UPDATE culture_posts SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                decision,
                now_iso(),
                post_id,
                ContentStatus.PENDING.value,
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "该内容已处理")
        return _mask_author(
            query_one(conn, f"{POST_SELECT_SQL} WHERE p.id = ?", (post_id,))
        )


def reply_to_post(actor_id: int, post_id: int, reply: str) -> dict:
    """企业对本企业相关帖子做一次官方回应。"""
    auth.require_role(actor_id, Role.COMPANY)
    reply = (reply or "").strip()
    if not 5 <= len(reply) <= 500:
        raise BusinessError("VALIDATION_ERROR", "官方回应需在 5-500 字之间")
    ensure_clean(reply)

    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")

        post = query_one(
            conn,
            "SELECT id, company_id, status, official_reply FROM culture_posts "
            "WHERE id = ?",
            (post_id,),
        )
        if post is None:
            raise BusinessError("NOT_FOUND", "帖子不存在")
        if post["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限回应其他企业的帖子")
        if post["status"] != ContentStatus.APPROVED.value:
            raise BusinessError("INVALID_STATE", "帖子通过审核后才能回应")
        if post["official_reply"]:
            raise BusinessError("INVALID_STATE", "该帖子已有官方回应")

        conn.execute(
            """
            UPDATE culture_posts SET official_reply = ?, updated_at = ?
            WHERE id = ?
            """,
            (reply, now_iso(), post_id),
        )
        return _mask_author(
            query_one(conn, f"{POST_SELECT_SQL} WHERE p.id = ?", (post_id,))
        )
