"""
FIN SIGHT AI - Page 8: Executive Report Generation & Export
Compiles extracted financial metrics, Python-verified ratios, solvency risks,
and multi-period trends into exportable Markdown and PDF reports.
"""
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="Report Generation | FIN SIGHT AI",
    page_icon="📋",
    layout="wide"
)

from src.ui.theme import (
    apply_light_theme,
    render_sidebar_brand,
    render_page_header,
    render_page_navigation,
    render_empty_state,
)
apply_light_theme()
render_sidebar_brand()

from src.finance.metric_extraction import metrics_summary
from src.finance.ratio_calculator import FinancialRatioCalculator
from src.finance.trend_analysis import analyse_trends, identify_risks_from_trends
from src.reporting.report_generator import generate_markdown_report, generate_pdf_report

render_page_header(
    title="Executive Report Compilation & Export",
    subtitle="Export audited financial intelligence summaries in publication-ready PDF and Markdown formats."
)

doc_session = st.session_state.get("document_session")
if doc_session is None:
    render_empty_state(
        title="No Document Loaded for Report Export",
        description="Please upload or input financial statements to compile an executive report.",
        action_label="Go to Ingestion Portal",
        action_page="pages/1_Upload_Report.py"
    )
    st.stop()

# ── Load or compute analysis data ────────────────────────────────────────────
cache = st.session_state.get("analysis_cache", {})
if "ratios" not in cache:
    metrics = metrics_summary(doc_session.extracted_metrics_raw)
    ratios_obj = FinancialRatioCalculator().calculate_all(metrics)
    trends = analyse_trends(doc_session.extracted_metrics_raw)
    cache["metrics"] = metrics
    cache["ratios"] = ratios_obj
    cache["trends"] = trends
    st.session_state.analysis_cache = cache
else:
    metrics = cache["metrics"]
    ratios_obj = cache["ratios"]
    trends = cache["trends"]

risk_findings = identify_risks_from_trends(trends, ratios_obj)

last_state = st.session_state.get("last_workflow_state")
financial_summary = last_state.get("financial_summary", "") if last_state else ""
if financial_summary and ("demo mode" in financial_summary.lower() or "no llm was used" in financial_summary.lower() or "no financial summary" in financial_summary.lower()):
    financial_summary = ""
validation_notes = last_state.get("validation_notes", []) if last_state else []

# Generate Markdown content
md_report = generate_markdown_report(
    document_name=doc_session.file_name,
    metrics=metrics,
    ratios=ratios_obj,
    risk_findings=risk_findings,
    financial_summary=financial_summary,
    validation_notes=validation_notes,
)

col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    st.download_button(
        label="📥 Download Markdown Report (.md)",
        data=md_report.encode("utf-8"),
        file_name=f"FIN_SIGHT_AI_Report_{doc_session.file_name}.md",
        mime="text/markdown",
        type="primary",
        use_container_width=True,
    )

with col_dl2:
    try:
        pdf_bytes = generate_pdf_report(
            document_name=doc_session.file_name,
            metrics=metrics,
            ratios=ratios_obj,
            risk_findings=risk_findings,
            financial_summary=financial_summary,
            validation_notes=validation_notes,
        )
        st.download_button(
            label="📄 Download Formatted PDF Report (.pdf)",
            data=pdf_bytes,
            file_name=f"FIN_SIGHT_AI_Report_{doc_session.file_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as exc:
        st.warning(f"PDF formatting library notice: {exc}. Markdown export remains fully functional.")

st.markdown("---")
st.markdown("### 📄 Preview of Compiled Executive Report")
st.markdown(md_report)

# ── Standard Page Navigation ─────────────────────────────────────────────────
render_page_navigation(
    prev_page="pages/7_Evidence_Explorer.py",
    next_page="pages/9_System_Performance.py",
    prev_label="Evidence Explorer",
    next_label="System Performance",
)
