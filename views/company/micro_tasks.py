"""企业小任务：发布短期任务、查看报名名单与结束任务。"""

import streamlit as st

from core.config import (
    MICRO_TASK_STATUS_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import micro_tasks
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "小任务管理",
    "发布展会协助、活动执行等短期任务；平台仅展示信息，不参与资金结算。",
    badge="Micro Tasks",
)

components.demo_info(
    background="企业短期用工需求缺少标准化发布与报名管理工具。",
    scenario="展会、开放日、活动执行等短期用工的发布、报名与名单管理。",
    demo_points=[
        "发布即进入审核，状态在待审核 / 招募中 / 已结束之间流转",
        "关键词红线拦截资金类与灰产类任务",
        "可查看报名名单并一键结束任务，平台不介入结算",
    ],
)

st.warning(
    "平台红线：禁止发布刷单、押金、垫付、返利、拉人头类任务，"
    "违规内容会被拒绝并影响账号信用。"
)

with st.form("company_task_create_form"):
    st.subheader("发布新任务")
    title = st.text_input("任务名称", placeholder="如：校园开放日现场协助")
    description = st.text_area(
        "任务说明（至少 30 字）", height=120, placeholder="工作内容、集合地点、注意事项"
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        city = st.text_input("城市")
    with col2:
        reward = st.text_input("报酬", placeholder="如：150 元/天")
    with col3:
        headcount = st.number_input("招募人数", min_value=1, max_value=100, value=5)
    schedule = st.text_input("时间安排", placeholder="如：11 月 25 日 9:00-17:00")
    submitted = st.form_submit_button(
        "提交审核", type="primary", use_container_width=True
    )

if submitted:
    try:
        micro_tasks.create_task(
            user["id"],
            {
                "title": title,
                "description": description,
                "city": city,
                "reward": reward,
                "schedule": schedule,
                "headcount": headcount,
            },
        )
    except BusinessError as exc:
        st.error(exc.message)
    else:
        st.session_state[SESSION_FLASH] = "任务已提交，审核通过后展示"
        st.rerun()

st.divider()
st.subheader("我发布的任务")
tasks = micro_tasks.list_company_tasks(user["id"])
if not tasks:
    st.info("还没有发布任务。")
    st.stop()

for task in tasks:
    with st.container(border=True):
        head, action = st.columns([4, 1.2], vertical_alignment="center")
        with head:
            st.markdown(f"**{task['title']}**")
            components.chips(
                [
                    MICRO_TASK_STATUS_LABELS.get(task["status"], task["status"]),
                    task["city"],
                    task["reward"] or "报酬面议",
                    f"报名 {task['signup_count']}/{task['headcount']}",
                ]
            )
        with action:
            if task["status"] in {"APPROVED", "PENDING"}:
                if st.button(
                    "结束任务",
                    key=f"task_close_{task['id']}",
                    use_container_width=True,
                ):
                    try:
                        micro_tasks.close_task(user["id"], task["id"])
                    except BusinessError as exc:
                        st.error(exc.message)
                    else:
                        st.session_state[SESSION_FLASH] = "任务已结束"
                        st.rerun()
        st.write(task["description"])
        if task["schedule"]:
            st.caption(f"时间安排：{task['schedule']}")

        if task["signup_count"]:
            with st.expander(f"查看报名名单（{task['signup_count']}）"):
                try:
                    signups = micro_tasks.task_signups(user["id"], task["id"])
                except BusinessError as exc:
                    st.caption(exc.message)
                else:
                    for item in signups:
                        st.write(
                            f"- {item['display_name']} · {item['email']} · "
                            f"{item['created_at'][:10]}"
                        )
