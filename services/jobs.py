"""职位服务：发布、检索、编辑、关闭、审核与推荐。"""

import re
from datetime import datetime, timedelta

from core import auth
from core.config import (
    CN_TZ,
    URGENT_MAX_DAYS,
    URGENT_MAX_RATIO,
    JobStatus,
    JobType,
    ReviewStatus,
    Role,
    now_iso,
)
from core.db import get_connection, query_all, query_one
from core.errors import BusinessError

JOB_SELECT_SQL = """
    SELECT j.id, j.company_id, c.name AS company_name, j.title, j.job_type,
           j.city, j.salary, j.description, j.requirements, j.status,
           j.is_featured, j.is_urgent, j.urgent_until,
           j.created_at, j.updated_at,
           c.logo_path AS company_logo_path, c.intro AS company_intro,
           c.culture AS company_culture, c.industry AS company_industry,
           c.company_size AS company_size, c.funding_stage AS company_funding,
           c.city AS company_city, c.benefits AS company_benefits,
           (SELECT ROUND(AVG((r.growth + r.salary + r.interview + r.recommend
                              + (6 - r.intensity)) / 5.0), 1)
            FROM company_reviews r
            WHERE r.company_id = c.id AND r.status = 'APPROVED')
               AS company_rating,
           (SELECT COUNT(*) FROM company_reviews r
            WHERE r.company_id = c.id AND r.status = 'APPROVED')
               AS company_review_count,
           (SELECT note FROM review_logs
            WHERE entity_type = 'job' AND entity_id = j.id
            ORDER BY id DESC LIMIT 1) AS review_note
    FROM jobs j
    JOIN companies c ON c.id = j.company_id
"""

CATEGORY_PATTERN = re.compile(r"【([^】]+)】")
KEYWORD_SPLIT_PATTERN = re.compile(r"[\s,，、;；/]+")


def job_category(title: str) -> str:
    """从“【技术】Python 后端工程师”中提取岗位类别。"""
    match = CATEGORY_PATTERN.search(title or "")
    return match.group(1) if match else ""


def _keyword_tokens(keyword: str) -> list[str]:
    return [token for token in KEYWORD_SPLIT_PATTERN.split(keyword or "") if token]


def _title_tokens(title: str) -> list[str]:
    cleaned = CATEGORY_PATTERN.sub(" ", title or "")
    tokens = []
    for token in KEYWORD_SPLIT_PATTERN.split(cleaned):
        token = token.strip("（）()·-—_")
        if len(token) >= 2:
            tokens.append(token)
    return tokens


def _get_company_for_actor(conn, actor_id: int) -> dict:
    """取当前企业账号对应的企业资料。"""
    company = query_one(conn, "SELECT * FROM companies WHERE user_id = ?", (actor_id,))
    if company is None:
        raise BusinessError("NOT_FOUND", "企业资料不存在，请先完善企业资料")
    return company


def _get_job(conn, job_id: int) -> dict | None:
    return query_one(conn, f"{JOB_SELECT_SQL} WHERE j.id = ?", (job_id,))


def can_publish(company: dict) -> bool:
    """企业资质与 HR 审核都为 APPROVED 时才可发布职位。"""
    return (
        company["status"] == ReviewStatus.APPROVED.value
        and company["hr_status"] == ReviewStatus.APPROVED.value
    )


def _validate_payload(payload: dict) -> dict:
    title = (payload.get("title") or "").strip()
    job_type = (payload.get("job_type") or "").strip().upper()
    city = (payload.get("city") or "").strip()
    salary = (payload.get("salary") or "").strip()
    description = (payload.get("description") or "").strip()
    requirements = (payload.get("requirements") or "").strip()

    if not title:
        raise BusinessError("VALIDATION_ERROR", "请填写职位名称")
    if job_type not in {item.value for item in JobType}:
        raise BusinessError("VALIDATION_ERROR", "职位类型不合法")
    if not city:
        raise BusinessError("VALIDATION_ERROR", "请填写工作城市")
    if len(description) < 20:
        raise BusinessError("VALIDATION_ERROR", "职位描述不能少于 20 字")

    return {
        "title": title,
        "job_type": job_type,
        "city": city,
        "salary": salary,
        "description": description,
        "requirements": requirements,
    }


def create_job(actor_id: int, payload: dict) -> dict:
    """企业发布职位，创建后为 PENDING。"""
    auth.require_role(actor_id, Role.COMPANY)
    data = _validate_payload(payload)

    with get_connection() as conn:
        company = _get_company_for_actor(conn, actor_id)
        if not can_publish(company):
            raise BusinessError("FORBIDDEN", "企业资质与 HR 审核都通过后才能发布职位")
        timestamp = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO jobs
                (company_id, title, job_type, city, salary, description,
                 requirements, status, is_featured, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                company["id"],
                data["title"],
                data["job_type"],
                data["city"],
                data["salary"] or None,
                data["description"],
                data["requirements"] or None,
                JobStatus.PENDING.value,
                timestamp,
                timestamp,
            ),
        )
        return _get_job(conn, int(cursor.lastrowid))


def update_job(actor_id: int, job_id: int, payload: dict) -> dict:
    """企业修改职位，修改后回到 PENDING 重新审核。"""
    auth.require_role(actor_id, Role.COMPANY)
    data = _validate_payload(payload)

    with get_connection() as conn:
        company = _get_company_for_actor(conn, actor_id)
        job = _get_job(conn, job_id)
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")
        if job["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限操作其他企业的职位")
        if job["status"] == JobStatus.CLOSED.value:
            raise BusinessError("INVALID_STATE", "已关闭的职位请先重新开放")

        conn.execute(
            """
            UPDATE jobs
            SET title = ?, job_type = ?, city = ?, salary = ?,
                description = ?, requirements = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data["title"],
                data["job_type"],
                data["city"],
                data["salary"] or None,
                data["description"],
                data["requirements"] or None,
                JobStatus.PENDING.value,
                now_iso(),
                job_id,
            ),
        )
        return _get_job(conn, job_id)


def close_job(actor_id: int, job_id: int) -> None:
    """企业关闭职位，学生端不再展示。"""
    auth.require_role(actor_id, Role.COMPANY)

    with get_connection() as conn:
        company = _get_company_for_actor(conn, actor_id)
        job = _get_job(conn, job_id)
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")
        if job["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限操作其他企业的职位")
        if job["status"] not in {
            JobStatus.PENDING.value,
            JobStatus.APPROVED.value,
        }:
            raise BusinessError("INVALID_STATE", "当前状态不允许关闭")

        cursor = conn.execute(
            """
            UPDATE jobs SET status = ?, updated_at = ?
            WHERE id = ? AND status IN (?, ?)
            """,
            (
                JobStatus.CLOSED.value,
                now_iso(),
                job_id,
                JobStatus.PENDING.value,
                JobStatus.APPROVED.value,
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "当前状态不允许关闭")


def reopen_job(actor_id: int, job_id: int) -> dict:
    """企业重新开放已关闭职位，状态回到 PENDING。"""
    auth.require_role(actor_id, Role.COMPANY)

    with get_connection() as conn:
        company = _get_company_for_actor(conn, actor_id)
        job = _get_job(conn, job_id)
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")
        if job["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限操作其他企业的职位")
        if job["status"] != JobStatus.CLOSED.value:
            raise BusinessError("INVALID_STATE", "只有已关闭职位可以重新开放")

        cursor = conn.execute(
            """
            UPDATE jobs SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (
                JobStatus.PENDING.value,
                now_iso(),
                job_id,
                JobStatus.CLOSED.value,
            ),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "只有已关闭职位可以重新开放")
        return _get_job(conn, job_id)


SORT_OPTIONS = {
    "featured": "j.is_featured DESC, j.created_at DESC",
    "latest": "j.created_at DESC",
    "salary": "j.salary DESC",
}


def get_public_job(job_id: int) -> dict | None:
    """学生端查看职位详情：只返回已通过且未关闭的职位。"""
    with get_connection() as conn:
        return query_one(
            conn,
            f"{JOB_SELECT_SQL} WHERE j.id = ? AND j.status = ?",
            (job_id, JobStatus.APPROVED.value),
        )


def search_jobs(
    keyword: str | None = None,
    city: str | None = None,
    job_type: str | None = None,
    category: str | None = None,
    search_field: str = "all",
    sort: str = "featured",
    limit: int = 200,
    company_id: int | None = None,
    only_urgent: bool = False,
) -> list[dict]:
    """学生职位广场：关键词精准搜索 + 多维筛选与排序。

    keyword 支持空格/逗号分隔的多个关键词，多个关键词之间为 AND 关系；
    search_field="title" 时只匹配职位名称，否则同时匹配名称与描述。
    only_urgent=True 时只返回仍在急招有效期内的职位。
    """
    conditions = ["j.status = ?"]
    params: list = [JobStatus.APPROVED.value]

    tokens = _keyword_tokens(keyword or "")
    city = (city or "").strip()
    job_type = (job_type or "").strip().upper()
    category = (category or "").strip()

    for token in tokens:
        like = f"%{token}%"
        if search_field == "title":
            conditions.append("j.title LIKE ?")
            params.append(like)
        else:
            conditions.append(
                "(j.title LIKE ? OR j.description LIKE ? "
                "OR IFNULL(j.requirements, '') LIKE ?)"
            )
            params.extend([like, like, like])
    if city:
        conditions.append("j.city = ?")
        params.append(city)
    if job_type:
        conditions.append("j.job_type = ?")
        params.append(job_type)
    if category:
        conditions.append("j.title LIKE ?")
        params.append(f"%【{category}】%")
    if company_id:
        conditions.append("j.company_id = ?")
        params.append(int(company_id))
    if only_urgent:
        conditions.append("j.is_urgent = 1 AND j.urgent_until >= ?")
        params.append(now_iso()[:10])

    order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS["featured"])
    sql = (
        f"{JOB_SELECT_SQL} WHERE {' AND '.join(conditions)} ORDER BY {order_by} LIMIT ?"
    )
    params.append(limit)

    with get_connection() as conn:
        return query_all(conn, sql, tuple(params))


def similar_jobs(job_id: int, limit: int = 5) -> list[dict]:
    """相似职位：同类目、同城市的职位优先，再按标题关键词重合度排序。"""
    with get_connection() as conn:
        base = query_one(
            conn,
            "SELECT id, title, city, company_id FROM jobs WHERE id = ?",
            (job_id,),
        )
        if base is None:
            return []

        candidates = query_all(
            conn,
            f"{JOB_SELECT_SQL} WHERE j.status = ? AND j.id != ? "
            "ORDER BY j.created_at DESC LIMIT 200",
            (JobStatus.APPROVED.value, job_id),
        )

    base_category = job_category(base["title"])
    base_tokens = set(_title_tokens(base["title"]))

    scored: list[tuple[float, dict]] = []
    for job in candidates:
        category_match = bool(base_category) and (
            job_category(job["title"]) == base_category
        )
        overlap = base_tokens & set(_title_tokens(job["title"]))
        if not category_match and not overlap:
            continue

        score = 0.0
        if category_match:
            score += 5
        if base["city"] and job["city"] == base["city"]:
            score += 3
        score += 2 * len(overlap)
        if job["company_id"] == base["company_id"]:
            score += 1
        scored.append((score, job))

    scored.sort(key=lambda item: (-item[0], item[1]["created_at"]))
    return [dict(job, match_score=score) for score, job in scored[:limit]]


def list_company_jobs(actor_id: int, limit: int = 100) -> list[dict]:
    """企业查看本公司全部职位。"""
    auth.require_role(actor_id, Role.COMPANY)
    with get_connection() as conn:
        company = _get_company_for_actor(conn, actor_id)
        return query_all(
            conn,
            f"{JOB_SELECT_SQL} WHERE j.company_id = ? "
            "ORDER BY j.created_at DESC LIMIT ?",
            (company["id"], limit),
        )


def list_pending_jobs(admin_id: int, limit: int = 100) -> list[dict]:
    """管理员查看待审核职位。"""
    auth.require_role(admin_id, Role.ADMIN)
    with get_connection() as conn:
        return query_all(
            conn,
            f"{JOB_SELECT_SQL} WHERE j.status = ? ORDER BY j.created_at ASC LIMIT ?",
            (JobStatus.PENDING.value, limit),
        )


def review_job(
    admin_id: int, job_id: int, decision: str, note: str | None = None
) -> dict:
    """管理员审核职位：只处理 PENDING，拒绝必须写理由。"""
    auth.require_role(admin_id, Role.ADMIN)

    decision = (decision or "").strip().upper()
    if decision not in {JobStatus.APPROVED.value, JobStatus.REJECTED.value}:
        raise BusinessError("VALIDATION_ERROR", "审核结论不合法")
    note = (note or "").strip()
    if decision == JobStatus.REJECTED.value and not note:
        raise BusinessError("VALIDATION_ERROR", "拒绝时必须填写理由")

    with get_connection() as conn:
        job = _get_job(conn, job_id)
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")

        cursor = conn.execute(
            """
            UPDATE jobs SET status = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (decision, now_iso(), job_id, JobStatus.PENDING.value),
        )
        if cursor.rowcount != 1:
            raise BusinessError("INVALID_STATE", "该记录已处理")

        conn.execute(
            """
            INSERT INTO review_logs
                (entity_type, entity_id, decision, note, reviewer_id, created_at)
            VALUES ('job', ?, ?, ?, ?, ?)
            """,
            (job_id, decision, note or None, admin_id, now_iso()),
        )
        return _get_job(conn, job_id)


def set_featured(admin_id: int, job_id: int, featured: bool) -> None:
    """管理员设置推荐；只有已通过职位可以推荐。"""
    auth.require_role(admin_id, Role.ADMIN)

    with get_connection() as conn:
        job = _get_job(conn, job_id)
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")
        if job["status"] != JobStatus.APPROVED.value:
            raise BusinessError("INVALID_STATE", "只有已通过职位可以设置推荐")

        conn.execute(
            "UPDATE jobs SET is_featured = ?, updated_at = ? WHERE id = ?",
            (1 if featured else 0, now_iso(), job_id),
        )


def set_urgent(actor_id: int, job_id: int, days: int) -> dict:
    """企业设置急招：最长 30 天，且急招岗位不超过在招岗位的 30%。"""
    auth.require_role(actor_id, Role.COMPANY)

    try:
        days = int(days)
    except (TypeError, ValueError) as exc:
        raise BusinessError("VALIDATION_ERROR", "急招天数必须是数字") from exc
    if not 1 <= days <= URGENT_MAX_DAYS:
        raise BusinessError(
            "VALIDATION_ERROR", f"急招天数需在 1-{URGENT_MAX_DAYS} 天之间"
        )

    with get_connection() as conn:
        company = _get_company_for_actor(conn, actor_id)
        job = query_one(
            conn,
            "SELECT id, company_id, status, is_urgent FROM jobs WHERE id = ?",
            (job_id,),
        )
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")
        if job["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限操作其他企业的职位")
        if job["status"] != JobStatus.APPROVED.value:
            raise BusinessError("INVALID_STATE", "只有已通过审核的职位可以设置急招")

        approved_count = query_one(
            conn,
            "SELECT COUNT(*) AS total FROM jobs WHERE company_id = ? AND status = ?",
            (company["id"], JobStatus.APPROVED.value),
        )["total"]
        urgent_count = query_one(
            conn,
            """
            SELECT COUNT(*) AS total FROM jobs
            WHERE company_id = ? AND status = ? AND is_urgent = 1
            """,
            (company["id"], JobStatus.APPROVED.value),
        )["total"]
        cap = max(1, int(approved_count * URGENT_MAX_RATIO))
        if not job["is_urgent"] and urgent_count + 1 > cap:
            raise BusinessError(
                "URGENT_LIMIT",
                f"急招岗位最多占在招岗位的 {int(URGENT_MAX_RATIO * 100)}%",
            )

        urgent_until = (datetime.now(CN_TZ) + timedelta(days=days)).date().isoformat()
        conn.execute(
            """
            UPDATE jobs SET is_urgent = 1, urgent_until = ?, updated_at = ?
            WHERE id = ?
            """,
            (urgent_until, now_iso(), job_id),
        )
        return _get_job(conn, job_id)


def cancel_urgent(actor_id: int, job_id: int) -> dict:
    """企业取消急招标记。"""
    auth.require_role(actor_id, Role.COMPANY)

    with get_connection() as conn:
        company = _get_company_for_actor(conn, actor_id)
        job = query_one(
            conn,
            "SELECT id, company_id FROM jobs WHERE id = ?",
            (job_id,),
        )
        if job is None:
            raise BusinessError("NOT_FOUND", "职位不存在")
        if job["company_id"] != company["id"]:
            raise BusinessError("FORBIDDEN", "无权限操作其他企业的职位")

        conn.execute(
            """
            UPDATE jobs SET is_urgent = 0, urgent_until = NULL, updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), job_id),
        )
        return _get_job(conn, job_id)
