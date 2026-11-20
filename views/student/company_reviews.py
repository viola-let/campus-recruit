"""企业评分：有实习 / 任职经历的学生对企业的结构化评价。"""

import streamlit as st

from core.config import (
    CONTENT_STATUS_LABELS,
    EMPLOYMENT_STATUS_LABELS,
    REVIEW_DIMENSION_LABELS,
    REVIEW_MIN_CONTENT,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import companies, reviews
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "企业评分",
    "仅在职、曾任职或实习过的用户可评价，多维度打分并附文字说明，先审后发。",
    badge="Company Rating",
)

components.demo_info(
    background="求职者需要可横向比较的企业口碑，单一总分容易被极端评价带偏。",
    scenario="拿到 offer 前比较企业成长性、薪酬福利、工作强度与面试体验。",
    demo_points=[
        "五维评分 + 不少于 50 字正文，简历核查后才可评价",
        "同一企业同一任职身份只能评一次，防止刷分",
        "样本少于 3 条不展示分数，达标后计入推荐算法的「企业口碑」理由",
    ],
)

company_list = companies.list_public_companies()
if not company_list:
    st.info("暂无已通过审核的企业。")
    st.stop()

labels = {item["id"]: item["name"] for item in company_list}
query_company = st.session_state.get("selected_company_id")
default_index = 0
if query_company in labels:
    default_index = list(labels).index(query_company)

tab_form, tab_mine = st.tabs(["提交评分", "我的评分"])

with tab_form:
    st.caption("每种任职身份对同一企业仅可评价一次；样本少于 3 条时平台不展示分数。")
    with st.form("company_review_form"):
        company_id = st.selectbox(
            "企业",
            list(labels),
            index=default_index,
            format_func=lambda value: labels[value],
        )
        employment_label = st.selectbox("任职身份", ["在职", "曾任职", "实习过"])
        st.write("评分维度（1 分最低，5 分最高）")
        col1, col2 = st.columns(2)
        with col1:
            growth = st.slider("成长空间", 1, 5, 4)
            salary = st.slider("薪酬福利", 1, 5, 4)
        with col2:
            intensity = st.slider("工作强度（越高越累）", 1, 5, 3)
            interview = st.slider("面试体验", 1, 5, 4)
        recommend = st.slider("推荐意愿", 1, 5, 4)
        content = st.text_area(
            "具体评价",
            height=150,
            placeholder=f"不少于 {REVIEW_MIN_CONTENT} 字，请描述真实经历",
        )
        submitted = st.form_submit_button(
            "提交审核", type="primary", use_container_width=True
        )

    if submitted:
        employment = next(
            key
            for key, label in EMPLOYMENT_STATUS_LABELS.items()
            if label == employment_label
        )
        try:
            reviews.submit_review(
                user["id"],
                company_id,
                {
                    "employment_status": employment,
                    "growth": growth,
                    "salary": salary,
                    "intensity": intensity,
                    "interview": interview,
                    "recommend": recommend,
                    "content": content,
                },
            )
        except BusinessError as exc:
            st.error(exc.message)
        else:
            st.session_state[SESSION_FLASH] = "评分已提交，审核通过后计入企业口碑"
            st.rerun()

with tab_mine:
    my_reviews = reviews.list_my_reviews(user["id"])
    if not my_reviews:
        st.caption("还没有提交过评分。")
    for item in my_reviews:
        with st.container(border=True):
            st.markdown(f"**{item['company_name']}**")
            components.chips(
                [
                    CONTENT_STATUS_LABELS.get(item["status"], item["status"]),
                    EMPLOYMENT_STATUS_LABELS.get(item["employment_status"], ""),
                ]
            )
            scores = " · ".join(
                f"{label} {item[key]}" for key, label in REVIEW_DIMENSION_LABELS.items()
            )
            st.caption(scores)
            st.write(item["content"])
