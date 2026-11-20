"""UGC 内容安全与身份核验的公共规则。

文化交流、企业评分与小任务共用同一套红线校验，避免规则分散。

功能展示信息
------------
开发人员：CampusRecruit 平台研发组（负责人：待补充）
功能背景：多个 UGC 模块需要一致的内容红线与身份判断，重复实现容易遗漏。
适用场景：文化帖、企业评分、小任务发布与审核。
演示要点：发布含「刷单 / 押金」内容被即时拒绝；简历核查状态决定身份标签。
"""

from core.config import CONTENT_BLOCKLIST
from core.db import get_connection, query_one
from core.errors import BusinessError


def ensure_clean(*texts: str | None) -> None:
    """命中平台黑名单（刷单、押金、拉人头等）时拒绝发布。"""
    lowered = " ".join(text or "" for text in texts).lower()
    for word in CONTENT_BLOCKLIST:
        if word.lower() in lowered:
            raise BusinessError("CONTENT_BLOCKED", f"内容包含不允许的表述：{word}")


def is_verified_student(student_id: int) -> bool:
    """学生简历已核查即视为身份可核验，用于显示「已核验」标签。"""
    with get_connection() as conn:
        resume = query_one(
            conn,
            "SELECT status FROM resumes WHERE student_id = ?",
            (student_id,),
        )
    return bool(resume and resume["status"] == "VERIFIED")
