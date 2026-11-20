"""全平台视觉主题样式（仅存放 CSS，由 views.theme 统一注入）。"""

THEME_CSS = """
:root {
    --cr-primary: #4F46E5;
    --cr-primary-dark: #4338CA;
    --cr-primary-soft: #EEF2FF;
    --cr-accent: #0EA5E9;
    --cr-success: #10B981;
    --cr-warning: #F59E0B;
    --cr-danger: #EF4444;
    --cr-ink: #0F172A;
    --cr-ink-soft: #475569;
    --cr-border: #E2E8F0;
    --cr-surface: #FFFFFF;
    --cr-canvas: #F6F8FC;
    --cr-radius: 16px;
    --cr-shadow: 0 1px 2px rgba(15, 23, 42, .04),
                 0 8px 24px rgba(15, 23, 42, .06);
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--cr-canvas);
    color: var(--cr-ink);
    font-family: "Inter", "PingFang SC", "Microsoft YaHei", "Segoe UI",
                 system-ui, sans-serif;
}

[data-testid="stHeader"] { background: transparent; }

[data-testid="stSidebar"] {
    background: #0F172A;
    border-right: 1px solid rgba(255, 255, 255, .06);
}
[data-testid="stSidebar"] * { color: #E2E8F0; }
[data-testid="stSidebar"] a { border-radius: 10px; }
[data-testid="stSidebar"] a:hover { background: rgba(255, 255, 255, .08); }
[data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, .12); }
[data-testid="stSidebar"] button {
    background: rgba(255, 255, 255, .08) !important;
    border: 1px solid rgba(255, 255, 255, .18) !important;
    color: #F8FAFC !important;
}

.block-container {
    padding-top: 2.2rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}

h1, h2, h3 { letter-spacing: -.02em; color: var(--cr-ink); }
h1 { font-size: 1.9rem !important; font-weight: 750 !important; }
h2 { font-size: 1.4rem !important; font-weight: 700 !important; }
h3 { font-size: 1.15rem !important; font-weight: 650 !important; }
p, label, .stMarkdown { color: var(--cr-ink-soft); }

.cr-hero {
    background: linear-gradient(120deg, #4F46E5 0%, #6366F1 45%, #0EA5E9 100%);
    border-radius: 22px;
    padding: 30px 34px;
    color: #FFFFFF;
    margin-bottom: 20px;
    box-shadow: 0 18px 40px rgba(79, 70, 229, .22);
}
.cr-hero h1, .cr-hero h2 {
    color: #FFFFFF !important;
    margin: 0 0 6px 0 !important;
}
.cr-hero p {
    color: rgba(255, 255, 255, .86);
    margin: 0;
    font-size: .98rem;
}
.cr-hero-badge {
    display: inline-block;
    padding: 3px 12px;
    margin-bottom: 12px;
    border-radius: 999px;
    background: rgba(255, 255, 255, .16);
    border: 1px solid rgba(255, 255, 255, .28);
    color: #FFFFFF;
    font-size: .76rem;
    letter-spacing: .08em;
    text-transform: uppercase;
}

.cr-section-title {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin: 26px 0 10px 0;
}
.cr-section-title strong {
    font-size: 1.12rem;
    color: var(--cr-ink);
    font-weight: 700;
}
.cr-section-title span { font-size: .86rem; color: #94A3B8; }

[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--cr-surface);
    border: 1px solid var(--cr-border) !important;
    border-radius: var(--cr-radius) !important;
    box-shadow: var(--cr-shadow);
    transition: transform .18s ease, box-shadow .18s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 4px rgba(15, 23, 42, .05),
                0 16px 36px rgba(79, 70, 229, .12);
}

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid var(--cr-border);
    transition: all .16s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    border-color: var(--cr-primary);
    color: var(--cr-primary);
    transform: translateY(-1px);
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4F46E5, #6366F1);
    border: none;
    color: #FFFFFF;
    box-shadow: 0 8px 18px rgba(79, 70, 229, .28);
}
.stButton > button[kind="primary"]:hover {
    color: #FFFFFF;
    box-shadow: 0 10px 24px rgba(79, 70, 229, .36);
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    border-radius: 10px !important;
    border-color: var(--cr-border) !important;
    background: #FFFFFF !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--cr-primary) !important;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, .14) !important;
}

[data-testid="stMetric"] {
    background: var(--cr-surface);
    border: 1px solid var(--cr-border);
    border-radius: var(--cr-radius);
    padding: 18px 20px;
    box-shadow: var(--cr-shadow);
}
[data-testid="stMetricValue"] { color: var(--cr-primary-dark); }

[data-testid="stExpander"] {
    border-radius: 12px !important;
    border: 1px solid var(--cr-border) !important;
    background: var(--cr-surface);
}
[data-testid="stTabs"] button { font-weight: 600; }

.stAlert { border-radius: 12px; }

.cr-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    border-radius: 16px;
    background: linear-gradient(135deg, #EEF2FF, #E0F2FE);
    border: 1px solid var(--cr-border);
    color: var(--cr-primary-dark);
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: -.04em;
}
.cr-brand-name {
    font-size: 1.12rem;
    font-weight: 750;
    color: var(--cr-ink);
    margin-bottom: 2px;
}
.cr-brand-meta { font-size: .85rem; color: #64748B; }
.cr-brand-intro {
    font-size: .92rem;
    color: var(--cr-ink-soft);
    line-height: 1.65;
}

.cr-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.cr-chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--cr-primary-soft);
    color: var(--cr-primary-dark);
    font-size: .76rem;
    font-weight: 600;
}
.cr-chip--muted { background: #F1F5F9; color: #475569; }
.cr-chip--accent { background: #E0F2FE; color: #0369A1; }

.cr-job-title { font-size: 1.1rem; font-weight: 700; color: var(--cr-ink); }
.cr-job-meta { font-size: .85rem; color: #64748B; margin-top: 2px; }
.cr-divider { height: 1px; background: var(--cr-border); margin: 14px 0; }

@media (max-width: 768px) {
    .block-container {
        padding: 1.1rem .9rem 2rem .9rem;
        max-width: 100%;
    }
    .cr-hero { padding: 22px 20px; border-radius: 18px; }
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.2rem !important; }
    [data-testid="stMetric"] { padding: 14px; }
    [data-testid="stSidebar"] { min-width: 250px; }
}
"""
