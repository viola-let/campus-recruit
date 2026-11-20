"""学生首页：简历状态、投递概览与快捷入口。"""

import streamlit as st

from core.config import (
    APPLICATION_STATUS_LABELS,
    RESUME_STATUS_LABELS,
    SESSION_AUTH_USER,
)
from services import applications, students
from views import theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    f"你好，{user['display_name']}",
    "查看简历状态与投递进度，发现与你匹配的校招机会。",
    badge="Student Center",
)

resume = students.get_resume(user["id"])
my_applications = applications.list_my_applications(user["id"])

col1, col2, col3 = st.columns(3)
with col1:
    status = (
        RESUME_STATUS_LABELS.get(resume["status"], "未填写") if resume else "未填写"
    )
    st.metric("简历状态", status)
with col2:
    st.metric("投递总数", len(my_applications))
with col3:
    hired = sum(1 for item in my_applications if item["status"] == "HIRED")
    st.metric("已录用", hired)

theme.section_title("快捷入口", "常用操作一键直达")
link1, link2, link3 = st.columns(3)
with link1:
    with st.container(border=True):
        st.markdown("**🔍 职位广场**")
        st.caption("关键词搜索、多维筛选、批量投递")
        st.page_link("views/student/jobs.py", label="去发现职位", icon="🔍")
with link2:
    with st.container(border=True):
        st.markdown("**✨ 智能推荐**")
        st.caption("基于简历画像的个性化岗位匹配")
        st.page_link("views/student/recommendations.py", label="查看推荐", icon="✨")
with link3:
    with st.container(border=True):
        st.markdown("**⭐ 我的收藏**")
        st.caption("集中比较收藏的岗位机会")
        st.page_link("views/student/favorites.py", label="查看收藏", icon="⭐")

if resume is None:
    st.info("你还没有简历，先去完善简历，通过核查后即可投递职位。")
    st.page_link("views/student/resume.py", label="去填写简历", icon="📄")
elif resume["status"] != "VERIFIED":
    st.info("简历通过管理员核查后才能投递职位。")
    if resume.get("review_note"):
        st.caption(f"最近一次审核备注：{resume['review_note']}")
else:
    st.success("简历已通过核查，可以投递职位。")

theme.section_title("最近投递", "按更新时间倒序展示近 5 条")
if not my_applications:
    st.caption("暂无投递记录。")
else:
    for item in my_applications[:5]:
        label = APPLICATION_STATUS_LABELS.get(item["status"], item["status"])
        with st.container(border=True):
            st.write(
                f"**{item['job_title']}**（{item['company_name']}）"
                f" · {label} · {item['updated_at']}"
            )
    st.page_link("views/student/applications.py", label="查看全部投递", icon="📬")
