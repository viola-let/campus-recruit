"""投递服务：投递、我的投递、候选人查询、状态流转、附件下载。"""

import json
import sqlite3

from core import auth
from core.config import ApplicationStatus, JobStatus, ResumeStatus, Role, now_iso
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError
from core.security import resolve_upload_path

APPLICATION_SELECT_SQL = """
    SELECT a.id, a.job_id, j.title AS job_title, c.name AS company_name,
           a.student_id, u.display_name AS student_name, a.resume_id,
           a.resume_snapshot, a.resume_file_snapshot, a.status, a.feedback,
           a.created_at, a.updated_at
    FROM applications a
    JOIN jobs j ON j.id = a.job_id
    JOIN companies c ON c.id = j.company_id
    JOIN users u ON u.id = a.student_id
"""

# Spec 5.3：允许的投递状态流转
ALLOWED_TRANSITIONS = {
    ApplicationStatus.SUBMITTED.value: {
        ApplicationStatus.VIEWED.value,
        ApplicationStatus.REJECTED.value,
    },
    ApplicationStatus.VIEWED.value: {
        ApplicationStatus.SHORTLISTED.value,
        ApplicationStatus.REJECTED.value,
    },
    ApplicationStatus.SHORTLISTED.value: {
        ApplicationStatus.HIRED.value,
        ApplicationStatus.REJECTED.value,
    },
}


def apply_to_job(actor_id: int, job_id: int) -> dict:
    """学生投递职位：简历已核查、职位已通过、不可重复投递。"""
    auth.require_role(actor_id, Role.STUDENT)

    with get_connection() as conn:
        resume = query_one(
            conn, "SELECT * FROM resumes WHERE student_id = ?", (actor_id,)
        )
        if resume is None or resume["status"] != ResumeStatus.VERIFIED.value:
            raise BusinessError("RESUME_NOT_VERIFIED", "简历通过核查后才能投递")

        job = query_one(
            conn,
            "SELECT id, status FROM jobs WHERE id = ?",
            (job_id,),
        )
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")
        if job["status"] != JobStatus.APPROVED.value:
            raise BusinessError("JOB_NOT_OPEN", "该职位已关闭或未通过审核")

        existing = query_one(
            conn,
            "SELECT id FROM applications WHERE job_id = ? AND student_id = ?",
            (job_id, actor_id),
        )
        if existing is not None:
            raise BusinessError("DUPLICATE_APPLICATION", "请勿重复投递")

        snapshot = {
            key: resume[key]
            for key in (
                "id",
                "real_name",
                "phone",
                "school",
                "major",
                "graduation_year",
                "skills",
                "summary",
                "file_path",
                "status",
                "updated_at",
            )
        }
        timestamp = now_iso()
        try:
            cursor = conn.execute(
                """
                INSERT INTO applications
                    (job_id, student_id, resume_id, resume_snapshot,
                     resume_file_snapshot, status, feedback, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    job_id,
                    actor_id,
                    resume["id"],
                    json.dumps(snapshot, ensure_ascii=False),
                    resume["file_path"],
                    ApplicationStatus.SUBMITTED.value,
                    timestamp,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise BusinessError("DUPLICATE_APPLICATION", "请勿重复投递") from exc

        return query_one(
            conn,
            f"{APPLICATION_SELECT_SQL} WHERE a.id = ?",
            (int(cursor.lastrowid),),
        )


MAX_BATCH_APPLY = 20


def batch_apply_to_job(actor_id: int, job_ids: list[int]) -> dict:
    """学生批量投递：逐个投递并汇总成功/失败结果，单次最多 20 个职位。"""
    auth.require_role(actor_id, Role.STUDENT)

    unique_ids: list[int] = []
    for raw in job_ids or []:
        try:
            job_id = int(raw)
        except (TypeError, ValueError):
            continue
        if job_id not in unique_ids:
            unique_ids.append(job_id)

    if not unique_ids:
        raise BusinessError("VALIDATION_ERROR", "请选择要投递的职位")
    if len(unique_ids) > MAX_BATCH_APPLY:
        raise BusinessError(
            "VALIDATION_ERROR", f"单次最多投递 {MAX_BATCH_APPLY} 个职位"
        )

    succeeded: list[dict] = []
    failed: list[dict] = []
    for job_id in unique_ids:
        try:
            succeeded.append(apply_to_job(actor_id, job_id))
        except BusinessError as exc:
            failed.append({"job_id": job_id, "code": exc.code, "message": exc.message})

    return {
        "requested": len(unique_ids),
        "succeeded": succeeded,
        "failed": failed,
    }


def applied_job_ids(actor_id: int) -> set[int]:
    """返回学生已投递过的职位 ID 集合，用于列表页标记。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        rows = query_all(
            conn,
            "SELECT job_id FROM applications WHERE student_id = ?",
            (actor_id,),
        )
    return {row["job_id"] for row in rows}


def list_my_applications(actor_id: int) -> list[dict]:
    """学生查看本人投递（按时间倒序）。"""
    auth.require_role(actor_id, Role.STUDENT)
    with get_connection() as conn:
        return query_all(
            conn,
            f"{APPLICATION_SELECT_SQL} WHERE a.student_id = ? "
            "ORDER BY a.created_at DESC, a.id DESC",
            (actor_id,),
        )


def _parse_snapshot(snapshot: str | None) -> dict:
    try:
        return json.loads(snapshot or "{}")
    except (TypeError, ValueError):
        return {}


def list_job_candidates(
    actor_id: int, filters: dict | None = None, limit: int = 100
) -> list[dict]:
    """企业按条件查询投递到本公司职位的候选人。"""
    auth.require_role(actor_id, Role.COMPANY)
    filters = filters or {}

    with get_connection() as conn:
        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None:
            return []

        conditions = ["j.company_id = ?"]
        params: list = [company["id"]]

        job_id = filters.get("job_id")
        if job_id:
            conditions.append("a.job_id = ?")
            params.append(int(job_id))
        status = (filters.get("status") or "").strip().upper()
        if status:
            conditions.append("a.status = ?")
            params.append(status)

        rows = query_all(
            conn,
            f"{APPLICATION_SELECT_SQL} WHERE {' AND '.join(conditions)} "
            "ORDER BY a.updated_at DESC, a.id DESC",
            tuple(params),
        )

    school = (filters.get("school") or "").strip()
    major = (filters.get("major") or "").strip()
    results = []
    for row in rows:
        snapshot = _parse_snapshot(row["resume_snapshot"])
        if school and snapshot.get("school") != school:
            continue
        if major and snapshot.get("major") != major:
            continue
        row["resume"] = snapshot
        results.append(row)
        if len(results) >= limit:
            break
    return results


def update_status(
    actor_id: int,
    application_id: int,
    new_status: str,
    feedback: str | None = None,
) -> dict:
    """企业更新投递状态；仅允许 Spec 5.3 的流转。"""
    auth.require_role(actor_id, Role.COMPANY)

    new_status = (new_status or "").strip().upper()
    valid_status = {item.value for item in ApplicationStatus}
    if new_status not in valid_status:
        raise BusinessError("VALIDATION_ERROR", "投递状态不合法")

    feedback = (feedback or "").strip()
    if new_status == ApplicationStatus.REJECTED.value and not feedback:
        raise BusinessError("VALIDATION_ERROR", "拒绝候选人时必须填写反馈")

    with get_connection() as conn:
        application = query_one(
            conn,
            """
            SELECT a.id, a.status, j.company_id
            FROM applications a
            JOIN jobs j ON j.id = a.job_id
            WHERE a.id = ?
            """,
            (application_id,),
        )
        if application is None:
            raise BusinessError("NOT_FOUND", "投递记录不存在")

        company = query_one(
            conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
        )
        if company is None or application["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限处理其他公司的投递")

        allowed = ALLOWED_TRANSITIONS.get(application["status"], set())
        if new_status not in allowed:
            raise BusinessError("INVALID_STATE", "当前状态不允许该操作")

        cursor = conn.execute(
            """
            UPDATE applications
            SET status = ?, feedback = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                new_status,
                feedback or None,
                now_iso(),
                application_id,
                application["status"],
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "当前状态不允许该操作")
        return query_one(
            conn,
            f"{APPLICATION_SELECT_SQL} WHERE a.id = ?",
            (application_id,),
        )


def get_resume_file(actor_id: int, application_id: int) -> tuple[str, bytes]:
    """下载投递时的简历附件快照。"""
    user = auth.get_user(actor_id)
    if user is None:
        raise BusinessError("AUTH_INVALID_CREDENTIALS", "登录状态失效，请重新登录")

    with get_connection() as conn:
        application = query_one(
            conn,
            """
            SELECT a.resume_file_snapshot, j.company_id
            FROM applications a
            JOIN jobs j ON j.id = a.job_id
            WHERE a.id = ?
            """,
            (application_id,),
        )
    if application is None:
        raise BusinessError("NOT_FOUND", "投递记录不存在")

    if user["role"] == Role.COMPANY.value:
        with get_connection() as conn:
            company = query_one(
                conn, "SELECT id FROM companies WHERE user_id = ?", (actor_id,)
            )
        if company is None or application["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限查看该简历")
    elif user["role"] != Role.ADMIN.value:
        raise BusinessError("FORBIDDEN", "无权限执行该操作")

    relative_path = application["resume_file_snapshot"]
    if not relative_path:
        raise BusinessError("NOT_FOUND", "投递时未上传简历附件")

    path = resolve_upload_path(relative_path)
    if not path.is_file():
        raise BusinessError("NOT_FOUND", "简历附件不存在")
    return path.name, path.read_bytes()
