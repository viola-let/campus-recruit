"""收藏服务：学生收藏 / 取消收藏职位，查看收藏列表。"""

from core import auth
from core.config import JobStatus, Role, now_iso
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError
from services.jobs import JOB_SELECT_SQL


def toggle_favorite(actor_id: int, job_id: int) -> bool:
    """切换收藏状态，返回切换后是否已收藏。"""
    auth.require_role(actor_id, Role.STUDENT)

    with get_connection() as conn:
        job = query_one(conn, "SELECT id, status FROM jobs WHERE id = ?", (job_id,))
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")

        existing = query_one(
            conn,
            "SELECT id FROM favorites WHERE student_id = ? AND job_id = ?",
            (actor_id, job_id),
        )
        if existing is not None:
            conn.execute("DELETE FROM favorites WHERE id = ?", (existing["id"],))
            return False

        if job["status"] != JobStatus.APPROVED.value:
            raise BusinessError("JOB_NOT_OPEN", "该职位已关闭或未通过审核")
        conn.execute(
            "INSERT INTO favorites (student_id, job_id, created_at) VALUES (?, ?, ?)",
            (actor_id, job_id, now_iso()),
        )
        return True


def favorite_job_ids(actor_id: int) -> set[int]:
    """返回学生收藏的职位 ID 集合，用于列表页标记。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        rows = query_all(
            conn,
            "SELECT job_id FROM favorites WHERE student_id = ?",
            (actor_id,),
        )
    return {row["job_id"] for row in rows}


def list_favorites(actor_id: int) -> list[dict]:
    """学生收藏的职位列表（按收藏时间倒序），只保留仍在招聘的职位。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        return query_all(
            conn,
            f"{JOB_SELECT_SQL} "
            "JOIN favorites f ON f.job_id = j.id "
            "WHERE f.student_id = ? AND j.status = ? "
            "ORDER BY f.created_at DESC",
            (actor_id, JobStatus.APPROVED.value),
        )
