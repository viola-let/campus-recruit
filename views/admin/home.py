"""管理端概览：6 项核心指标与审核待办。"""

import streamlit as st

from core.config import (
    JOB_STATUS_LABELS,
    RESUME_STATUS_LABELS,
    SESSION_AUTH_USER,
)
from services import admin
from views import theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "平台概览",
    "集中查看审核待办与平台核心指标，保障招聘流程顺畅运行。",
    badge="Admin Console",
)

counts = admin.dashboard_counts(user["id"])
moderation = admin.moderation_counts(user["id"])

row1 = st.columns(3)
row1[0].metric("待审企业资质", counts["pending_company_license"])
row1[1].metric("待审企业 HR", counts["pending_company_hr"])
row1[2].metric("待审职位", counts["pending_jobs"])

row2 = st.columns(3)
row2[0].metric("待核查简历", counts["pending_resumes"])
row2[1].metric("投递总数", counts["total_applications"])
row2[2].metric("已录用", counts["hired_applications"])

st.divider()
row3 = st.columns(3)
row3[0].metric("待审文化帖", moderation["culture_posts"])
row3[1].metric("待审企业评分", moderation["company_reviews"])
row3[2].metric("待审小任务", moderation["micro_tasks"])

st.divider()

link1, link2, link3, link4 = st.columns(4)
with link1:
    st.page_link("views/admin/moderation.py", label="内容审核", icon="🛡️")
with link2:
    st.page_link("views/admin/companies.py", label="企业审核", icon="🏢")
with link3:
    st.page_link("views/admin/jobs.py", label="职位审核", icon="📌")
with link4:
    st.page_link("views/admin/resumes.py", label="简历核查", icon="📄")

st.divider()
st.subheader("最新待办")

queues = admin.pending_queues(user["id"], limit=5)

st.write("**待审企业**")
if queues["companies"]:
    for item in queues["companies"]:
        st.write(f"- {item['name']} · 资质：{item['status']} · HR：{item['hr_status']}")
else:
    st.caption("暂无待审企业。")

st.write("**待审职位**")
if queues["jobs"]:
    for item in queues["jobs"]:
        label = JOB_STATUS_LABELS.get(item["status"], item["status"])
        st.write(f"- {item['title']}（{item['company_name']}）· {label}")
else:
    st.caption("暂无待审职位。")

st.write("**待核查简历**")
if queues["resumes"]:
    for item in queues["resumes"]:
        label = RESUME_STATUS_LABELS.get(item["status"], item["status"])
        st.write(f"- {item['real_name']} · {item['school']} · {label}")
else:
    st.caption("暂无待核查简历。")
