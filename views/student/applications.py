"""我的投递：查看状态与企业反馈。"""

import streamlit as st

from core.config import (
    APPLICATION_STATUS_LABELS,
    SESSION_AUTH_USER,
)
from services import applications
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "我的投递",
    "按投递时间倒序展示，企业更新后会显示最新状态与反馈。",
    badge="Applications",
)

items = applications.list_my_applications(user["id"])

if not items:
    st.info("还没有投递记录，去职位广场看看合适的岗位吧。")
    st.page_link("views/student/jobs.py", label="去职位广场", icon="🔍")
    st.stop()

for item in items:
    status_label = APPLICATION_STATUS_LABELS.get(item["status"], item["status"])
    with st.container(border=True):
        st.subheader(item["job_title"])
        st.caption(f"{item['company_name']} · 投递时间：{item['created_at']}")
        components.chips([f"当前状态：{status_label}"])
        st.write(f"反馈：{item['feedback'] or '暂无'}")
        st.caption(f"最后更新：{item['updated_at']}")
