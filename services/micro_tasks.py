"""小任务兼职：任务发布、审核、报名与企业查看报名名单。

合规边界：
- 平台只做信息展示，不托管资金、不参与结算；
- 发布与审核双重拦截刷单、押金、垫付、拉人头等高风险表述；
- 仅四审通过企业可发布，学生采用轻量报名制，不进入投递与简历快照流程。

功能展示信息
------------
开发人员：CampusRecruit 平台研发组（负责人：待补充）
功能背景：短期用工需求混在实习岗位中，既影响匹配效率也放大诈骗风险。
适用场景：展会协助、活动执行、问卷访问等 1-3 天短期任务。
演示要点：企业发布 → 关键词拦截 → 管理员审核 → 学生报名 → 企业查看名单并结束任务。
"""

import sqlite3

from core import auth
from core.config import MicroTaskStatus, Role, now_iso
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError
from services import companies
from services.content_guard import ensure_clean

TASK_SELECT_SQL = """
    SELECT t.id, t.company_id, t.title, t.description, t.city, t.reward,
           t.schedule, t.headcount, t.status, t.created_at, t.updated_at,
           c.name AS company_name, c.logo_path AS company_logo_path,
           (SELECT COUNT(*) FROM task_signups s WHERE s.task_id = t.id)
               AS signup_count
    FROM micro_tasks t
    JOIN companies c ON c.id = t.company_id
"""


def _validate(payload: dict) -> dict:
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    city = (payload.get("city") or "").strip()
    reward = (payload.get("reward") or "").strip()
    schedule = (payload.get("schedule") or "").strip()

    ensure_clean(title, description, city, reward, schedule)
    if not 4 <= len(title) <= 60:
        raise BusinessError("VALIDATION_ERROR", "任务名称需在 4-60 字之间")
    if len(description) < 30:
        raise BusinessError("VALIDATION_ERROR", "任务说明不能少于 30 字")
    if not city:
        raise BusinessError("VALIDATION_ERROR", "请填写任务城市")
    try:
        headcount = int(payload.get("headcount") or 1)
    except (TypeError, ValueError) as exc:
        raise BusinessError("VALIDATION_ERROR", "招募人数必须是数字") from exc
    if not 1 <= headcount <= 100:
        raise BusinessError("VALIDATION_ERROR", "招募人数需在 1-100 之间")

    return {
        "title": title,
        "description": description,
        "city": city,
        "reward": reward,
        "schedule": schedule,
        "headcount": headcount,
    }


def create_task(actor_id: int, payload: dict) -> dict:
    """企业发布小任务，进入待审核队列。"""
    auth.require_role(actor_id, Role.COMPANY)
    if not companies.can_publish_job(actor_id):
        raise BusinessError("FORBIDDEN", "企业资质与 HR 审核都通过后才能发布任务")
    data = _validate(payload)

    timestamp = now_iso()
    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")
        cursor = conn.execute(
            """
            INSERT INTO micro_tasks
                (company_id, title, description, city, reward, schedule,
                 headcount, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company["id"],
                data["title"],
                data["description"],
                data["city"],
                data["reward"] or None,
                data["schedule"] or None,
                data["headcount"],
                MicroTaskStatus.PENDING.value,
                timestamp,
                timestamp,
            ),
        )
        return query_one(
            conn, f"{TASK_SELECT_SQL} WHERE t.id = ?", (int(cursor.lastrowid),)
        )


def list_open_tasks(limit: int = 50) -> list[dict]:
    """学生端展示的招募中任务。"""
    with get_connection() as conn:
        return query_all(
            conn,
            f"{TASK_SELECT_SQL} WHERE t.status = ? "
            "ORDER BY t.created_at DESC, t.id DESC LIMIT ?",
            (MicroTaskStatus.APPROVED.value, limit),
        )


def list_company_tasks(actor_id: int, limit: int = 100) -> list[dict]:
    """企业查看自己发布的任务。"""
    auth.require_role(actor_id, Role.COMPANY)
    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")
        return query_all(
            conn,
            f"{TASK_SELECT_SQL} WHERE t.company_id = ? "
            "ORDER BY t.created_at DESC LIMIT ?",
            (company["id"], limit),
        )


def list_pending_tasks(admin_id: int, limit: int = 100) -> list[dict]:
    """管理员待审核任务。"""
    auth.require_role(admin_id, Role.ADMIN)
    with get_connection() as conn:
        return query_all(
            conn,
            f"{TASK_SELECT_SQL} WHERE t.status = ? ORDER BY t.created_at ASC LIMIT ?",
            (MicroTaskStatus.PENDING.value, limit),
        )


def review_task(admin_id: int, task_id: int, decision: str) -> dict:
    """管理员审核任务：通过或拒绝，只处理待审核任务。"""
    auth.require_role(admin_id, Role.ADMIN)
    decision = (decision or "").strip().upper()
    allowed = {MicroTaskStatus.APPROVED.value, MicroTaskStatus.REJECTED.value}
    if decision not in allowed:
        raise BusinessError("VALIDATION_ERROR", "审核结论不合法")

    with get_connection() as conn:
        task = query_one(conn, "SELECT id FROM micro_tasks WHERE id = ?", (task_id,))
        if task is None:
            raise BusinessError("NOT_FOUND", "任务不存在")
        cursor = conn.execute(
            """
            UPDATE micro_tasks SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                decision,
                now_iso(),
                task_id,
                MicroTaskStatus.PENDING.value,
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "该任务已处理")
        return query_one(conn, f"{TASK_SELECT_SQL} WHERE t.id = ?", (task_id,))


def signup_task(actor_id: int, task_id: int) -> dict:
    """学生报名小任务：需登录、名额未满、不可重复报名。"""
    auth.require_role(actor_id, Role.STUDENT)

    with get_connection() as conn:
        task = query_one(
            conn,
            "SELECT id, status, headcount FROM micro_tasks WHERE id = ?",
            (task_id,),
        )
        if task is None:
            raise BusinessError("NOT_FOUND", "任务不存在")
        if task["status"] != MicroTaskStatus.APPROVED.value:
            raise BusinessError("INVALID_STATE", "该任务已结束或未通过审核")

        existing = query_one(
            conn,
            "SELECT id FROM task_signups WHERE task_id = ? AND student_id = ?",
            (task_id, actor_id),
        )
        if existing is not None:
            raise BusinessError("DUPLICATE_SIGNUP", "请勿重复报名")

        signed = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM task_signups WHERE task_id = ?",
            (task_id,),
        )["total"]
        if signed >= task["headcount"]:
            raise BusinessError("TASK_FULL", "该任务名额已满")

        try:
            conn.execute(
                """
                INSERT INTO task_signups (task_id, student_id, created_at)
                VALUES (?, ?, ?)
                """,
                (task_id, actor_id, now_iso()),
            )
        except sqlite3.IntegrityError as exc:
            raise BusinessError("DUPLICATE_SIGNUP", "请勿重复报名") from exc

        return query_one(
            conn,
            """
            SELECT s.id, s.task_id, t.title, t.city, t.reward, s.created_at
            FROM task_signups s
            JOIN micro_tasks t ON t.id = s.task_id
            WHERE s.task_id = ? AND s.student_id = ?
            """,
            (task_id, actor_id),
        )


def my_signups(actor_id: int, limit: int = 50) -> list[dict]:
    """学生查看本人报名记录。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        return query_all(
            conn,
            """
            SELECT s.id, s.task_id, s.created_at, t.title, t.city, t.reward,
                   t.schedule, t.status, c.name AS company_name
            FROM task_signups s
            JOIN micro_tasks t ON t.id = s.task_id
            JOIN companies c ON c.id = t.company_id
            WHERE s.student_id = ?
            ORDER BY s.created_at DESC LIMIT ?
            """,
            (actor_id, limit),
        )


def task_signups(actor_id: int, task_id: int) -> list[dict]:
    """企业查看本企业任务的报名名单。"""
    auth.require_role(actor_id, Role.COMPANY)
    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        task = query_one(
            conn, "SELECT id, company_id FROM micro_tasks WHERE id = ?", (task_id,)
        )
        if company is None or task is None:
            raise BusinessError("NOT_FOUND", "任务不存在")
        if task["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限查看其他企业的报名")
        return query_all(
            conn,
            """
            SELECT s.id, s.created_at, u.display_name, u.email
            FROM task_signups s
            JOIN users u ON u.id = s.student_id
            WHERE s.task_id = ?
            ORDER BY s.created_at ASC
            """,
            (task_id,),
        )


def close_task(actor_id: int, task_id: int) -> dict:
    """企业结束任务，学生端不再展示。"""
    auth.require_role(actor_id, Role.COMPANY)
    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id, status FROM companies WHERE user_id = ?", (actor_id,)
        )
        task = query_one(
            conn,
            "SELECT id, company_id, status FROM micro_tasks WHERE id = ?",
            (task_id,),
        )
        if company is None or task is None:
            raise BusinessError("NOT_FOUND", "任务不存在")
        if task["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限操作其他企业的任务")
        if task["status"] not in {
            MicroTaskStatus.APPROVED.value,
            MicroTaskStatus.PENDING.value,
        }:
            raise BusinessError("INVALID_STATE", "当前状态不允许结束任务")
        conn.execute(
            "UPDATE micro_tasks SET status = ?, updated_at = ? WHERE id = ?",
            (MicroTaskStatus.CLOSED.value, now_iso(), task_id),
        )
        return query_one(conn, f"{TASK_SELECT_SQL} WHERE t.id = ?", (task_id,))
