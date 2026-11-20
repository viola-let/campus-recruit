"""通用页面组件：企业品牌卡、标签、职位元信息。"""

import html
import re

import streamlit as st

from core.config import JOB_TYPE_LABELS
from core.errors import BusinessError
from core.security import resolve_upload_path

TAG_SPLIT_PATTERN = re.compile(r"[\s,，、;；/|]+")


def _pick(source: dict, *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value:
            return str(value)
    return ""


def brand_fields(source: dict) -> dict:
    """兼容企业资料行与职位联表行两种字段命名。"""
    raw_name = _pick(source, "company_name", "name") or "企业"
    # 种子数据的企业名带有“（行业·规模·融资·城市）”后缀，展示时去掉
    name = re.sub(r"（[^）]*）\s*$", "", raw_name).strip() or raw_name
    return {
        "name": name,
        "logo": _pick(source, "company_logo_path", "logo_path"),
        "intro": _pick(source, "company_intro", "intro"),
        "culture": _pick(source, "company_culture", "culture"),
        "industry": _pick(source, "company_industry", "industry"),
        "size": _pick(source, "company_size"),
        "funding": _pick(source, "company_funding", "funding_stage"),
        "city": _pick(source, "company_city", "city"),
        "benefits": _pick(source, "company_benefits", "benefits"),
    }


def split_tags(text: str) -> list[str]:
    return [item for item in TAG_SPLIT_PATTERN.split(text or "") if item]


def chips(items: list[str], variant: str = "") -> None:
    """渲染一组圆角标签。"""
    if not items:
        return
    css_class = f"cr-chip {variant}".strip()
    parts = "".join(
        f'<span class="{css_class}">{html.escape(item)}</span>' for item in items
    )
    st.html(f'<div class="cr-chips">{parts}</div>')


def _logo_file(relative_path: str):
    if not relative_path:
        return None
    try:
        path = resolve_upload_path(relative_path)
    except BusinessError:
        return None
    return path if path.is_file() else None


def render_logo(source: dict, size: int = 64) -> None:
    """展示企业 logo；未上传时按企业名首字生成占位标识。"""
    fields = brand_fields(source)
    path = _logo_file(fields["logo"])
    if path is not None:
        st.image(str(path), width=size)
        return
    initial = fields["name"][:1] or "企"
    st.html(
        f'<div class="cr-logo" style="width:{size}px;height:{size}px;'
        f'font-size:{max(16, int(size * 0.42))}px;">{html.escape(initial)}</div>'
    )


def company_brand_panel(source: dict, compact: bool = False) -> None:
    """企业专属信息卡：logo、名称、行业规模与简介、文化、福利。"""
    fields = brand_fields(source)
    with st.container(border=True):
        logo_col, info_col = st.columns([1, 6], vertical_alignment="center")
        with logo_col:
            render_logo(source, 56 if compact else 76)
        with info_col:
            meta = " · ".join(
                filter(
                    None,
                    [
                        fields["industry"],
                        fields["size"],
                        fields["funding"],
                        fields["city"],
                    ],
                )
            )
            meta_html = (
                f'<div class="cr-brand-meta">{html.escape(meta)}</div>' if meta else ""
            )
            st.html(
                f'<div class="cr-brand-name">{html.escape(fields["name"])}</div>'
                f"{meta_html}"
            )

        if compact:
            if fields["intro"]:
                st.caption(fields["intro"][:80])
            return

        if fields["intro"]:
            st.markdown("**企业简介**")
            st.write(fields["intro"])
        if fields["culture"]:
            st.markdown("**企业文化**")
            st.write(fields["culture"])
        benefits = split_tags(fields["benefits"])
        if benefits:
            st.markdown("**福利标签**")
            chips(benefits, "cr-chip--accent")


def job_title_line(job: dict) -> str:
    """职位名称与基础元信息（公司、类型、城市、薪资）。"""
    featured = "⭐ " if job.get("is_featured") else ""
    job_type = JOB_TYPE_LABELS.get(job.get("job_type"), job.get("job_type") or "")
    meta = " · ".join(
        filter(
            None,
            [
                job.get("company_name"),
                job_type,
                job.get("city"),
                job.get("salary") or "薪资面议",
            ],
        )
    )
    return f"{featured}{job.get('title') or '职位'}", meta


MODULE_OWNER = "CampusRecruit 平台研发组（负责人：待补充）"


def demo_info(background: str, scenario: str, demo_points: list[str]) -> None:
    """标准化功能展示信息：开发人员、背景、适用场景与演示要点。"""
    with st.expander("功能说明与演示要点", expanded=False):
        st.markdown(f"**开发人员**：{MODULE_OWNER}")
        st.markdown(f"**功能背景**：{background}")
        st.markdown(f"**适用场景**：{scenario}")
        st.markdown("**演示要点**")
        for point in demo_points:
            st.markdown(f"- {point}")
