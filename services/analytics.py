"""招聘效果看板：职位浏览、投递漏斗与企业平均响应时长。

浏览数据来自学生打开职位详情时写入的 job_views（同一学生对同一职位只计一次），
投递数据复用 applications，不修改现有投递状态机。

功能展示信息
------------
开发人员：CampusRecruit 平台研发组（负责人：待补充）
功能背景：企业只能看到候选人，无法判断职位曝光、转化与响应效率。
适用场景：招聘复盘、职位描述优化、招聘团队内部考核。
演示要点：学生浏览详情产生去重浏览 → 企业看板展示漏斗 → 对比不同岗位转化率。
"""

from datetime import datetime

from core import auth
from core.config import ApplicationStatus, JobStatus, Role, now_iso
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError


def record_job_view(actor_id: int, job_id: int) -> bool:
    """记录学生浏览职位；职位不可见时不记录。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        job = query_one(conn, "SELECT id, status FROM jobs WHERE id = ?", (job_id,))
        if job is None or job["status"] != JobStatus.APPROVED.value:
            return False
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO job_views (job_id, student_id, created_at)
            VALUES (?, ?, ?)
            """,
            (job_id, actor_id, now_iso()),
        )
        return cursor.rowcount == 1


def _response_hours(applications: list[dict]) -> float | None:
    """企业首次处理投递的平均时长（小时），不含仍为「已投递」的记录。"""
    durations = []
    for item in applications:
        if item["status"] == ApplicationStatus.SUBMITTED.value:
            continue
        try:
            created = datetime.fromisoformat(item["created_at"])
            updated = datetime.fromisoformat(item["updated_at"])
        except (TypeError, ValueError):
            continue
        durations.append((updated - created).total_seconds() / 3600)
    if not durations:
        return None
    return round(sum(durations) / len(durations), 1)


def company_dashboard(actor_id: int) -> dict:
    """企业招聘漏斗：每个职位的浏览、投递、面试、录用与转化率。"""
    auth.require_role(actor_id, Role.COMPANY)

    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None:
            raise BusinessError("NOT_FOUND", "企业资料不存在")

        jobs = query_all(
            conn,
            """
            SELECT id, title, status, created_at FROM jobs
            WHERE company_id = ? ORDER BY created_at DESC
            """,
            (company["id"],),
        )
        view_rows = query_all(
            conn,
            """
            SELECT jv.job_id, COUNT(*) AS total
            FROM job_views jv
            JOIN jobs j ON j.id = jv.job_id
            WHERE j.company_id = ?
            GROUP BY jv.job_id
            """,
            (company["id"],),
        )
        applications = query_all(
            conn,
            """
            SELECT a.job_id, a.status, a.created_at, a.updated_at
            FROM applications a
            JOIN jobs j ON j.id = a.job_id
            WHERE j.company_id = ?
            """,
            (company["id"],),
        )

    views = {row["job_id"]: row["total"] for row in view_rows}
    by_job: dict[int, list[dict]] = {}
    for item in applications:
        by_job.setdefault(item["job_id"], []).append(item)

    rows = []
    totals = {
        "views": 0,
        "applications": 0,
        "interviews": 0,
        "hired": 0,
        "response_hours": _response_hours(applications),
    }
    for job in jobs:
        job_apps = by_job.get(job["id"], [])
        view_count = views.get(job["id"], 0)
        hired = sum(
            1 for item in job_apps if item["status"] == ApplicationStatus.HIRED.value
        )
        interviews = sum(
            1
            for item in job_apps
            if item["status"]
            in {
                ApplicationStatus.SHORTLISTED.value,
                ApplicationStatus.HIRED.value,
            }
        )
        rows.append(
            {
                "id": job["id"],
                "title": job["title"],
                "status": job["status"],
                "views": view_count,
                "applications": len(job_apps),
                "interviews": interviews,
                "hired": hired,
                "conversion": round(100 * len(job_apps) / view_count, 1)
                if view_count
                else 0.0,
            }
        )
        totals["views"] += view_count
        totals["applications"] += len(job_apps)
        totals["interviews"] += interviews
        totals["hired"] += hired

    return {"jobs": rows, "totals": totals}
