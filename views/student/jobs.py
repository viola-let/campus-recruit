"""职位广场：关键词精准搜索、多维筛选、排序与批量投递。"""

import streamlit as st

from core.config import (
    JOB_CATEGORIES,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import applications, favorites, jobs, students
from views import theme
from views.student import cards

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "职位广场",
    "多关键词组合搜索、按类别与城市精准筛选，选中多个职位即可一键批量投递。",
    badge="Job Discovery",
)

resume = students.get_resume(user["id"])
can_apply = resume is not None and resume["status"] == "VERIFIED"
if not can_apply:
    st.warning("简历通过核查后才能投递职位，请先完善并等待核查。")

with st.form("student_jobs_filter"):
    row1 = st.columns([2.4, 1.2])
    with row1[0]:
        keyword = st.text_input(
            "关键词",
            placeholder="支持多个关键词，用空格或逗号分隔，例如：Python 后端",
        )
    with row1[1]:
        scope_label = st.selectbox("搜索范围", ["全部字段", "仅职位名称"])

    row2 = st.columns(4)
    with row2[0]:
        city = st.text_input("城市", placeholder="如：杭州")
    with row2[1]:
        type_label = st.selectbox("类型", ["全部", "校招", "实习"])
    with row2[2]:
        category_label = st.selectbox("岗位类别", ["全部", *JOB_CATEGORIES])
    with row2[3]:
        sort_label = st.selectbox("排序", ["推荐优先", "最新发布", "薪资优先"])

    st.form_submit_button("搜索职位", type="primary", use_container_width=True)

job_type = {"校招": "CAMPUS", "实习": "INTERN"}.get(type_label)
search_field = "title" if scope_label == "仅职位名称" else "all"
sort_key = {"推荐优先": "featured", "最新发布": "latest", "薪资优先": "salary"}[
    sort_label
]

results = jobs.search_jobs(
    keyword=keyword,
    city=city,
    job_type=job_type,
    category=None if category_label == "全部" else category_label,
    search_field=search_field,
    sort=sort_key,
)

favorite_ids = favorites.favorite_job_ids(user["id"])
applied_ids = applications.applied_job_ids(user["id"])

st.markdown(f"### 共找到 {len(results)} 个职位")
if favorite_ids or applied_ids:
    st.caption(f"已收藏 {len(favorite_ids)} 个 · 已投递 {len(applied_ids)} 个")

# 批量投递选区：用版本号重置复选框状态
batch_version = st.session_state.get("student_batch_version", 0)
key_prefix = f"jobs{batch_version}"

if can_apply and results:
    with st.container(border=True):
        bar1, bar2 = st.columns([3, 1])
        with bar1:
            st.markdown("**批量投递**")
            st.caption("勾选下方职位后点击按钮，单次最多投递 20 个职位。")
        with bar2:
            if st.button(
                "🚀 批量投递已选",
                type="primary",
                use_container_width=True,
                key=f"{key_prefix}_batch_submit",
            ):
                selected = [
                    job["id"]
                    for job in results
                    if st.session_state.get(f"{key_prefix}_pick_{job['id']}")
                ]
                try:
                    result = applications.batch_apply_to_job(user["id"], selected)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    summary = (
                        f"批量投递完成：成功 {len(result['succeeded'])} 个，"
                        f"失败 {len(result['failed'])} 个"
                    )
                    if result["failed"]:
                        reasons = "；".join(
                            item["message"] for item in result["failed"][:2]
                        )
                        summary += f"（{reasons}）"
                    st.session_state[SESSION_FLASH] = summary
                    st.session_state["student_batch_version"] = batch_version + 1
                    st.rerun()

if not results:
    st.info("没有符合条件的职位，试试减少关键词或放宽筛选条件。")
    st.stop()

for job in results:
    cards.render_job_card(
        job,
        user_id=user["id"],
        can_apply=can_apply,
        favorited=job["id"] in favorite_ids,
        applied=job["id"] in applied_ids,
        key_prefix=key_prefix,
        show_pick=can_apply,
    )
