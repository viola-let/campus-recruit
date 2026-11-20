"""简历核查：通过、拒绝与理由记录。"""

import streamlit as st

from core.config import SESSION_AUTH_USER, SESSION_FLASH
from core.errors import BusinessError
from core.security import resolve_upload_path
from services import students

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

st.title("📄 简历核查")
st.caption("核查通过后学生才能投递；学生修改简历后会重新进入待核查。")

pending = students.list_pending_resumes(user["id"], limit=200)
if not pending:
    st.info("暂无待核查简历。")

for resume in pending:
    with st.container(border=True):
        st.subheader(f"{resume['real_name']} · {resume['school']}")
        st.caption(
            f"专业：{resume['major']} · 毕业年份：{resume['graduation_year']} · "
            f"手机号：{resume['phone']}"
        )
        st.write(f"技能：{resume['skills'] or '-'}")
        st.write(f"简介：{resume['summary'] or '-'}")

        if resume.get("file_path"):
            try:
                path = resolve_upload_path(resume["file_path"])
            except BusinessError:
                st.caption("简历附件缺失")
            else:
                st.download_button(
                    "下载简历附件",
                    path.read_bytes(),
                    file_name=path.name,
                    key=f"admin_resume_{resume['id']}",
                )
        else:
            st.caption("学生未上传附件")

        note = st.text_input(
            "核查备注（拒绝时必填）", key=f"resume_note_{resume['id']}"
        )
        approve, reject = st.columns(2)
        if approve.button("核查通过", key=f"resume_ok_{resume['id']}"):
            try:
                students.review_resume(user["id"], resume["id"], "VERIFIED", note)
            except BusinessError as exc:
                st.error(exc.message)
            else:
                st.session_state[SESSION_FLASH] = "简历已核查通过"
                st.rerun()
        if reject.button("拒绝简历", key=f"resume_no_{resume['id']}"):
            try:
                students.review_resume(user["id"], resume["id"], "REJECTED", note)
            except BusinessError as exc:
                st.error(exc.message)
            else:
                st.session_state[SESSION_FLASH] = "简历已拒绝"
                st.rerun()
