"""职位详情：完整职位信息、企业品牌展示与相似职位推荐。"""

import streamlit as st

from core.config import REVIEW_MIN_SAMPLE, SESSION_AUTH_USER, SESSION_FLASH
from core.errors import BusinessError
from services import analytics, applications, favorites, jobs, students
from views import components, theme
from views.student import cards

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

back_col, _ = st.columns([1, 4])
with back_col:
    if st.button("← 返回职位广场", use_container_width=True):
        st.switch_page("views/student/jobs.py")

raw_job_id = st.session_state.get("selected_job_id") or st.query_params.get("job_id")
try:
    job_id = int(raw_job_id)
except (TypeError, ValueError):
    st.warning("未指定职位，请从职位广场进入详情页。")
    st.stop()

job = jobs.get_public_job(job_id)
if job is None:
    st.warning("职位不存在或已关闭。")
    st.stop()

analytics.record_job_view(user["id"], job_id)

title, meta = components.job_title_line(job)
theme.section_title(title, meta)
category = jobs.job_category(job["title"])
tags = [tag for tag in [category, job["city"], job.get("salary") or "薪资面议"] if tag]
urgent = cards.urgent_label(job)
if urgent:
    tags.insert(0, urgent)
rating = job.get("company_rating")
if rating and (job.get("company_review_count") or 0) >= REVIEW_MIN_SAMPLE:
    tags.append(f"企业口碑 {rating}/5")
components.chips(tags)

resume = students.get_resume(user["id"])
can_apply = resume is not None and resume["status"] == "VERIFIED"
applied = job["id"] in applications.applied_job_ids(user["id"])
favorited = job["id"] in favorites.favorite_job_ids(user["id"])

body_col, side_col = st.columns([2.1, 1])

with body_col:
    with st.container(border=True):
        st.markdown("#### 职位描述")
        st.write(job["description"])
        if job.get("requirements"):
            st.markdown("#### 任职要求")
            st.write(job["requirements"])
    with st.container(border=True):
        components.company_brand_panel(job, compact=False)

with side_col:
    with st.container(border=True):
        st.markdown("**投递操作**")
        if not can_apply:
            st.warning("简历通过核查后才能投递。")
        if st.button(
            "★ 已收藏" if favorited else "☆ 收藏职位",
            use_container_width=True,
            key="detail_favorite",
        ):
            try:
                favorites.toggle_favorite(user["id"], job["id"])
            except BusinessError as exc:
                st.error(exc.message)
            else:
                st.rerun()
        if st.button(
            "✓ 已投递" if applied else "立即投递",
            type="primary",
            use_container_width=True,
            disabled=not can_apply or applied,
            key="detail_apply",
        ):
            try:
                applications.apply_to_job(user["id"], job["id"])
            except BusinessError as exc:
                st.error(exc.message)
            else:
                st.session_state[SESSION_FLASH] = "投递成功，可在「我的投递」查看进度"
                st.rerun()
        st.caption("投递后企业可查看你的简历快照，请确保简历信息与附件为最新版本。")
        if st.button("查看企业主页", use_container_width=True, key="detail_company"):
            st.session_state["selected_company_id"] = job["company_id"]
            st.switch_page("views/student/company.py")

similar = jobs.similar_jobs(job["id"], limit=4)
if similar:
    theme.section_title("相似职位推荐", "同类岗位 · 同城机会 · 关键词匹配")
    for item in similar:
        cards.render_job_card(
            item,
            user_id=user["id"],
            can_apply=can_apply,
            favorited=item["id"] in favorites.favorite_job_ids(user["id"]),
            applied=item["id"] in applications.applied_job_ids(user["id"]),
            key_prefix="similar",
        )
