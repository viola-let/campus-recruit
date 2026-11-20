"""企业文化交流区：浏览企业口碑、发布经验或提问、查看审核状态。"""

import streamlit as st

from core.config import (
    CONTENT_STATUS_LABELS,
    EMPLOYMENT_STATUS_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import companies, culture, reviews, students
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "企业文化交流区",
    "在职 / 曾任职 / 实习过的用户分享真实体验，匿名发布、先审后发、企业可官方回应。",
    badge="Company Culture",
)

components.demo_info(
    background="官方品牌介绍之外，求职者缺少员工视角的企业真实信息。",
    scenario="求职前了解团队氛围、福利兑现、培养机制与面试体验；离职员工反馈真实经历。",
    demo_points=[
        "任职状态区分在职 / 曾任职 / 实习过 / 未任职，未任职只能提问",
        "匿名发布前台显示「匿名用户」，后台保留账号便于追责",
        "先审后发 + 关键词红线，企业可对已通过帖子做一次官方回应",
    ],
)

company_list = companies.list_public_companies()
if not company_list:
    st.info("暂无已通过审核的企业，稍后再来看看。")
    st.stop()

labels = {item["id"]: item["name"] for item in company_list}
resume = students.get_resume(user["id"])
verified = resume is not None and resume["status"] == "VERIFIED"


def _badge(post: dict) -> str:
    status = EMPLOYMENT_STATUS_LABELS.get(post["employment_status"], "未知")
    if post["employment_status"] == "NONE":
        return "未任职 · 求职者"
    return f"{'已核验' if post['is_verified'] else '自述'} · {status}"


browse_tab, publish_tab, mine_tab = st.tabs(
    ["浏览企业口碑", "发布经验 / 提问", "我的发布"]
)

with browse_tab:
    company_id = st.selectbox(
        "选择企业",
        list(labels),
        format_func=lambda value: labels[value],
        key="culture_browse_company",
    )
    summary = reviews.rating_summary(company_id)
    if summary["count"] == 0:
        st.info("该企业暂无员工评分。")
    elif not summary["reliable"]:
        st.info(
            f"已有 {summary['count']} 条评价，样本少于 3 条暂不展示分数，避免误导。"
        )
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("综合口碑", f"{summary['average']} / 5")
        col2.metric("推荐率", f"{summary['recommend_rate']}%")
        col3.metric("评价数", summary["count"])
        dimensions = summary["dimensions"]
        st.caption(
            " · ".join(
                f"{label} {dimensions.get(key, '-')}"
                for key, label in (
                    ("growth", "成长"),
                    ("salary", "薪酬"),
                    ("intensity", "强度"),
                    ("interview", "面试"),
                )
            )
        )

    if st.button("查看企业主页", key="culture_company_page"):
        st.session_state["selected_company_id"] = company_id
        st.switch_page("views/student/company.py")

    st.divider()
    posts = culture.list_company_posts(company_id)
    st.markdown(f"### 共 {len(posts)} 条员工分享")
    if not posts:
        st.caption("还没有已通过的分享，欢迎发布第一条经验。")
    for post in posts:
        with st.container(border=True):
            st.markdown(f"**{post['title']}**")
            components.chips(
                [
                    _badge(post),
                    "经验分享" if post["topic"] == "experience" else "求职提问",
                ]
            )
            st.caption(f"{post['company_name']} · {post['created_at'][:10]}")
            st.write(post["content"])
            if post["official_reply"]:
                st.info(f"企业官方回应：{post['official_reply']}")

with publish_tab:
    st.caption(
        "简历已核查：发布经验将标记为「已核验」；否则显示「自述」。"
        if verified
        else "你的简历尚未核查，发布经验将标记为「自述」，建议先完成简历核查。"
    )
    if not verified:
        st.page_link("views/student/resume.py", label="去完善简历", icon="📄")

    with st.form("culture_post_form"):
        target_id = st.selectbox(
            "企业",
            list(labels),
            format_func=lambda value: labels[value],
            key="culture_publish_company",
        )
        employment_label = st.selectbox(
            "你的任职状态", list(EMPLOYMENT_STATUS_LABELS.values())
        )
        topic_label = st.selectbox("内容类型", ["经验分享", "求职提问"])
        title = st.text_input("标题", placeholder="如：后端实习三个月的真实体验")
        content = st.text_area(
            "正文",
            height=160,
            placeholder="经验分享不少于 30 字；提问不少于 10 字",
        )
        anonymous = st.checkbox("匿名发布（前台匿名，平台后台可追溯）", value=True)
        submitted = st.form_submit_button(
            "提交审核", type="primary", use_container_width=True
        )

    if submitted:
        employment = next(
            key
            for key, label in EMPLOYMENT_STATUS_LABELS.items()
            if label == employment_label
        )
        topic = "experience" if topic_label == "经验分享" else "question"
        try:
            culture.create_post(
                user["id"],
                target_id,
                {
                    "employment_status": employment,
                    "topic": topic,
                    "title": title,
                    "content": content,
                    "anonymous": anonymous,
                },
            )
        except BusinessError as exc:
            st.error(exc.message)
        else:
            st.session_state[SESSION_FLASH] = "内容已提交，审核通过后展示"
            st.rerun()

with mine_tab:
    my_posts = culture.list_my_posts(user["id"])
    if not my_posts:
        st.caption("还没有发布记录。")
    for post in my_posts:
        with st.container(border=True):
            st.markdown(f"**{post['title']}**")
            components.chips(
                [
                    CONTENT_STATUS_LABELS.get(post["status"], post["status"]),
                    _badge(post),
                ]
            )
            st.caption(f"{post['company_name']} · {post['created_at'][:10]}")
            st.write(post["content"])
            if post["status"] == "REJECTED":
                st.caption("未通过审核，可调整表述后重新发布。")
