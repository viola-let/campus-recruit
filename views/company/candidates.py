"""候选人：筛选投递、查看简历快照、下载附件与状态流转。"""

import streamlit as st

from core.config import (
    APPLICATION_STATUS_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import applications, jobs, matching
from views import components

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

st.title("👥 候选人")
st.caption("只能查看投递到本公司职位的简历，展示的是投递时的快照。")

my_jobs = jobs.list_company_jobs(user["id"])
job_options = {"全部职位": None}
job_options.update({f"{job['title']}（#{job['id']}）": job["id"] for job in my_jobs})

with st.form("company_candidates_filter"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        job_label = st.selectbox("职位", list(job_options.keys()))
    with col2:
        school = st.text_input("学校")
    with col3:
        major = st.text_input("专业")
    with col4:
        status_label = st.selectbox(
            "状态", ["全部", *APPLICATION_STATUS_LABELS.values()]
        )
    sort_by_match = st.checkbox("按岗位匹配度排序", value=True)
    st.form_submit_button("筛选")

status_value = None
if status_label != "全部":
    for value, label in APPLICATION_STATUS_LABELS.items():
        if label == status_label:
            status_value = value
            break

filters = {
    "job_id": job_options[job_label],
    "school": school,
    "major": major,
    "status": status_value,
}
if sort_by_match:
    candidates = matching.list_candidates_ranked(user["id"], filters)
else:
    candidates = applications.list_job_candidates(user["id"], filters)

if not candidates:
    st.info("没有符合条件的候选人。")
    st.stop()

if sort_by_match:
    st.caption("已按简历与岗位的匹配度排序，匹配理由仅供参考。")

for item in candidates:
    snapshot = item.get("resume") or {}
    item_status = APPLICATION_STATUS_LABELS.get(item["status"], item["status"])
    with st.container(border=True):
        st.subheader(f"{snapshot.get('real_name', item['student_name'])}")
        st.caption(
            f"应聘：{item['job_title']} · 学校：{snapshot.get('school', '-')} "
            f"· 专业：{snapshot.get('major', '-')} · 状态：{item_status}"
        )
        if item.get("match_reasons"):
            components.chips(
                [f"匹配分 {item['match_score']}", *item["match_reasons"][:3]],
                "cr-chip--accent",
            )

        with st.expander("查看简历快照"):
            st.write(f"手机号：{snapshot.get('phone', '-')}")
            st.write(f"毕业年份：{snapshot.get('graduation_year', '-')}")
            st.write(f"技能：{snapshot.get('skills') or '-'}")
            st.write(f"简介：{snapshot.get('summary') or '-'}")
            if item.get("resume_file_snapshot"):
                try:
                    filename, data = applications.get_resume_file(
                        user["id"], item["id"]
                    )
                except BusinessError as exc:
                    st.caption(exc.message)
                else:
                    st.download_button(
                        "下载简历附件",
                        data,
                        file_name=filename,
                        key=f"candidate_file_{item['id']}",
                    )

        st.write(f"企业反馈：{item['feedback'] or '暂无'}")

        feedback = st.text_area(
            "反馈（拒绝时必填）",
            value=item["feedback"] or "",
            key=f"candidate_feedback_{item['id']}",
        )

        actions = []
        if item["status"] == "SUBMITTED":
            actions.append(("标记已查看", "VIEWED"))
        if item["status"] == "VIEWED":
            actions.append(("进入面试", "SHORTLISTED"))
        if item["status"] == "SHORTLISTED":
            actions.append(("录用", "HIRED"))
        if item["status"] in {"SUBMITTED", "VIEWED", "SHORTLISTED"}:
            actions.append(("不合适", "REJECTED"))

        if not actions:
            st.caption("该投递已结束，状态不可再变更。")
            continue

        columns = st.columns(len(actions))
        for column, (label, new_status) in zip(columns, actions, strict=True):
            with column:
                if st.button(label, key=f"candidate_{new_status}_{item['id']}"):
                    try:
                        applications.update_status(
                            user["id"], item["id"], new_status, feedback
                        )
                    except BusinessError as exc:
                        st.error(exc.message)
                    else:
                        st.session_state[SESSION_FLASH] = f"已更新为「{label}」"
                        st.rerun()
