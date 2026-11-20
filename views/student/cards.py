"""学生端职位卡片：企业品牌信息、收藏、投递与详情跳转。"""

import html
from datetime import date, datetime

import streamlit as st

from core.config import CN_TZ, REVIEW_MIN_SAMPLE, SESSION_FLASH
from core.errors import BusinessError
from services import applications, favorites, jobs
from views import components


def urgent_label(job: dict) -> str:
    """急招剩余天数；已过期或未设置时返回空字符串。"""
    if not job.get("is_urgent") or not job.get("urgent_until"):
        return ""
    try:
        until = date.fromisoformat(job["urgent_until"])
    except (TypeError, ValueError):
        return ""
    days = (until - datetime.now(CN_TZ).date()).days
    return f"急招 · 剩 {days} 天" if days >= 0 else ""


def go_detail(job_id: int) -> None:
    """记录待查看职位并跳转详情页（query_params 无法跨 switch_page 保留）。"""
    st.session_state["selected_job_id"] = job_id
    st.query_params["job_id"] = str(job_id)
    st.switch_page("views/student/job_detail.py")


def _handle_favorite(user_id: int, job_id: int) -> None:
    try:
        favorites.toggle_favorite(user_id, job_id)
    except BusinessError as exc:
        st.error(exc.message)
    else:
        st.rerun()


def _handle_apply(user_id: int, job_id: int) -> None:
    try:
        applications.apply_to_job(user_id, job_id)
    except BusinessError as exc:
        st.error(exc.message)
    else:
        st.session_state[SESSION_FLASH] = "投递成功，可在「我的投递」查看进度"
        st.rerun()


def render_job_card(
    job: dict,
    user_id: int,
    can_apply: bool,
    favorited: bool,
    applied: bool,
    key_prefix: str = "job",
    show_pick: bool = False,
    reasons: list[str] | None = None,
) -> None:
    """渲染单个职位卡片；所有操作按钮都带唯一 key。"""
    job_id = job["id"]
    with st.container(border=True):
        logo_col, body_col, action_col = st.columns(
            [1, 4.4, 1.6], vertical_alignment="center"
        )
        with logo_col:
            components.render_logo(job, 54)
        with body_col:
            title, meta = components.job_title_line(job)
            st.html(
                f'<div class="cr-job-title">{html.escape(title)}</div>'
                f'<div class="cr-job-meta">{html.escape(meta)}</div>'
            )
            category = jobs.job_category(job.get("title") or "")
            tags = [category] if category else []
            urgent = urgent_label(job)
            if urgent:
                tags.insert(0, urgent)
            rating = job.get("company_rating")
            if rating and (job.get("company_review_count") or 0) >= REVIEW_MIN_SAMPLE:
                tags.append(f"口碑 {rating}")
            if applied:
                tags.append("✓ 已投递")
            if favorited:
                tags.append("★ 已收藏")
            components.chips(tags)
            if reasons:
                components.chips(reasons[:3], "cr-chip--accent")

        with action_col:
            if show_pick:
                st.checkbox(
                    "加入批量",
                    key=f"{key_prefix}_pick_{job_id}",
                    disabled=not can_apply or applied,
                )
            if st.button(
                "★ 已收藏" if favorited else "☆ 收藏",
                key=f"{key_prefix}_fav_{job_id}",
                use_container_width=True,
            ):
                _handle_favorite(user_id, job_id)
            if st.button(
                "✓ 已投递" if applied else "立即投递",
                key=f"{key_prefix}_apply_{job_id}",
                type="primary",
                use_container_width=True,
                disabled=not can_apply or applied,
            ):
                _handle_apply(user_id, job_id)
            if st.button(
                "查看详情",
                key=f"{key_prefix}_detail_{job_id}",
                use_container_width=True,
            ):
                go_detail(job_id)

        with st.expander("职位描述与任职要求"):
            st.write(job.get("description") or "暂无职位描述")
            if job.get("requirements"):
                st.markdown("**任职要求**")
                st.write(job["requirements"])
            brand = components.brand_fields(job)
            if brand["intro"]:
                st.markdown(f"**关于 {brand['name']}**")
                st.write(brand["intro"])
