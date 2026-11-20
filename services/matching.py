"""候选人智能匹配：按岗位要求为投递候选人打分，并给出可解释理由。

评分与学生的智能推荐同源：技能命中为主，专业与城市偏好为辅，
分数只作为排序参考，页面同时展示命中原因，避免 HR 盲从模型。

功能展示信息
------------
开发人员：CampusRecruit 平台研发组（负责人：待补充）
功能背景：候选人按投递时间排列，HR 需要逐个打开简历才能判断匹配度。
适用场景：职位投递量较大时的初筛、批量筛选前的优先级排序。
演示要点：两位技能不同的候选人 → 匹配分排序 → 展示技能 / 专业 / 城市命中理由。
"""

import re

from core import auth
from core.config import Role
from services import applications, jobs

TOKEN_SPLIT_PATTERN = re.compile(r"[\s,，、;；/|·+]+")
MIN_TOKEN_LENGTH = 2


def _tokens(text: str | None) -> set[str]:
    return {
        token.strip().lower()
        for token in TOKEN_SPLIT_PATTERN.split(text or "")
        if len(token.strip()) >= MIN_TOKEN_LENGTH
    }


def _score(snapshot: dict, job: dict) -> tuple[float, list[str]]:
    text = " ".join(
        filter(
            None, [job.get("title"), job.get("description"), job.get("requirements")]
        )
    ).lower()
    score = 0.0
    reasons: list[str] = []

    skills = _tokens(snapshot.get("skills"))
    matched = sorted(token for token in skills if token in text)
    if matched:
        score += 10 * len(matched)
        reasons.append("技能匹配：" + "、".join(matched[:5]))

    major = (snapshot.get("major") or "").strip()
    if major and major.lower() in text:
        score += 6
        reasons.append(f"专业相关：{major}")

    city = job.get("city") or ""
    summary = (snapshot.get("summary") or "").lower()
    if city and city.lower() in summary:
        score += 3
        reasons.append(f"城市匹配：{city}")

    return score, reasons


def list_candidates_ranked(
    actor_id: int, filters: dict | None = None, limit: int = 100
) -> list[dict]:
    """返回带 match_score / match_reasons 的候选人列表，按匹配分倒序。"""
    auth.require_role(actor_id, Role.COMPANY)
    items = applications.list_job_candidates(actor_id, filters or {}, limit=limit)
    if not items:
        return []

    job_map = {job["id"]: job for job in jobs.list_company_jobs(actor_id, limit=200)}
    for item in items:
        job = job_map.get(item["job_id"])
        if job is None:
            item["match_score"] = 0.0
            item["match_reasons"] = []
            continue
        score, reasons = _score(item.get("resume") or {}, job)
        item["match_score"] = round(score, 1)
        item["match_reasons"] = reasons

    items.sort(key=lambda item: (-item["match_score"], item["updated_at"]))
    return items
