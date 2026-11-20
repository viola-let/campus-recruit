"""我的收藏：集中查看已收藏职位并快速投递。"""

import streamlit as st

from core.config import SESSION_AUTH_USER
from services import applications, favorites, students
from views import theme
from views.student import cards

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "我的收藏",
    "收藏感兴趣的机会，集中比较后再决定投递。",
    badge="Saved Jobs",
)

items = favorites.list_favorites(user["id"])
resume = students.get_resume(user["id"])
can_apply = resume is not None and resume["status"] == "VERIFIED"

st.markdown(f"### 共收藏 {len(items)} 个职位")
if not items:
    st.info("还没有收藏任何职位，去职位广场发现合适的机会吧。")
    if st.button("去职位广场", type="primary"):
        st.switch_page("views/student/jobs.py")
    st.stop()

applied_ids = applications.applied_job_ids(user["id"])
for job in items:
    cards.render_job_card(
        job,
        user_id=user["id"],
        can_apply=can_apply,
        favorited=True,
        applied=job["id"] in applied_ids,
        key_prefix="fav",
    )
