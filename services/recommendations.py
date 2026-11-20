"""智能推荐服务：基于简历画像为学生推荐匹配职位。

匹配思路（可解释、可复现）：
1. 技能命中：简历技能关键词出现在职位名称/描述/要求中，每命中一个加分；
2. 专业相关：专业名称出现在职位文本中；
3. 城市偏好：简历摘要中提及职位所在城市；
4. 平台推荐位：管理员设置推荐的职位加权。
最终按得分倒序返回，并附带命中原因，供页面直接展示。
"""

import re

from core import auth
from core.config import REVIEW_MIN_SAMPLE, Role
from core.db import get_connection, query_all
from core.errors import BusinessError
from services import jobs, students

TOKEN_SPLIT_PATTERN = re.compile(r"[\s,，、;；/|·+]+")
MIN_TOKEN_LENGTH = 2


def _tokens(text: str | None) -> set[str]:
    """把技能、摘要等文本拆成小写关键词集合。"""
    return {
        token.strip().lower()
        for token in TOKEN_SPLIT_PATTERN.split(text or "")
        if len(token.strip()) >= MIN_TOKEN_LENGTH
    }


def _job_text(job: dict) -> str:
    return " ".join(
        filter(
            None,
            [job["title"], job["description"], job["requirements"]],
        )
    ).lower()


def _score_job(job: dict, resume: dict) -> tuple[float, list[str]]:
    """计算单个职位的匹配分与命中原因。"""
    text = _job_text(job)
    score = 0.0
    reasons: list[str] = []

    skill_tokens = _tokens(resume.get("skills"))
    matched_skills = sorted(token for token in skill_tokens if token in text)
    if matched_skills:
        score += 10 * len(matched_skills)
        reasons.append("技能匹配：" + "、".join(matched_skills[:5]))

    major = (resume.get("major") or "").strip()
    if major and major.lower() in text:
        score += 6
        reasons.append(f"专业相关：{major}")

    city = job.get("city") or ""
    summary = (resume.get("summary") or "").lower()
    if city and city.lower() in summary:
        score += 3
        reasons.append(f"城市偏好：{city}")

    if job.get("is_featured"):
        score += 2
        reasons.append("平台推荐")

    rating = job.get("company_rating") or 0
    review_count = job.get("company_review_count") or 0
    if review_count >= REVIEW_MIN_SAMPLE and rating >= 4:
        score += 3
        reasons.append(f"企业口碑 {rating:.1f}/5")

    return score, reasons


def recommend_jobs(actor_id: int, limit: int = 10) -> list[dict]:
    """为学生推荐职位，排除已投递职位；无简历时给出明确错误。"""
    auth.require_role(actor_id, Role.STUDENT)

    resume = students.get_resume(actor_id)
    if resume is None:
        raise BusinessError("RESUME_REQUIRED", "请先完善简历，再获取智能推荐")

    with get_connection() as conn:
        applied = {
            row["job_id"]
            for row in query_all(
                conn,
                "SELECT job_id FROM applications WHERE student_id = ?",
                (actor_id,),
            )
        }

    candidates = jobs.search_jobs(limit=200)
    scored: list[tuple[float, list[str], dict]] = []
    for job in candidates:
        if job["id"] in applied:
            continue
        score, reasons = _score_job(job, resume)
        if score <= 0:
            continue
        scored.append((score, reasons, job))

    scored.sort(key=lambda item: (-item[0], item[2]["created_at"]))
    return [
        dict(job, match_score=round(score, 1), match_reasons=reasons)
        for score, reasons, job in scored[:limit]
    ]
