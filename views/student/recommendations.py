"""智能推荐：基于简历画像的岗位匹配与推荐理由。"""

import streamlit as st

from core.config import SESSION_AUTH_USER
from core.errors import BusinessError
from services import applications, favorites, recommendations, students
from views import components, theme
from views.student import cards

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "智能推荐",
    "结合你的专业技能、专业方向与城市偏好，自动匹配最值得投递的岗位。",
    badge="AI Matching",
)

resume = students.get_resume(user["id"])
if resume is None:
    st.info("完善简历后即可获得个性化岗位推荐。")
    if st.button("去完善简历", type="primary"):
        st.switch_page("views/student/resume.py")
    st.stop()

skills = components.split_tags(resume.get("skills"))
with st.container(border=True):
    st.markdown(
        f"**推荐画像**：{resume['school']} · {resume['major']} · "
        f"{resume['graduation_year']} 届"
    )
    if skills:
        components.chips(skills, "cr-chip--accent")
    st.caption("推荐依据：简历技能命中职位关键词、专业方向匹配、城市偏好与平台推荐位。")

try:
    results = recommendations.recommend_jobs(user["id"], limit=12)
except BusinessError as exc:
    st.warning(exc.message)
    st.stop()

st.markdown(f"### 为你推荐 {len(results)} 个职位")
if not results:
    st.info("暂未找到高匹配度职位，完善技能标签或前往职位广场浏览更多机会。")
    st.stop()

favorite_ids = favorites.favorite_job_ids(user["id"])
applied_ids = applications.applied_job_ids(user["id"])
for job in results:
    cards.render_job_card(
        job,
        user_id=user["id"],
        can_apply=resume["status"] == "VERIFIED",
        favorited=job["id"] in favorite_ids,
        applied=job["id"] in applied_ids,
        key_prefix="reco",
        reasons=job.get("match_reasons"),
    )
