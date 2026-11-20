"""学生与简历服务：保存简历、附件、核查。

页面与 REST 路由只调用这里的函数，业务校验全部在本文件完成。
"""

from core import auth
from core.config import (
    RESUME_UPLOAD_DIR,
    ResumeStatus,
    Role,
    now_iso,
)
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError
from core.security import save_upload

RESUME_FIELDS = """
    id, student_id, real_name, phone, school, major, graduation_year,
    skills, summary, file_path, status, updated_at
"""

LATEST_RESUME_NOTE_SQL = """
    (SELECT note FROM review_logs
     WHERE entity_type = 'resume' AND entity_id = resumes.id
     ORDER BY id DESC LIMIT 1) AS review_note
"""


def get_resume(actor_id: int, student_id: int | None = None) -> dict | None:
    """查看简历：学生只能看本人，管理员可指定学生。"""
    actor = auth.get_user(actor_id)
    if actor is None:
        raise BusinessError("AUTH_INVALID_CREDENTIALS", "登录状态失效，请重新登录")

    if actor["role"] == Role.STUDENT.value:
        if student_id is not None and student_id != actor_id:
            raise BusinessError("FORBIDDEN", "无权限查看他人简历")
        target_id = actor_id
    elif actor["role"] == Role.ADMIN.value:
        if student_id is None:
            raise BusinessError("VALIDATION_ERROR", "请指定学生")
        target_id = student_id
    else:
        raise BusinessError("FORBIDDEN", "无权限执行该操作")

    with get_connection() as conn:
        return query_one(
            conn,
            f"SELECT {RESUME_FIELDS}, {LATEST_RESUME_NOTE_SQL} "
            "FROM resumes WHERE student_id = ?",
            (target_id,),
        )


def _validate_payload(payload: dict) -> dict:
    """校验简历字段，返回整理后的数据。"""
    real_name = (payload.get("real_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    school = (payload.get("school") or "").strip()
    major = (payload.get("major") or "").strip()
    skills = (payload.get("skills") or "").strip()
    summary = (payload.get("summary") or "").strip()

    for value, label in (
        (real_name, "姓名"),
        (phone, "手机号"),
        (school, "学校"),
        (major, "专业"),
    ):
        if not value:
            raise BusinessError("VALIDATION_ERROR", f"请填写{label}")

    try:
        graduation_year = int(payload.get("graduation_year"))
    except (TypeError, ValueError) as exc:
        raise BusinessError("VALIDATION_ERROR", "毕业年份必须是数字") from exc
    if not 2000 <= graduation_year <= 2100:
        raise BusinessError("VALIDATION_ERROR", "毕业年份需在 2000-2100 之间")

    return {
        "real_name": real_name,
        "phone": phone,
        "school": school,
        "major": major,
        "graduation_year": graduation_year,
        "skills": skills,
        "summary": summary,
    }


def save_resume(actor_id: int, payload: dict) -> dict:
    """保存简历；新增或修改后状态统一回到 PENDING。"""
    auth.require_role(actor_id, Role.STUDENT)
    data = _validate_payload(payload)
    timestamp = now_iso()

    with get_connection() as conn:
        existing = query_one(
            conn, "SELECT id FROM resumes WHERE student_id = ?", (actor_id,)
        )
        if existing is None:
            conn.execute(
                """
                INSERT INTO resumes
                    (student_id, real_name, phone, school, major, graduation_year,
                     skills, summary, file_path, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    actor_id,
                    data["real_name"],
                    data["phone"],
                    data["school"],
                    data["major"],
                    data["graduation_year"],
                    data["skills"],
                    data["summary"],
                    ResumeStatus.PENDING.value,
                    timestamp,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE resumes
                SET real_name = ?, phone = ?, school = ?, major = ?,
                    graduation_year = ?, skills = ?, summary = ?,
                    status = ?, updated_at = ?
                WHERE student_id = ?
                """,
                (
                    data["real_name"],
                    data["phone"],
                    data["school"],
                    data["major"],
                    data["graduation_year"],
                    data["skills"],
                    data["summary"],
                    ResumeStatus.PENDING.value,
                    timestamp,
                    actor_id,
                ),
            )

    return get_resume(actor_id)


def attach_resume_file(actor_id: int, filename: str, content: bytes) -> str:
    """保存简历附件并写回数据库，返回相对路径。"""
    auth.require_role(actor_id, Role.STUDENT)

    with get_connection() as conn:
        resume = query_one(
            conn, "SELECT id FROM resumes WHERE student_id = ?", (actor_id,)
        )
    if resume is None:
        raise BusinessError("VALIDATION_ERROR", "请先保存简历再上传附件")

    relative_path = save_upload(filename, content, RESUME_UPLOAD_DIR)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE resumes
            SET file_path = ?, status = ?, updated_at = ?
            WHERE student_id = ?
            """,
            (
                relative_path,
                ResumeStatus.PENDING.value,
                now_iso(),
                actor_id,
            ),
        )
    return relative_path


def list_pending_resumes(admin_id: int, limit: int = 100) -> list[dict]:
    """管理员查看待核查简历。"""
    auth.require_role(admin_id, Role.ADMIN)
    with get_connection() as conn:
        return query_all(
            conn,
            f"""
            SELECT {RESUME_FIELDS}, {LATEST_RESUME_NOTE_SQL}
            FROM resumes
            WHERE status = ?
            ORDER BY updated_at ASC
            LIMIT ?
            """,
            (ResumeStatus.PENDING.value, limit),
        )


def review_resume(
    admin_id: int, resume_id: int, decision: str, note: str | None = None
) -> dict:
    """管理员核查简历：只处理 PENDING，拒绝必须写理由。"""
    auth.require_role(admin_id, Role.ADMIN)

    decision = (decision or "").strip().upper()
    if decision in {"VERIFIED", "APPROVED"}:
        new_status = ResumeStatus.VERIFIED.value
        log_decision = "VERIFIED"
    elif decision == "REJECTED":
        new_status = ResumeStatus.REJECTED.value
        log_decision = "REJECTED"
    else:
        raise BusinessError("VALIDATION_ERROR", "审核结论不合法")

    note = (note or "").strip()
    if log_decision == "REJECTED" and not note:
        raise BusinessError("VALIDATION_ERROR", "拒绝时必须填写理由")

    with get_connection() as conn:
        resume = query_one(
            conn, "SELECT status FROM resumes WHERE id = ?", (resume_id,)
        )
        if resume is None:
            raise BusinessError("NOT_FOUND", "简历不存在")

        cursor = conn.execute(
            """
            UPDATE resumes SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                new_status,
                now_iso(),
                resume_id,
                ResumeStatus.PENDING.value,
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "该记录已处理")

        conn.execute(
            """
            INSERT INTO review_logs
                (entity_type, entity_id, decision, note, reviewer_id, created_at)
            VALUES ('resume', ?, ?, ?, ?, ?)
            """,
            (resume_id, log_decision, note or None, admin_id, now_iso()),
        )

        return query_one(
            conn,
            f"SELECT {RESUME_FIELDS}, {LATEST_RESUME_NOTE_SQL} "
            "FROM resumes WHERE id = ?",
            (resume_id,),
        )
