"""急招专区：独立流量入口，只展示仍在有效期内的急招职位。"""

import streamlit as st

from core.config import SESSION_AUTH_USER
from services import applications, favorites, jobs, students
from views import components, theme
from views.student import cards

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "急招专区",
    "企业设置明确到期时间并承诺优先处理投递，到期后自动回到普通职位。",
    badge="Urgent Hiring",
)

components.demo_info(
    background="企业临时补招与项目急缺人时，普通职位列表无法体现时效差异。",
    scenario="校招补录、实习急招、项目临时扩编等需要快速响应的招聘场景。",
    demo_points=[
        "企业在职位管理设置 1-30 天急招，卡片显示「急招 · 剩 N 天」",
        "过期职位自动退出专区，避免长期挂急招",
        "急招岗位不超过在招岗位 30%，防止专区失去筛选价值",
    ],
)

results = jobs.search_jobs(only_urgent=True, sort="latest")
resume = students.get_resume(user["id"])
can_apply = resume is not None and resume["status"] == "VERIFIED"
favorite_ids = favorites.favorite_job_ids(user["id"])
applied_ids = applications.applied_job_ids(user["id"])

st.markdown(f"### 当前有 {len(results)} 个急招职位")
st.caption("急招岗位由企业设置 1-30 天有效期，且不超过在招岗位的 30%。")

if not can_apply:
    st.warning("简历通过核查后才能投递，可先浏览并收藏。")

if not results:
    st.info("暂无急招职位，去职位广场看看更多机会吧。")
    st.page_link("views/student/jobs.py", label="前往职位广场", icon="🔍")
    st.stop()

for job in results:
    cards.render_job_card(
        job,
        user_id=user["id"],
        can_apply=can_apply,
        favorited=job["id"] in favorite_ids,
        applied=job["id"] in applied_ids,
        key_prefix="urgent",
        show_pick=can_apply,
    )
