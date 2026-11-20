"""企业首页：审核状态、职位与候选人概览。"""

import streamlit as st

from core.config import REVIEW_STATUS_LABELS, SESSION_AUTH_USER
from services import applications, companies, jobs
from views import theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    f"欢迎，{user['display_name']}",
    "完成企业资质与 HR 审核后即可发布职位，品牌信息会展示给学生。",
    badge="Company Center",
)

profile = companies.get_profile(user["id"])

if profile is None:
    st.info("尚未创建企业资料，请先在「企业资料」填写。")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "企业资质", REVIEW_STATUS_LABELS.get(profile["status"], profile["status"])
    )
with col2:
    st.metric(
        "HR 审核",
        REVIEW_STATUS_LABELS.get(profile["hr_status"], profile["hr_status"]),
    )

my_jobs = jobs.list_company_jobs(user["id"])
candidates = applications.list_job_candidates(user["id"])
with col3:
    st.metric("本公司职位", len(my_jobs))
with col4:
    st.metric("收到投递", len(candidates))

st.divider()

if companies.can_publish_job(user["id"]):
    st.success("企业资质与 HR 均已通过，可以发布职位。")
    st.page_link("views/company/jobs.py", label="去发布职位", icon="📌")
else:
    st.warning("企业资质与 HR 审核都通过后才能发布职位。")
    st.page_link("views/company/profile.py", label="完善企业资料", icon="🏢")
    if profile["status"] == "REJECTED" and profile.get("license_note"):
        st.caption(f"企业资质审核备注：{profile['license_note']}")
    if profile["hr_status"] == "REJECTED" and profile.get("hr_note"):
        st.caption(f"HR 审核备注：{profile['hr_note']}")

st.subheader("待处理候选人")
pending = [
    item
    for item in candidates
    if item["status"] in {"SUBMITTED", "VIEWED", "SHORTLISTED"}
]
if not pending:
    st.caption("暂无待处理投递。")
else:
    st.write(f"共有 {len(pending)} 条待处理投递。")
    st.page_link("views/company/candidates.py", label="去处理候选人", icon="👥")
