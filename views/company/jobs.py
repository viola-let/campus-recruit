"""职位管理：发布、编辑、关闭与重新开放。"""

import streamlit as st

from core.config import (
    JOB_CATEGORIES,
    JOB_STATUS_LABELS,
    JOB_TYPE_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import companies, jobs
from views import theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "职位管理",
    "发布与维护招聘职位，岗位类别会自动写入职位标题，便于学生精准筛选。",
    badge="Job Management",
)

can_publish = companies.can_publish_job(user["id"])
if not can_publish:
    st.warning("企业资质与 HR 审核都通过后才能发布或编辑职位。")

with st.form("company_job_create_form"):
    st.subheader("发布新职位")
    title = st.text_input("职位名称", placeholder="如：Python 后端工程师")
    job_type_label = st.selectbox("职位类型", ["校招", "实习"])
    category_label = st.selectbox("岗位类别", JOB_CATEGORIES)
    city = st.text_input("工作城市")
    salary = st.text_input("薪资", placeholder="如 15-25K/月")
    description = st.text_area("职位描述（至少 20 字）")
    requirements = st.text_area("任职要求")
    create_submitted = st.form_submit_button(
        "提交审核", disabled=not can_publish, use_container_width=True
    )

if create_submitted:
    final_title = (
        title if title.startswith("【") else f"【{category_label}】{title.strip()}"
    )
    try:
        jobs.create_job(
            user["id"],
            {
                "title": final_title,
                "job_type": "CAMPUS" if job_type_label == "校招" else "INTERN",
                "city": city,
                "salary": salary,
                "description": description,
                "requirements": requirements,
            },
        )
    except BusinessError as exc:
        st.error(exc.message)
    else:
        st.session_state[SESSION_FLASH] = "职位已提交，等待管理员审核"
        st.rerun()

st.divider()
st.subheader("已发布职位")

my_jobs = jobs.list_company_jobs(user["id"])
if not my_jobs:
    st.info("还没有职位，先在上方发布一个吧。")
    st.stop()

for job in my_jobs:
    status_label = JOB_STATUS_LABELS.get(job["status"], job["status"])
    with st.container(border=True):
        head1, head2 = st.columns([4, 2])
        with head1:
            featured = "⭐ 推荐 · " if job["is_featured"] else ""
            st.subheader(f"{featured}{job['title']}")
            st.caption(
                f"{JOB_TYPE_LABELS.get(job['job_type'], job['job_type'])} · "
                f"{job['city']} · {job['salary'] or '薪资面议'}"
            )
        with head2:
            st.write(f"状态：**{status_label}**")
            if job["status"] == "CLOSED":
                if st.button("重新开放", key=f"reopen_{job['id']}"):
                    try:
                        jobs.reopen_job(user["id"], job["id"])
                    except BusinessError as exc:
                        st.error(exc.message)
                    else:
                        st.session_state[SESSION_FLASH] = "职位已重新开放，等待审核"
                        st.rerun()
            elif job["status"] in {"PENDING", "APPROVED"}:
                if st.button("关闭职位", key=f"close_{job['id']}"):
                    try:
                        jobs.close_job(user["id"], job["id"])
                    except BusinessError as exc:
                        st.error(exc.message)
                    else:
                        st.session_state[SESSION_FLASH] = "职位已关闭"
                        st.rerun()

        if job.get("review_note"):
            st.caption(f"最近审核备注：{job['review_note']}")

        if job["status"] == "APPROVED":
            urgent_col, days_col = st.columns([2.4, 1.3])
            with urgent_col:
                if job.get("is_urgent") and job.get("urgent_until"):
                    st.caption(f"⚡ 急招中，截止 {job['urgent_until']}")
                else:
                    st.caption("未设置急招（急招岗位不超过在招岗位的 30%）")
            with days_col:
                if job.get("is_urgent"):
                    if st.button("取消急招", key=f"urgent_cancel_{job['id']}"):
                        try:
                            jobs.cancel_urgent(user["id"], job["id"])
                        except BusinessError as exc:
                            st.error(exc.message)
                        else:
                            st.session_state[SESSION_FLASH] = "已取消急招"
                            st.rerun()
                else:
                    urgent_days = st.number_input(
                        "急招天数",
                        min_value=1,
                        max_value=30,
                        value=7,
                        key=f"urgent_days_{job['id']}",
                    )
                    if st.button("设为急招", key=f"urgent_set_{job['id']}"):
                        try:
                            jobs.set_urgent(user["id"], job["id"], urgent_days)
                        except BusinessError as exc:
                            st.error(exc.message)
                        else:
                            st.session_state[SESSION_FLASH] = "已设为急招"
                            st.rerun()

        if job["status"] != "CLOSED":
            with st.expander("编辑职位"):
                with st.form(f"company_job_edit_{job['id']}"):
                    edit_title = st.text_input("职位名称", value=job["title"])
                    edit_type = st.selectbox(
                        "职位类型",
                        ["校招", "实习"],
                        index=0 if job["job_type"] == "CAMPUS" else 1,
                    )
                    edit_city = st.text_input("工作城市", value=job["city"])
                    edit_salary = st.text_input("薪资", value=job["salary"] or "")
                    edit_description = st.text_area(
                        "职位描述", value=job["description"]
                    )
                    edit_requirements = st.text_area(
                        "任职要求", value=job["requirements"] or ""
                    )
                    if st.form_submit_button("保存并重新送审"):
                        try:
                            jobs.update_job(
                                user["id"],
                                job["id"],
                                {
                                    "title": edit_title,
                                    "job_type": "CAMPUS"
                                    if edit_type == "校招"
                                    else "INTERN",
                                    "city": edit_city,
                                    "salary": edit_salary,
                                    "description": edit_description,
                                    "requirements": edit_requirements,
                                },
                            )
                        except BusinessError as exc:
                            st.error(exc.message)
                        else:
                            st.session_state[SESSION_FLASH] = "职位已更新，等待重新审核"
                            st.rerun()
