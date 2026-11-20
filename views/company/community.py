"""企业社区：回应员工帖子、查看本企业收到的口碑评分。"""

import streamlit as st

from core.config import (
    CONTENT_STATUS_LABELS,
    EMPLOYMENT_STATUS_LABELS,
    REVIEW_DIMENSION_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import companies, culture, reviews
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "企业社区",
    "对员工分享做一次官方回应，并查看学生对本企业的多维度评分。",
    badge="Employer Brand",
)

components.demo_info(
    background="员工评价一旦只有单向发声，容易形成信息失衡，企业需要正当回应渠道。",
    scenario="企业回应员工分享、澄清不实信息、查看本企业多维口碑。",
    demo_points=[
        "对已通过帖子可做一次官方回应，回应以独立样式展示",
        "可查看待审 / 已通过评分，但无法删除或修改学生评价",
        "评分与推荐算法联动，口碑成为企业长期信用资产",
    ],
)

profile = companies.get_profile(user["id"])
if profile is None:
    st.warning("企业资料不存在。")
    st.stop()

reply_tab, rating_tab = st.tabs(["员工分享与回应", "收到的评分"])

with reply_tab:
    posts = culture.list_company_posts_for_owner(user["id"])
    if not posts:
        st.info("暂无与本企业相关的已通过帖子。")
    for post in posts:
        with st.container(border=True):
            st.markdown(f"**{post['title']}**")
            status = EMPLOYMENT_STATUS_LABELS.get(post["employment_status"], "")
            components.chips(
                [
                    f"{'已核验' if post['is_verified'] else '自述'} · {status}",
                    "经验分享" if post["topic"] == "experience" else "求职提问",
                ]
            )
            st.caption(post["created_at"][:10])
            st.write(post["content"])
            if post["official_reply"]:
                st.info(f"已回应：{post['official_reply']}")
                continue
            with st.form(f"culture_reply_{post['id']}"):
                reply = st.text_input(
                    "官方回应（5-500 字）", key=f"culture_reply_text_{post['id']}"
                )
                submitted = st.form_submit_button("提交回应")
            if submitted:
                try:
                    culture.reply_to_post(user["id"], post["id"], reply)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "官方回应已发布"
                    st.rerun()

with rating_tab:
    summary = reviews.rating_summary(profile["id"])
    if summary["count"] == 0:
        st.info("暂无已通过的员工评分。")
    elif not summary["reliable"]:
        st.info(f"已有 {summary['count']} 条评价，样本少于 3 条暂不计算综合分。")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("综合口碑", f"{summary['average']} / 5")
        col2.metric("推荐率", f"{summary['recommend_rate']}%")
        col3.metric("评价数", summary["count"])
        st.caption(
            " · ".join(
                f"{label} {summary['dimensions'].get(key, '-')}"
                for key, label in REVIEW_DIMENSION_LABELS.items()
            )
        )

    st.divider()
    items = reviews.list_company_reviews_for_owner(user["id"])
    if not items:
        st.caption("还没有收到评分。")
    for item in items:
        with st.container(border=True):
            components.chips(
                [
                    CONTENT_STATUS_LABELS.get(item["status"], item["status"]),
                    EMPLOYMENT_STATUS_LABELS.get(item["employment_status"], ""),
                ]
            )
            st.caption(
                " · ".join(
                    f"{label} {item[key]}"
                    for key, label in REVIEW_DIMENSION_LABELS.items()
                )
            )
            st.write(item["content"])
