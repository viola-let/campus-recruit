"""内容审核：企业文化帖、企业评分与小任务的三合一审核队列。"""

import streamlit as st

from core.config import (
    EMPLOYMENT_STATUS_LABELS,
    REVIEW_DIMENSION_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import culture, micro_tasks, reviews
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "内容审核",
    "统一处理企业文化帖、企业评分与小任务，先审后发，保障内容真实合规。",
    badge="Content Moderation",
)

components.demo_info(
    background="UGC 内容与短期任务需要统一入口审核，避免分散在多个页面导致漏审。",
    scenario="管理员日常审核文化帖、企业评分与小任务，处理举报与违规内容。",
    demo_points=[
        "三类内容分页签展示，身份标签与评分维度一目了然",
        "通过 / 拒绝即时生效，已处理内容不再进入队列",
        "管理员首页同步展示三类待审计数，便于排优先级",
    ],
)

post_tab, review_tab, task_tab = st.tabs(["文化帖", "企业评分", "小任务"])

with post_tab:
    posts = culture.list_pending_posts(user["id"])
    st.caption(f"待审核 {len(posts)} 条")
    if not posts:
        st.info("暂无待审核文化帖。")
    for post in posts:
        with st.container(border=True):
            st.markdown(f"**{post['title']}**")
            status = EMPLOYMENT_STATUS_LABELS.get(post["employment_status"], "")
            components.chips(
                [
                    post["company_name"],
                    f"{'已核验' if post['is_verified'] else '自述'} · {status}",
                    "经验分享" if post["topic"] == "experience" else "求职提问",
                ]
            )
            st.write(post["content"])
            approve, reject = st.columns(2)
            if approve.button("通过", key=f"culture_ok_{post['id']}"):
                try:
                    culture.review_post(user["id"], post["id"], "APPROVED")
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "文化帖已通过"
                    st.rerun()
            if reject.button("拒绝", key=f"culture_no_{post['id']}"):
                try:
                    culture.review_post(user["id"], post["id"], "REJECTED")
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "文化帖已拒绝"
                    st.rerun()

with review_tab:
    pending_reviews = reviews.list_pending_reviews(user["id"])
    st.caption(f"待审核 {len(pending_reviews)} 条")
    if not pending_reviews:
        st.info("暂无待审核企业评分。")
    for item in pending_reviews:
        with st.container(border=True):
            st.markdown(f"**{item['company_name']}**")
            components.chips(
                [EMPLOYMENT_STATUS_LABELS.get(item["employment_status"], "")]
            )
            st.caption(
                " · ".join(
                    f"{label} {item[key]}"
                    for key, label in REVIEW_DIMENSION_LABELS.items()
                )
            )
            st.write(item["content"])
            approve, reject = st.columns(2)
            if approve.button("通过", key=f"review_ok_{item['id']}"):
                try:
                    reviews.review_review(user["id"], item["id"], "APPROVED")
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "评分已通过"
                    st.rerun()
            if reject.button("拒绝", key=f"review_no_{item['id']}"):
                try:
                    reviews.review_review(user["id"], item["id"], "REJECTED")
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "评分已拒绝"
                    st.rerun()

with task_tab:
    tasks = micro_tasks.list_pending_tasks(user["id"])
    st.caption(f"待审核 {len(tasks)} 条")
    if not tasks:
        st.info("暂无待审核任务。")
    for task in tasks:
        with st.container(border=True):
            st.markdown(f"**{task['title']}**")
            components.chips(
                [
                    task["company_name"],
                    task["city"],
                    task["reward"] or "报酬面议",
                    f"招募 {task['headcount']} 人",
                ]
            )
            if task["schedule"]:
                st.caption(f"时间：{task['schedule']}")
            st.write(task["description"])
            approve, reject = st.columns(2)
            if approve.button("通过", key=f"task_ok_{task['id']}"):
                try:
                    micro_tasks.review_task(user["id"], task["id"], "APPROVED")
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "任务已通过"
                    st.rerun()
            if reject.button("拒绝", key=f"task_no_{task['id']}"):
                try:
                    micro_tasks.review_task(user["id"], task["id"], "REJECTED")
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "任务已拒绝"
                    st.rerun()
