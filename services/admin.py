"""管理端统计：平台概览指标与四类审核待办。"""

from core import auth
from core.config import ApplicationStatus, JobStatus, ResumeStatus, ReviewStatus, Role
from core.db import get_connection, query_one
from services import companies, jobs, students


def dashboard_counts(admin_id: int) -> dict:
    """返回 6 项核心指标。"""
    auth.require_role(admin_id, Role.ADMIN)

    with get_connection() as conn:
        pending_license = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM companies WHERE status = ?",
            (ReviewStatus.PENDING.value,),
        )["total"]
        pending_hr = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM companies WHERE hr_status = ?",
            (ReviewStatus.PENDING.value,),
        )["total"]
        pending_jobs = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM jobs WHERE status = ?",
            (JobStatus.PENDING.value,),
        )["total"]
        pending_resumes = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM resumes WHERE status = ?",
            (ResumeStatus.PENDING.value,),
        )["total"]
        total_applications = query_one(
            conn, "SELECT COUNT(*) AS total FROM applications"
        )["total"]
        hired = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM applications WHERE status = ?",
            (ApplicationStatus.HIRED.value,),
        )["total"]

    return {
        "pending_company_license": pending_license,
        "pending_company_hr": pending_hr,
        "pending_jobs": pending_jobs,
        "pending_resumes": pending_resumes,
        "total_applications": total_applications,
        "hired_applications": hired,
    }


def pending_queues(admin_id: int, limit: int = 20) -> dict:
    """返回三类待办列表（企业、职位、简历）。"""
    auth.require_role(admin_id, Role.ADMIN)
    return {
        "companies": companies.list_pending_companies(admin_id, limit),
        "jobs": jobs.list_pending_jobs(admin_id, limit),
        "resumes": students.list_pending_resumes(admin_id, limit),
    }


def list_approved_jobs(admin_id: int, limit: int = 200) -> list[dict]:
    """管理员查看已通过职位，用于设置推荐。"""
    auth.require_role(admin_id, Role.ADMIN)
    return jobs.search_jobs(limit=limit)


def moderation_counts(admin_id: int) -> dict:
    """v1.2 内容审核待办：文化帖、企业评分与小任务。"""
    auth.require_role(admin_id, Role.ADMIN)
    with get_connection() as conn:
        return {
            "culture_posts": query_one(
                conn,
                "SELECT COUNT(*) AS total FROM culture_posts WHERE status = ?",
                ("PENDING",),
            )["total"],
            "company_reviews": query_one(
                conn,
                "SELECT COUNT(*) AS total FROM company_reviews WHERE status = ?",
                ("PENDING",),
            )["total"],
            "micro_tasks": query_one(
                conn,
                "SELECT COUNT(*) AS total FROM micro_tasks WHERE status = ?",
                ("PENDING",),
            )["total"],
        }
