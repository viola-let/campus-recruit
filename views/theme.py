"""全平台视觉主题：注入统一样式，并提供主视觉与标题组件。

样式常量集中在 views/theme_css.py；页面只需调用 apply_theme()。
"""

import html

import streamlit as st

from views.theme_css import THEME_CSS

BRAND_NAME = "CampusRecruit"
BRAND_SLOGAN = "连接校园与企业的智能校招平台"


def apply_theme() -> None:
    """注入全局样式，页面顶部调用一次即可。"""
    st.html(f"<style>{THEME_CSS}</style>")


def hero(title: str, subtitle: str = "", badge: str = "CampusRecruit") -> None:
    """渐变主视觉区，用于各角色首页与重点页面。"""
    badge_html = f'<div class="cr-hero-badge">{html.escape(badge)}</div>'
    subtitle_html = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    st.html(
        f'<div class="cr-hero">{badge_html}<h1>{html.escape(title)}</h1>'
        f"{subtitle_html}</div>"
    )


def section_title(title: str, caption: str = "") -> None:
    """带辅助说明的小节标题。"""
    caption_html = f"<span>{html.escape(caption)}</span>" if caption else ""
    st.html(
        f'<div class="cr-section-title"><strong>{html.escape(title)}</strong>'
        f"{caption_html}</div>"
    )


def sidebar_brand() -> None:
    """侧边栏品牌区。"""
    st.html(
        '<div style="padding:6px 0 14px 0;">'
        '<div class="cr-brand-name" style="color:#F8FAFC;font-size:1.05rem;">'
        f"{BRAND_NAME}</div>"
        '<div style="font-size:.78rem;color:#94A3B8;">'
        f"{BRAND_SLOGAN}</div>"
        "</div>"
    )
