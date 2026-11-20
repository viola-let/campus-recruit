"""企业口碑评分：实习 / 离职经历的员工对企业的结构化评价。

规则：
- 只有「在职 / 曾任职 / 实习过」身份可评分，每种身份对同一企业仅评一次；
- 五个维度 1-5 分，正文不少于 50 字，先审后发；
- 样本少于 3 条时不展示数值，仅提示「样本不足」，避免新企业被误伤。

功能展示信息
------------
开发人员：CampusRecruit 平台研发组（负责人：待补充）
功能背景：单一总分容易被极端评价带偏，企业缺少可横向比较的结构化口碑。
适用场景：求职者比较 offer、企业复盘雇主品牌、推荐算法引入口碑维度。
演示要点：五维评分 → 简历核查门槛 → 管理员审核 → 样本达标后展示并进入推荐理由。
"""

import sqlite3

from core import auth
from core.config import (
    REVIEW_MIN_CONTENT,
    REVIEW_MIN_SAMPLE,
    ContentStatus,
    EmploymentStatus,
    ReviewStatus,
    Role,
    now_iso,
)
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError
from services.content_guard import ensure_clean, is_verified_student

DIMENSIONS = ("growth", "salary", "intensity", "interview", "recommend")
ALLOWED_REVIEW_STATUSES = {
    EmploymentStatus.CURRENT.value,
    EmploymentStatus.FORMER.value,
    EmploymentStatus.INTERN.value,
}

REVIEW_SELECT_SQL = """
    SELECT r.id, r.company_id, r.user_id, r.employment_status, r.growth,
           r.salary, r.intensity, r.interview, r.recommend, r.content,
           r.status, r.created_at, r.updated_at, c.name AS company_name
    FROM company_reviews r
    JOIN companies c ON c.id = r.company_id
"""


def _overall(row: dict) -> float:
    """综合分：工作强度反向计分，越低强度得分越高。"""
    return (
        row["growth"]
        + row["salary"]
        + row["interview"]
        + row["recommend"]
        + (6 - row["intensity"])
    ) / 5


def submit_review(actor_id: int, company_id: int, payload: dict) -> dict:
    """学生提交企业评分，进入待审核队列。"""
    auth.require_role(actor_id, Role.STUDENT)
    if not is_verified_student(actor_id):
        raise BusinessError("RESUME_REQUIRED", "简历核查通过后才能评价企业")

    employment = (payload.get("employment_status") or "").strip().upper()
    content = (payload.get("content") or "").strip()
    if employment not in ALLOWED_REVIEW_STATUSES:
        raise BusinessError("FORBIDDEN", "只有在职、曾任职或实习过的用户才能评分")
    if len(content) < REVIEW_MIN_CONTENT:
        raise BusinessError(
            "VALIDATION_ERROR", f"评价正文不能少于 {REVIEW_MIN_CONTENT} 字"
        )
    ensure_clean(content)

    scores = {}
    for key in DIMENSIONS:
        try:
            value = int(payload.get(key))
        except (TypeError, ValueError) as exc:
            raise BusinessError("VALIDATION_ERROR", "评分必须为 1-5 的整数") from exc
        if not 1 <= value <= 5:
            raise BusinessError("VALIDATION_ERROR", "评分必须为 1-5 的整数")
        scores[key] = value

    timestamp = now_iso()
    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id, status FROM companies WHERE id = ?", (company_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业不存在")
        if company["status"] != ReviewStatus.APPROVED.value:
            raise BusinessError("INVALID_STATE", "该企业暂未开放评分")

        try:
            cursor = conn.execute(
                """
                INSERT INTO company_reviews
                    (company_id, user_id, employment_status, growth, salary,
                     intensity, interview, recommend, content, status,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    actor_id,
                    employment,
                    scores["growth"],
                    scores["salary"],
                    scores["intensity"],
                    scores["interview"],
                    scores["recommend"],
                    content,
                    ContentStatus.PENDING.value,
                    timestamp,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise BusinessError(
                "DUPLICATE_REVIEW", "该任职身份已评价过这家企业"
            ) from exc

        return query_one(
            conn, f"{REVIEW_SELECT_SQL} WHERE r.id = ?", (int(cursor.lastrowid),)
        )


def list_company_reviews(company_id: int, limit: int = 50) -> list[dict]:
    """企业主页展示的已通过评价。"""
    with get_connection() as conn:
        return query_all(
            conn,
            f"{REVIEW_SELECT_SQL} WHERE r.company_id = ? AND r.status = ? "
            "ORDER BY r.created_at DESC, r.id DESC LIMIT ?",
            (company_id, ContentStatus.APPROVED.value, limit),
        )


def rating_summary(company_id: int) -> dict:
    """聚合已通过评价；样本不足 3 条时 reliable=False。"""
    with get_connection() as conn:
        rows = query_all(
            conn,
            "SELECT * FROM company_reviews WHERE company_id = ? AND status = ?",
            (company_id, ContentStatus.APPROVED.value),
        )

    count = len(rows)
    if count == 0:
        return {
            "count": 0,
            "reliable": False,
            "average": None,
            "recommend_rate": None,
            "dimensions": {},
        }

    dimensions = {
        key: round(sum(row[key] for row in rows) / count, 1) for key in DIMENSIONS
    }
    return {
        "count": count,
        "reliable": count >= REVIEW_MIN_SAMPLE,
        "average": round(sum(_overall(row) for row in rows) / count, 1),
        "recommend_rate": round(
            100 * sum(1 for row in rows if row["recommend"] >= 4) / count
        ),
        "dimensions": dimensions,
    }


def list_company_reviews_for_owner(actor_id: int, limit: int = 100) -> list[dict]:
    """企业查看本企业评价（含待审核），便于了解学生反馈。"""
    auth.require_role(actor_id, Role.COMPANY)
    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")
        return query_all(
            conn,
            f"{REVIEW_SELECT_SQL} WHERE r.company_id = ? "
            "ORDER BY r.created_at DESC, r.id DESC LIMIT ?",
            (company["id"], limit),
        )


def list_my_reviews(actor_id: int, limit: int = 50) -> list[dict]:
    """学生查看自己提交的企业评分与审核状态。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        return query_all(
            conn,
            f"{REVIEW_SELECT_SQL} WHERE r.user_id = ? "
            "ORDER BY r.created_at DESC, r.id DESC LIMIT ?",
            (actor_id, limit),
        )


def list_pending_reviews(admin_id: int, limit: int = 100) -> list[dict]:
    """管理员待审核企业评分。"""
    auth.require_role(admin_id, Role.ADMIN)
    with get_connection() as conn:
        return query_all(
            conn,
            f"{REVIEW_SELECT_SQL} WHERE r.status = ? ORDER BY r.created_at ASC LIMIT ?",
            (ContentStatus.PENDING.value, limit),
        )


def review_review(admin_id: int, review_id: int, decision: str) -> dict:
    """管理员审核企业评分：通过或拒绝。"""
    auth.require_role(admin_id, Role.ADMIN)
    decision = (decision or "").strip().upper()
    if decision not in {ContentStatus.APPROVED.value, ContentStatus.REJECTED.value}:
        raise BusinessError("VALIDATION_ERROR", "审核结论不合法")

    with get_connection() as conn:
        review = query_one(
            conn, "SELECT id FROM company_reviews WHERE id = ?", (review_id,)
        )
        if review is None:
            raise BusinessError("NOT_FOUND", "评价不存在")
        cursor = conn.execute(
            """
            UPDATE company_reviews SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                decision,
                now_iso(),
                review_id,
                ContentStatus.PENDING.value,
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "该评价已处理")
        return query_one(conn, f"{REVIEW_SELECT_SQL} WHERE r.id = ?", (review_id,))
