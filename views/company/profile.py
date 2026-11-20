"""企业资料：信息维护、双状态展示、营业执照与 HR 证明上传。"""

import streamlit as st

from core.config import (
    REVIEW_STATUS_LABELS,
    SESSION_AUTH_USER,
    SESSION_FLASH,
)
from core.errors import BusinessError
from core.security import resolve_upload_path
from services import companies
from views import components, theme

user = st.session_state.get(SESSION_AUTH_USER)
if user is None:
    st.warning("请先登录")
    st.stop()

theme.hero(
    "企业资料",
    "维护资质材料与品牌展示信息，品牌内容将展示在岗位列表与职位详情页。",
    badge="Company Profile",
)

profile = companies.get_profile(user["id"])
if profile is None:
    st.warning("企业资料不存在，请联系平台管理员。")
    st.stop()

theme.section_title("品牌展示", "logo · 企业简介 · 企业文化 · 福利标签")
with st.container(border=True):
    logo_col, brand_form_col = st.columns([1, 4])
    with logo_col:
        components.render_logo(profile, 96)
        logo_file = st.file_uploader(
            "上传企业 logo", type=["png", "jpg", "jpeg", "webp"], key="company_logo"
        )
        if logo_file is not None and st.button("上传 logo", use_container_width=True):
            try:
                companies.attach_logo(user["id"], logo_file.name, logo_file.getvalue())
            except BusinessError as exc:
                st.error(exc.message)
            else:
                st.session_state[SESSION_FLASH] = "企业 logo 已更新"
                st.rerun()

    with brand_form_col:
        with st.form("company_branding_form"):
            intro = st.text_area(
                "企业简介",
                value=profile.get("intro") or "",
                height=110,
                placeholder="用 2-3 句话介绍企业定位、主营业务与团队规模",
            )
            culture = st.text_area(
                "企业文化",
                value=profile.get("culture") or "",
                height=90,
                placeholder="例如：扁平协作、技术驱动、导师制培养",
            )
            meta1, meta2 = st.columns(2)
            with meta1:
                industry = st.text_input(
                    "所属行业", value=profile.get("industry") or ""
                )
                company_size = st.text_input(
                    "企业规模",
                    value=profile.get("company_size") or "",
                    placeholder="如：500-2000 人",
                )
            with meta2:
                funding_stage = st.text_input(
                    "融资阶段",
                    value=profile.get("funding_stage") or "",
                    placeholder="如：C 轮 / 已上市",
                )
                city = st.text_input("所在城市", value=profile.get("city") or "")
            benefits = st.text_input(
                "福利标签",
                value=profile.get("benefits") or "",
                placeholder="用逗号分隔，如：六险一金，弹性工作，年度体检",
            )
            branding_saved = st.form_submit_button(
                "保存品牌信息", type="primary", use_container_width=True
            )

        if branding_saved:
            try:
                companies.update_branding(
                    user["id"],
                    {
                        "intro": intro,
                        "culture": culture,
                        "industry": industry,
                        "company_size": company_size,
                        "funding_stage": funding_stage,
                        "city": city,
                        "benefits": benefits,
                    },
                )
            except BusinessError as exc:
                st.error(exc.message)
            else:
                st.session_state[SESSION_FLASH] = "品牌信息已保存"
                st.rerun()

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.info(
        f"企业资质：{REVIEW_STATUS_LABELS.get(profile['status'], profile['status'])}"
    )
    if profile.get("license_note"):
        st.caption(f"审核备注：{profile['license_note']}")
with col2:
    st.info(
        "HR 审核："
        f"{REVIEW_STATUS_LABELS.get(profile['hr_status'], profile['hr_status'])}"
    )
    if profile.get("hr_note"):
        st.caption(f"审核备注：{profile['hr_note']}")

with st.form("company_profile_form"):
    name = st.text_input("企业名称", value=profile["name"])
    license_no = st.text_input("统一社会信用代码", value=profile["license_no"])
    hr_name = st.text_input("HR 姓名", value=profile["hr_name"])
    hr_email = st.text_input("HR 企业邮箱", value=profile["hr_email"])
    submitted = st.form_submit_button("保存资料并重新送审", use_container_width=True)

if submitted:
    try:
        companies.upsert_profile(
            user["id"],
            {
                "name": name,
                "license_no": license_no,
                "hr_name": hr_name,
                "hr_email": hr_email,
            },
        )
    except BusinessError as exc:
        st.error(exc.message)
    else:
        st.session_state[SESSION_FLASH] = "企业资料已保存，等待管理员重新审核"
        st.rerun()

st.divider()
st.subheader("证明材料")

license_col, hr_col = st.columns(2)
with license_col:
    st.write("营业执照")
    if profile.get("license_file"):
        st.caption("已上传")
    license_file = st.file_uploader(
        "上传营业执照", type=["pdf", "docx"], key="company_license_file"
    )
    if license_file is not None and st.button("上传营业执照"):
        try:
            companies.attach_company_file(
                user["id"], "license", license_file.name, license_file.getvalue()
            )
        except BusinessError as exc:
            st.error(exc.message)
        else:
            st.session_state[SESSION_FLASH] = "营业执照已上传，等待审核"
            st.rerun()

with hr_col:
    st.write("HR 在职证明")
    if profile.get("hr_proof_file"):
        st.caption("已上传")
    hr_file = st.file_uploader(
        "上传 HR 在职证明", type=["pdf", "docx"], key="company_hr_file"
    )
    if hr_file is not None and st.button("上传 HR 证明"):
        try:
            companies.attach_company_file(
                user["id"], "hr_proof", hr_file.name, hr_file.getvalue()
            )
        except BusinessError as exc:
            st.error(exc.message)
        else:
            st.session_state[SESSION_FLASH] = "HR 在职证明已上传，等待审核"
            st.rerun()

st.divider()
st.subheader("已上传文件")
for label, relative_path in (
    ("营业执照", profile.get("license_file")),
    ("HR 在职证明", profile.get("hr_proof_file")),
):
    if not relative_path:
        continue
    try:
        path = resolve_upload_path(relative_path)
        data = path.read_bytes()
    except BusinessError:
        st.caption(f"{label}：文件缺失")
        continue
    st.download_button(label, data, file_name=path.name, key=f"company_dl_{label}")

theme.section_title("品牌展示预览", "学生将在岗位列表与详情页看到以下内容")
components.company_brand_panel(profile, compact=False)
