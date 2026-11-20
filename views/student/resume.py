"""我的简历：填写、保存、上传附件、查看核查状态。"""

import streamlit as st

from core.config import (
    RESUME_STATUS_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from services import students

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

st.title("📄 我的简历")

resume = students.get_resume(user["id"])

if resume:
    status_label = RESUME_STATUS_LABELS.get(resume["status"], resume["status"])
    st.info(f"当前状态：{status_label}（修改并保存后会重新进入待核查）")
    if resume.get("review_note"):
        st.caption(f"最近一次审核备注：{resume['review_note']}")
else:
    st.info("请先填写并保存简历。")

with st.form("student_resume_form"):
    real_name = st.text_input("姓名", value=resume["real_name"] if resume else "")
    phone = st.text_input("手机号", value=resume["phone"] if resume else "")
    school = st.text_input("学校", value=resume["school"] if resume else "")
    major = st.text_input("专业", value=resume["major"] if resume else "")
    graduation_year = st.number_input(
        "毕业年份",
        min_value=2000,
        max_value=2100,
        value=int(resume["graduation_year"]) if resume else 2027,
        step=1,
    )
    skills = st.text_area(
        "技能", value=resume["skills"] if resume and resume["skills"] else ""
    )
    summary = st.text_area(
        "个人简介",
        value=resume["summary"] if resume and resume["summary"] else "",
    )
    submitted = st.form_submit_button("保存简历", use_container_width=True)

if submitted:
    try:
        students.save_resume(
            user["id"],
            {
                "real_name": real_name,
                "phone": phone,
                "school": school,
                "major": major,
                "graduation_year": graduation_year,
                "skills": skills,
                "summary": summary,
            },
        )
    except BusinessError as exc:
        st.error(exc.message)
    else:
        st.session_state[SESSION_FLASH] = "简历已保存，等待管理员核查"
        st.rerun()

st.divider()
st.subheader("简历附件")
st.caption("支持 PDF / DOCX，大小不超过 5 MB。上传后简历会重新进入待核查。")

if resume and resume.get("file_path"):
    st.caption(f"已上传附件：{resume['file_path'].split('/')[-1]}")
else:
    st.caption("尚未上传附件。")

uploaded = st.file_uploader("选择附件", type=["pdf", "docx"], key="student_resume_file")
if uploaded is not None and st.button("上传附件"):
    try:
        students.attach_resume_file(user["id"], uploaded.name, uploaded.getvalue())
    except BusinessError as exc:
        st.error(exc.message)
    else:
        st.session_state[SESSION_FLASH] = "附件上传成功，等待管理员核查"
        st.rerun()
