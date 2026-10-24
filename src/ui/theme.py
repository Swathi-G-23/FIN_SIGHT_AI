"""
FIN SIGHT AI - Professional Light Theme & UI Design System
Enterprise banking and financial business intelligence styling.
Centralized typography, standard color palette, consistent card hierarchy,
and workflow navigation controls across all pages.
"""
from typing import Optional
import streamlit as st

# ── Color Palette Constants ──────────────────────────────────────────────────
PAGE_BG = "#F5F7FA"
CARD_BG = "#FFFFFF"
PRIMARY_NAVY = "#17365D"
PRIMARY_BLUE = "#3976C5"
SOFT_BLUE = "#EAF2FF"
TEXT_PRIMARY = "#253247"
TEXT_MUTED = "#697586"
BORDER_COLOR = "#E1E7EF"
SUCCESS_GREEN = "#24865B"
WARNING_AMBER = "#D99020"
ERROR_RED = "#C74440"

# Unified palette dictionary
PALETTE = {
    "navy_primary": PRIMARY_NAVY,
    "blue_accent": PRIMARY_BLUE,
    "soft_blue": SOFT_BLUE,
    "text_primary": TEXT_PRIMARY,
    "text_muted": TEXT_MUTED,
    "border_color": BORDER_COLOR,
    "green_accent": SUCCESS_GREEN,
    "gold_accent": WARNING_AMBER,
    "coral_accent": ERROR_RED,
    "bg_white": CARD_BG,
    "bg_light": PAGE_BG,
}

# Standardized chart defaults
CHART_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#F8FAFC",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", color="#253247", size=13),
    margin=dict(l=40, r=40, t=50, b=40),
)

LIGHT_THEME_CSS = """
<style>
/* ── Typography & Base Styles ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    color: #253247;
    font-size: 15px;
    line-height: 1.6;
}

/* Page Background */
.stApp {
    background-color: #F5F7FA !important;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E1E7EF !important;
}

/* ── Heading Hierarchy ── */
h1, .fin-page-title {
    font-size: 32px !important;
    font-weight: 700 !important;
    color: #17365D !important;
    letter-spacing: -0.02em !important;
    line-height: 1.25 !important;
    margin-top: 0 !important;
    margin-bottom: 6px !important;
}

.fin-page-subtitle {
    font-size: 15px !important;
    color: #697586 !important;
    line-height: 1.5 !important;
    margin-bottom: 20px !important;
}

h2, .fin-section-title {
    font-size: 24px !important;
    font-weight: 600 !important;
    color: #17365D !important;
    letter-spacing: -0.01em !important;
    margin-top: 24px !important;
    margin-bottom: 12px !important;
}

h3 {
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #17365D !important;
    margin-top: 18px !important;
    margin-bottom: 10px !important;
}

h4, .fin-card-heading {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #17365D !important;
    margin-bottom: 6px !important;
}

/* Paragraphs & Body text - exclude buttons so button text contrast is preserved */
p:not(button p):not([data-testid^="stBaseButton"] p), li {
    font-size: 15px !important;
    color: #253247 !important;
}

/* Labels for inputs */
label, [data-testid="stWidgetLabel"] p {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #253247 !important;
}

/* Small helper / captions */
.stCaption, small, .fin-caption {
    font-size: 13px !important;
    color: #697586 !important;
    line-height: 1.4 !important;
}

/* ── Financial Cards & Containers ── */
.fin-card {
    background-color: #FFFFFF;
    border: 1px solid #E1E7EF;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 18px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03), 0 1px 2px rgba(0, 0, 0, 0.02);
}

.fin-card-header {
    font-size: 13px;
    font-weight: 600;
    color: #697586;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 8px;
}

.fin-card-value {
    font-size: 28px;
    font-weight: 700;
    color: #17365D;
    line-height: 1.2;
}

.fin-card-delta {
    font-size: 13px;
    font-weight: 500;
    margin-top: 6px;
}

/* ── Badges & Status Pills ── */
.badge-pill {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.badge-success {
    background-color: #E6F4EA;
    color: #137333;
    border: 1px solid #CEEAD6;
}

.badge-info {
    background-color: #EAF2FF;
    color: #17365D;
    border: 1px solid #D2E3FC;
}

.badge-warning {
    background-color: #FEF7E0;
    color: #B06000;
    border: 1px solid #FEEFC3;
}

.badge-danger {
    background-color: #FCE8E6;
    color: #C5221F;
    border: 1px solid #FAD2CF;
}

/* ── Callout Box ── */
.callout-box {
    background-color: #EAF2FF;
    border-left: 4px solid #3976C5;
    padding: 14px 18px;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
    color: #17365D;
    margin-bottom: 18px;
    line-height: 1.5;
}

/* ── DataFrames & Tables ── */
div[data-testid="stDataFrame"] {
    border: 1px solid #E1E7EF !important;
    border-radius: 8px !important;
    background-color: #FFFFFF !important;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #697586 !important;
    padding: 10px 16px !important;
}

button[aria-selected="true"] {
    color: #17365D !important;
    font-weight: 600 !important;
    border-bottom-color: #17365D !important;
}

/* ── Centralized Professional Button Styling with WCAG AAA Contrast ── */

/* 1. Primary Buttons: Dark Navy background with crisp #FFFFFF text */
button[kind="primary"],
div.stButton > button[kind="primary"],
div.stDownloadButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"],
div[data-testid="stFormSubmitButton"] > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button {
    background-color: #17365D !important;
    border: 1px solid #17365D !important;
    color: #FFFFFF !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    padding: 8px 18px !important;
    transition: all 0.15s ease-in-out !important;
    box-shadow: 0 1px 2px rgba(15, 37, 64, 0.08) !important;
}

/* Ensure text elements inside primary buttons are always white */
button[kind="primary"] p,
button[kind="primary"] span,
button[kind="primary"] div,
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] span,
button[data-testid="stBaseButton-primary"] div,
div.stButton > button[kind="primary"] p,
div.stButton > button[kind="primary"] span,
div.stDownloadButton > button[kind="primary"] p,
div.stDownloadButton > button[kind="primary"] span,
div[data-testid="stFormSubmitButton"] > button p,
div[data-testid="stFormSubmitButton"] > button span {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}

/* Primary hover & focus states */
button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
div.stButton > button[kind="primary"]:hover,
div.stDownloadButton > button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
    background-color: #3976C5 !important;
    border-color: #3976C5 !important;
    color: #FFFFFF !important;
}

button[kind="primary"]:hover p,
button[data-testid="stBaseButton-primary"]:hover p,
div.stButton > button[kind="primary"]:hover p,
div[data-testid="stFormSubmitButton"] > button:hover p {
    color: #FFFFFF !important;
}

button[kind="primary"]:active,
button[data-testid="stBaseButton-primary"]:active,
div[data-testid="stFormSubmitButton"] > button:active {
    background-color: #0F2540 !important;
    border-color: #0F2540 !important;
    color: #FFFFFF !important;
}

button[kind="primary"]:focus:not(:active),
button[data-testid="stBaseButton-primary"]:focus:not(:active) {
    border-color: #17365D !important;
    box-shadow: 0 0 0 3px rgba(23, 54, 93, 0.25) !important;
}

button[kind="primary"]:disabled,
button[data-testid="stBaseButton-primary"]:disabled,
div[data-testid="stFormSubmitButton"] > button:disabled {
    background-color: #94A3B8 !important;
    border-color: #94A3B8 !important;
    color: #F8FAFC !important;
    cursor: not-allowed !important;
    opacity: 0.75 !important;
}

button[kind="primary"]:disabled p,
button[data-testid="stBaseButton-primary"]:disabled p {
    color: #F8FAFC !important;
}

/* 2. Secondary & Interactive Standard Buttons */
button[kind="secondary"],
div.stButton > button[kind="secondary"],
div.stDownloadButton > button[kind="secondary"],
button[data-testid="stBaseButton-secondary"],
div.stButton > button:not([kind="primary"]),
div.stDownloadButton > button:not([kind="primary"]) {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    color: #17365D !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 8px 18px !important;
    transition: all 0.15s ease-in-out !important;
}

/* Ensure text inside secondary buttons is high-contrast dark navy */
button[kind="secondary"] p,
button[kind="secondary"] span,
button[kind="secondary"] div,
button[data-testid="stBaseButton-secondary"] p,
button[data-testid="stBaseButton-secondary"] span,
div.stButton > button:not([kind="primary"]) p,
div.stButton > button:not([kind="primary"]) span,
div.stDownloadButton > button:not([kind="primary"]) p,
div.stDownloadButton > button:not([kind="primary"]) span {
    color: #17365D !important;
    font-weight: 500 !important;
}

/* Secondary hover & active states */
button[kind="secondary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover,
div.stButton > button:not([kind="primary"]):hover,
div.stDownloadButton > button:not([kind="primary"]):hover {
    background-color: #F1F5F9 !important;
    border-color: #94A3B8 !important;
    color: #0F2540 !important;
}

button[kind="secondary"]:hover p,
div.stButton > button:not([kind="primary"]):hover p {
    color: #0F2540 !important;
}

button[kind="secondary"]:active,
button[data-testid="stBaseButton-secondary"]:active {
    background-color: #E2E8F0 !important;
    border-color: #64748B !important;
    color: #0F2540 !important;
}

button[kind="secondary"]:focus:not(:active),
button[data-testid="stBaseButton-secondary"]:focus:not(:active) {
    border-color: #3976C5 !important;
    box-shadow: 0 0 0 3px rgba(57, 118, 197, 0.25) !important;
}

button[kind="secondary"]:disabled,
button[data-testid="stBaseButton-secondary"]:disabled {
    background-color: #F8FAFC !important;
    border-color: #E2E8F0 !important;
    color: #94A3B8 !important;
    cursor: not-allowed !important;
    opacity: 0.7 !important;
}

button[kind="secondary"]:disabled p,
button[data-testid="stBaseButton-secondary"]:disabled p {
    color: #94A3B8 !important;
}

/* Metric Widget Container */
div[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E1E7EF;
    border-radius: 8px;
    padding: 14px 18px;
}
div[data-testid="stMetricLabel"] p {
    font-size: 13px !important;
    color: #697586 !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
}
div[data-testid="stMetricValue"] div {
    color: #17365D !important;
    font-weight: 700 !important;
    font-size: 24px !important;
}
</style>
"""


def apply_light_theme():
    """Injects global light theme CSS into the Streamlit session."""
    st.markdown(LIGHT_THEME_CSS, unsafe_allow_html=True)


def inject_theme():
    """Alias for apply_light_theme."""
    apply_light_theme()


def render_page_header(title: str, subtitle: str = ""):
    """Renders standardized typography header for application pages."""
    sub_html = f"<div class='fin-page-subtitle'>{subtitle}</div>" if subtitle else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 18px;">
            <h1 class="fin-page-title">{title}</h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = ""):
    """Renders section heading with consistent styling."""
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def kpi_card(title: str, value: str, delta: str = "", delta_type: str = "positive"):
    """Renders standard metric card."""
    st.metric(title, value, delta=delta if delta else None)


def render_sidebar_brand():
    """Renders the FIN SIGHT AI enterprise brand in the sidebar."""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 12px 0 16px 0; border-bottom: 1px solid #E1E7EF; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="background: #17365D; color: white; width: 34px; height: 34px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px;">
                        FS
                    </div>
                    <div>
                        <div style="font-weight: 700; font-size: 16px; color: #17365D; letter-spacing: -0.02em;">FIN SIGHT AI</div>
                        <div style="font-size: 11px; color: #697586; font-weight: 500;">Financial Intelligence Platform</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_page_navigation(
    prev_page: Optional[str] = None,
    next_page: Optional[str] = None,
    prev_label: Optional[str] = None,
    next_label: Optional[str] = None,
):
    """
    Renders standard navigation buttons at the bottom of pages.
    Preserves all active state (company, period, documents) using Streamlit's st.switch_page.
    """
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    col_prev, col_spacer, col_next = st.columns([2, 3, 2])

    with col_prev:
        if prev_page:
            p_text = f"← {prev_label}" if prev_label else "← Previous Page"
            if st.button(p_text, use_container_width=True, key=f"nav_prev_{prev_page}"):
                st.switch_page(prev_page)

    with col_next:
        if next_page:
            n_text = f"{next_label} →" if next_label else "Next Page →"
            if st.button(n_text, type="primary", use_container_width=True, key=f"nav_next_{next_page}"):
                st.switch_page(next_page)


def render_empty_state(
    title: str = "No Financial Report Uploaded",
    description: str = "Upload a company PDF, Excel spreadsheet, CSV dataset, or enter financial metrics to begin automated analysis.",
    action_label: str = "Go to Ingestion Portal",
    action_page: str = "pages/1_Upload_Report.py",
):
    """Renders an enterprise clean empty state container."""
    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 44px 24px; text-align: center; margin: 20px 0;">
            <div style="font-size: 36px; margin-bottom: 10px;">📑</div>
            <div style="font-size: 18px; font-weight: 600; color: #17365D; margin-bottom: 8px;">{title}</div>
            <div style="font-size: 14px; color: #697586; max-width: 520px; margin: 0 auto 18px auto; line-height: 1.5;">
                {description}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(f"⚡ {action_label}", use_container_width=True, type="primary"):
            st.switch_page(action_page)
