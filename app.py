"""CampusRecruit 唯一入口：会话初始化 + 全局主题 + 按角色构建导航。"""

import streamlit as st

from core.config import (
    ROLE_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
    Role,
)
from views.theme import apply_theme, sidebar_brand

st.set_page_config(
    page_title="校招平台 CampusRecruit",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

if SESSION_AUTH_USER not in st.session_state:
    st.session_state[SESSION_AUTH_USER] = None
if SESSION_FLASH not in st.session_state:
    st.session_state[SESSION_FLASH] = None

user = st.session_state[SESSION_AUTH_USER]

if user is None:
    page = st.navigation(
        [st.Page("views/auth/login.py", title="登录 / 注册", icon="🔐")]
    )
elif user["role"] == Role.STUDENT.value:
    page = st.navigation(
        {
            "求职中心": [
                st.Page("views/student/home.py", title="首页", default=True, icon="🏠"),
                st.Page("views/student/jobs.py", title="职位广场", icon="🔍"),
                st.Page("views/student/urgent.py", title="急招专区", icon="⚡"),
                st.Page(
                    "views/student/recommendations.py",
                    title="智能推荐",
                    icon="✨",
                ),
                st.Page("views/student/favorites.py", title="我的收藏", icon="⭐"),
                st.Page("views/student/applications.py", title="我的投递", icon="📬"),
            ],
            "校园社区": [
                st.Page("views/student/community.py", title="企业文化", icon="💬"),
                st.Page(
                    "views/student/company_reviews.py", title="企业评分", icon="📝"
                ),
                st.Page("views/student/micro_tasks.py", title="小任务", icon="🧩"),
            ],
            "个人中心": [
                st.Page("views/student/resume.py", title="我的简历", icon="📄"),
                st.Page(
                    "views/student/job_detail.py",
                    title="职位详情",
                    visibility="hidden",
                ),
                st.Page(
                    "views/student/company.py",
                    title="企业主页",
                    visibility="hidden",
                ),
            ],
        }
    )
elif user["role"] == Role.COMPANY.value:
    page = st.navigation(
        {
            "企业端": [
                st.Page("views/company/home.py", title="首页", default=True, icon="🏠"),
                st.Page("views/company/dashboard.py", title="招聘看板", icon="📊"),
                st.Page("views/company/profile.py", title="企业资料", icon="🏢"),
                st.Page("views/company/jobs.py", title="职位管理", icon="📌"),
                st.Page("views/company/candidates.py", title="候选人", icon="👥"),
                st.Page("views/company/community.py", title="企业社区", icon="💬"),
                st.Page("views/company/micro_tasks.py", title="小任务", icon="🧩"),
            ]
        }
    )
else:
    page = st.navigation(
        {
            "管理端": [
                st.Page("views/admin/home.py", title="概览", default=True, icon="📊"),
                st.Page("views/admin/moderation.py", title="内容审核", icon="🛡️"),
                st.Page("views/admin/companies.py", title="企业审核", icon="🏢"),
                st.Page("views/admin/jobs.py", title="职位审核", icon="📌"),
                st.Page("views/admin/resumes.py", title="简历核查", icon="📄"),
            ]
        }
    )

with st.sidebar:
    sidebar_brand()
    st.divider()
    if user is None:
        st.caption("当前用户：未登录")
    else:
        st.markdown(f"**{user['display_name']}**")
        st.caption(f"角色：{ROLE_LABELS.get(user['role'], user['role'])}")
        st.caption(f"邮箱：{user['email']}")
        if st.button("退出登录", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    flash = st.session_state.get(SESSION_FLASH)
    if flash:
        st.success(flash)
        st.session_state[SESSION_FLASH] = None

page.run()
