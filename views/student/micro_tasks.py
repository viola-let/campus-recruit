"""小任务兼职：浏览审核通过的任务、报名与查看报名记录。"""

import streamlit as st

from core.config import SESSION_AUTH_USER, SESSION_FLASH
from core.errors import BusinessError
from services import micro_tasks
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "小任务兼职",
    "展会协助、传单派发、问卷参与等轻量任务，报名制、不占实习经历。",
    badge="Micro Tasks",
)

components.demo_info(
    background="短期、轻量的兼职需求缺少独立入口，混在实习岗位中影响匹配效率。",
    scenario="展会协助、活动执行、问卷访问等 1-3 天短期任务。",
    demo_points=[
        "任务与实习严格区隔，不进入投递与简历快照流程",
        "平台只展示信息、不参与结算，页面固定展示防诈骗提示",
        "关键词拦截刷单 / 押金 / 垫付，先审后发、报名制",
    ],
)

st.warning(
    "安全提示：平台只展示任务信息，不参与任何资金结算。"
    "任何要求先交押金、垫付费用、刷单返利的任务都是诈骗，请立即举报。"
)

tasks = micro_tasks.list_open_tasks()
my_signups = micro_tasks.my_signups(user["id"])
signed_ids = {item["task_id"] for item in my_signups}

st.markdown(f"### 招募中任务（{len(tasks)}）")
if not tasks:
    st.info("当前没有招募中的任务，稍后再来看看。")

for task in tasks:
    signed = task["id"] in signed_ids
    full = task["signup_count"] >= task["headcount"]
    with st.container(border=True):
        head, action = st.columns([4, 1.2], vertical_alignment="center")
        with head:
            st.markdown(f"**{task['title']}**")
            components.chips(
                [
                    task["company_name"],
                    task["city"],
                    task["reward"] or "报酬面议",
                    f"已报名 {task['signup_count']}/{task['headcount']}",
                ]
            )
            if task["schedule"]:
                st.caption(f"时间安排：{task['schedule']}")
        with action:
            if st.button(
                "✓ 已报名" if signed else ("名额已满" if full else "立即报名"),
                key=f"task_signup_{task['id']}",
                type="primary",
                use_container_width=True,
                disabled=signed or full,
            ):
                try:
                    micro_tasks.signup_task(user["id"], task["id"])
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "报名成功，请留意企业联系"
                    st.rerun()
        st.write(task["description"])
        st.caption("本任务为短期兼职信息，不进入实习投递与简历快照流程。")

st.divider()
st.markdown("### 我的报名")
if not my_signups:
    st.caption("还没有报名记录。")
for item in my_signups:
    st.write(
        f"- {item['title']} · {item['company_name']} · {item['city']} · "
        f"{item['reward'] or '报酬面议'} · 报名于 {item['created_at'][:10]}"
    )
