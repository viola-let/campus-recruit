"""企业主页：品牌信息、员工口碑、在招职位与经验分享的聚合页。"""

import streamlit as st

from core.config import (
    EMPLOYMENT_STATUS_LABELS,
    REVIEW_DIMENSION_LABELS,
    SESSION_AUTH_USER,
)
from services import (
    applications,
    companies,
    culture,
    favorites,
    jobs,
    reviews,
    students,
)
from views import components
from views.student import cards

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

back_col, _ = st.columns([1, 4])
with back_col:
    if st.button("← 返回", use_container_width=True):
        st.switch_page("views/student/jobs.py")

raw_company_id = st.session_state.get("selected_company_id") or st.query_params.get(
    "company_id"
)
try:
    company_id = int(raw_company_id)
except (TypeError, ValueError):
    st.warning("未指定企业，请从职位详情页进入。")
    st.stop()

company = companies.get_public_company(company_id)
if company is None:
    st.warning("企业不存在或未通过审核。")
    st.stop()

components.company_brand_panel(company)
components.demo_info(
    background="品牌信息、在招职位与员工口碑分散在不同页面，求职者需要一站式判断企业。",
    scenario="投递前快速了解企业品牌、口碑、在招岗位与员工真实分享。",
    demo_points=[
        "顶部展示官方品牌与口碑综合分",
        "「在招职位」可直接收藏 / 投递 / 查看详情",
        "「员工分享」「员工评分」与官方介绍形成对照",
    ],
)

summary = reviews.rating_summary(company_id)
if summary["count"] == 0:
    st.caption("暂无员工评分。")
elif not summary["reliable"]:
    st.caption(f"已有 {summary['count']} 条评价，样本少于 3 条暂不展示分数。")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("综合口碑", f"{summary['average']} / 5")
    col2.metric("推荐率", f"{summary['recommend_rate']}%")
    col3.metric("评价数", summary["count"])

job_tab, culture_tab, review_tab = st.tabs(["在招职位", "员工分享", "员工评分"])

with job_tab:
    company_jobs = jobs.search_jobs(company_id=company_id, limit=50)
    if not company_jobs:
        st.info("该企业暂无在招职位。")
    resume = students.get_resume(user["id"])
    can_apply = resume is not None and resume["status"] == "VERIFIED"
    favorite_ids = favorites.favorite_job_ids(user["id"])
    applied_ids = applications.applied_job_ids(user["id"])
    for job in company_jobs:
        cards.render_job_card(
            job,
            user_id=user["id"],
            can_apply=can_apply,
            favorited=job["id"] in favorite_ids,
            applied=job["id"] in applied_ids,
            key_prefix="company_page",
        )

with culture_tab:
    posts = culture.list_company_posts(company_id)
    if not posts:
        st.info("该企业还没有员工分享。")
    for post in posts:
        with st.container(border=True):
            st.markdown(f"**{post['title']}**")
            status = EMPLOYMENT_STATUS_LABELS.get(post["employment_status"], "")
            components.chips(
                [f"{'已核验' if post['is_verified'] else '自述'} · {status}"]
            )
            st.caption(post["created_at"][:10])
            st.write(post["content"])
            if post["official_reply"]:
                st.info(f"企业官方回应：{post['official_reply']}")

with review_tab:
    company_reviews = reviews.list_company_reviews(company_id)
    if not company_reviews:
        st.info("该企业还没有员工评分。")
    for item in company_reviews:
        with st.container(border=True):
            status = EMPLOYMENT_STATUS_LABELS.get(item["employment_status"], "")
            components.chips([status])
            st.caption(
                " · ".join(
                    f"{label} {item[key]}"
                    for key, label in REVIEW_DIMENSION_LABELS.items()
                )
            )
            st.write(item["content"])
