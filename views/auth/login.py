"""登录 / 注册页面。"""

import streamlit as st

from core import auth
from core.config import SESSION_AUTH_USER, SESSION_FLASH
from core.errors import BusinessError
from views import theme

theme.hero(
    "校招平台 CampusRecruit",
    "学生 · 企业 · 平台管理员，三端统一登录入口",
    badge="Welcome",
)

with st.expander("演示账号（点击展开）"):
    st.markdown(
        "- 学生：`student01@seed.campus` / `Student123!`\n"
        "- 企业：`company01@seed.campus` / `Company123!`\n"
        "- 管理员：`admin@example.com` / `ChangeMe123`"
    )

login_tab, register_tab = st.tabs(["登录", "注册"])

with login_tab:
    with st.form("auth_login_form"):
        login_email = st.text_input("邮箱", key="auth_login_email")
        login_password = st.text_input(
            "密码", type="password", key="auth_login_password"
        )
        login_submitted = st.form_submit_button("登录", use_container_width=True)

    if login_submitted:
        try:
            user = auth.login(login_email, login_password)
        except BusinessError as exc:
            st.error(exc.message)
        else:
            st.session_state[SESSION_AUTH_USER] = user
            st.session_state[SESSION_FLASH] = f"欢迎回来，{user['display_name']}"
            st.rerun()

with register_tab:
    role_label = st.radio(
        "注册身份", ["学生", "企业"], horizontal=True, key="auth_register_role"
    )
    name_label = "姓名" if role_label == "学生" else "企业名称"

    with st.form("auth_register_form"):
        register_email = st.text_input("邮箱", key="auth_register_email")
        register_name = st.text_input(name_label, key="auth_register_name")
        register_password = st.text_input(
            "密码（至少 8 位）", type="password", key="auth_register_password"
        )
        register_confirm = st.text_input(
            "确认密码", type="password", key="auth_register_confirm"
        )
        register_submitted = st.form_submit_button("注册", use_container_width=True)

    if register_submitted:
        if register_password != register_confirm:
            st.error("两次输入的密码不一致")
        else:
            try:
                if role_label == "学生":
                    auth.register_student(
                        register_email, register_password, register_name
                    )
                else:
                    auth.register_company(
                        register_email, register_password, register_name
                    )
            except BusinessError as exc:
                st.error(exc.message)
            else:
                st.success("注册成功，请切换到「登录」页签登录")
