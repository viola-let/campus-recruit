"""招聘看板：职位浏览、投递、面试、录用漏斗与企业响应时长。"""

import streamlit as st

from core.config import JOB_STATUS_LABELS, SESSION_AUTH_USER
from services import analytics
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "招聘看板",
    "查看每个职位的浏览、投递与转化情况，用数据判断招聘效果。",
    badge="Recruiting Analytics",
)

components.demo_info(
    background="企业发布职位后缺少效果反馈，无法判断岗位吸引力与处理效率。",
    scenario="招聘负责人复盘岗位转化、优化职位描述、评估响应速度。",
    demo_points=[
        "浏览数按学生去重，避免刷新虚高",
        "逐职位展示浏览 → 投递 → 面试 → 录用漏斗与转化率",
        "平均响应时长基于已处理投递计算，可直接用于内部考核",
    ],
)

data = analytics.company_dashboard(user["id"])
totals = data["totals"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("职位浏览", totals["views"])
col2.metric("收到投递", totals["applications"])
col3.metric("进入面试", totals["interviews"])
col4.metric("成功录用", totals["hired"])

conversion = (
    round(100 * totals["applications"] / totals["views"], 1) if totals["views"] else 0.0
)
response = totals["response_hours"]
st.caption(
    f"浏览 → 投递转化率：{conversion}% · "
    + (f"平均响应时长：{response} 小时" if response is not None else "暂无处理记录")
)

st.divider()
if not data["jobs"]:
    st.info("还没有发布职位。")
    st.page_link("views/company/jobs.py", label="去发布职位", icon="📌")
    st.stop()

rows = [
    {
        "职位": item["title"],
        "状态": JOB_STATUS_LABELS.get(item["status"], item["status"]),
        "浏览": item["views"],
        "投递": item["applications"],
        "面试": item["interviews"],
        "录用": item["hired"],
        "投递转化率": f"{item['conversion']}%",
    }
    for item in data["jobs"]
]
st.dataframe(rows, use_container_width=True, hide_index=True)
st.caption("浏览数为去重后的学生人数；转化率 = 投递数 / 浏览数。")
