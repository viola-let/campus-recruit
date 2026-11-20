"""企业审核：企业资质与 HR 身份两层独立审核。"""

import streamlit as st

from core.config import SESSION_AUTH_USER, SESSION_FLASH
from core.errors import BusinessError
from core.security import resolve_upload_path
from services import companies

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

st.title("🏢 企业审核")
st.caption("企业资质与 HR 身份互相独立，任一未通过企业都不能发布职位。")

pending = companies.list_pending_companies(user["id"], limit=200)

license_tab, hr_tab = st.tabs(["企业资质", "企业 HR"])

with license_tab:
    license_items = [item for item in pending if item["status"] == "PENDING"]
    if not license_items:
        st.info("暂无待审企业资质。")
    for item in license_items:
        with st.container(border=True):
            st.subheader(item["name"])
            st.caption(
                f"统一社会信用代码：{item['license_no']} · "
                f"HR：{item['hr_name']}（{item['hr_email']}）"
            )
            if item.get("license_file"):
                try:
                    path = resolve_upload_path(item["license_file"])
                except BusinessError:
                    st.caption("营业执照文件缺失")
                else:
                    st.download_button(
                        "下载营业执照",
                        path.read_bytes(),
                        file_name=path.name,
                        key=f"admin_license_{item['id']}",
                    )
            else:
                st.caption("企业尚未上传营业执照")

            note = st.text_input(
                "审核备注（拒绝时必填）", key=f"license_note_{item['id']}"
            )
            approve, reject = st.columns(2)
            if approve.button("通过资质", key=f"license_ok_{item['id']}"):
                try:
                    companies.review_license(user["id"], item["id"], "APPROVED", note)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "企业资质已通过"
                    st.rerun()
            if reject.button("拒绝资质", key=f"license_no_{item['id']}"):
                try:
                    companies.review_license(user["id"], item["id"], "REJECTED", note)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "企业资质已拒绝"
                    st.rerun()

with hr_tab:
    hr_items = [item for item in pending if item["hr_status"] == "PENDING"]
    if not hr_items:
        st.info("暂无待审企业 HR。")
    for item in hr_items:
        with st.container(border=True):
            st.subheader(f"{item['name']} · {item['hr_name']}")
            st.caption(f"HR 企业邮箱：{item['hr_email']}")
            if item.get("hr_proof_file"):
                try:
                    path = resolve_upload_path(item["hr_proof_file"])
                except BusinessError:
                    st.caption("HR 在职证明缺失")
                else:
                    st.download_button(
                        "下载 HR 在职证明",
                        path.read_bytes(),
                        file_name=path.name,
                        key=f"admin_hr_{item['id']}",
                    )
            else:
                st.caption("企业尚未上传 HR 在职证明")

            note = st.text_input("审核备注（拒绝时必填）", key=f"hr_note_{item['id']}")
            approve, reject = st.columns(2)
            if approve.button("通过 HR", key=f"hr_ok_{item['id']}"):
                try:
                    companies.review_hr(user["id"], item["id"], "APPROVED", note)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "企业 HR 已通过"
                    st.rerun()
            if reject.button("拒绝 HR", key=f"hr_no_{item['id']}"):
                try:
                    companies.review_hr(user["id"], item["id"], "REJECTED", note)
                except BusinessError as exc:
                    st.error(exc.message)
                else:
                    st.session_state[SESSION_FLASH] = "企业 HR 已拒绝"
                    st.rerun()
