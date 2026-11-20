"""职位审核：通过、拒绝与推荐设置。"""

import streamlit as st

from core.config import (
    JOB_TYPE_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import admin, jobs

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

st.title("📌 职位审核")

pending_tab, featured_tab = st.tabs(["待审核职位", "推荐管理"])

with pending_tab:
    pending = jobs.list_pending_jobs(user["id"], limit=200)
    if not pending:
        st.info("暂无待审职位。")
    for job in pending:
        with st.container(border=True):
            st.subheader(job["title"])
            st.caption(
                f"{job['company_name']} · "
                f"{JOB_TYPE_LABELS.get(job['job_type'], job['job_type'])} · "
                f"{job['city']} · {job['salary'] or '薪资面议'}"
            )
            st.write(job["description"])
            if job["requirements"]:
                st.caption(f"任职要求：{job['requirements']}")

            note = st.text_input("审核备注（拒绝时必填）", key=f"job_note_{job['id']}")
            approve, reject = st.columns(2)
            if approve.button("通过职位", key=f"job_ok_{job['id']}"):
                try:
                    jobs.review_job(user["id"], job["id"], "APPROVED", note)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "职位已通过"
                    st.rerun()
            if reject.button("拒绝职位", key=f"job_no_{job['id']}"):
                try:
                    jobs.review_job(user["id"], job["id"], "REJECTED", note)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "职位已拒绝"
                    st.rerun()

with featured_tab:
    approved = admin.list_approved_jobs(user["id"], limit=200)
    if not approved:
        st.info("暂无已通过职位。")
    for job in approved:
        with st.container(border=True):
            st.subheader(job["title"])
            st.caption(f"{job['company_name']} · {job['city']}")
            if job["is_featured"]:
                if st.button("取消推荐", key=f"unfeature_{job['id']}"):
                    try:
                        jobs.set_featured(user["id"], job["id"], False)
                    except BusinessError as exc:
                        st.error(exc.message)
                    else:
                        st.session_state[SESSION_FLASH] = "已取消推荐"
                        st.rerun()
            else:
                if st.button("设为推荐", key=f"feature_{job['id']}"):
                    try:
                        jobs.set_featured(user["id"], job["id"], True)
                    except BusinessError as exc:
                        st.error(exc.message)
                    else:
                        st.session_state[SESSION_FLASH] = "已设为推荐"
                        st.rerun()
