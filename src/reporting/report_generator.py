"""
FIN SIGHT AI - Report Generator
Generates downloadable PDF and Markdown financial analysis reports.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.config import REPORTS_DIR
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def _format_metrics_md(metrics: Dict[str, Any]) -> str:
    if not metrics:
        return "*No financial metrics were extracted.*"
    rows = ["| Metric | Value | Period | Source Page |", "|--------|-------|--------|-------------|"]
    for key, m in metrics.items():
        label = key.replace("_", " ").title()
        val = m.get("raw", str(m.get("value", "N/A")))
        period = m.get("period", "N/A")
        page = str(m.get("page", "N/A"))
        rows.append(f"| {label} | {val} | {period} | {page} |")
    return "\n".join(rows)


def _format_ratios_md(ratios: Dict[str, Any]) -> str:
    if not ratios:
        return "*No ratios calculated.*"
    rows = [
        "| Ratio | Formula | Result | Period | Status |",
        "|-------|---------|--------|--------|--------|",
    ]
    for name, r in ratios.items():
        result_str = f"{r.result:.2f}{r.unit}" if r.result is not None else "N/A"
        status = "✅ Valid" if r.is_valid and r.result is not None else f"⚠️ {r.error_message}"
        rows.append(f"| {name} | {r.formula} | {result_str} | {r.period or 'N/A'} | {status} |")
    return "\n".join(rows)


def _format_risks_md(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "*No risk findings.*"
    parts = []
    for f in findings:
        level_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Info": "ℹ️"}.get(f["level"], "")
        parts.append(
            f"### {level_emoji} [{f['level']}] {f['title']}\n"
            f"- **Detail**: {f['detail']}\n"
            f"- **Explanation**: {f['explanation']}"
        )
    return "\n\n".join(parts)


def _synthesize_executive_summary(
    document_name: str,
    metrics: Dict[str, Any],
    ratios: Dict[str, Any],
) -> str:
    """Automatically constructs an executive financial summary from audited metrics and ratios."""
    if not metrics:
        return "No financial metrics available in the loaded document to generate an executive summary."

    rev = metrics.get("revenue", {})
    gp = metrics.get("gross_profit", {})
    ebit = metrics.get("operating_income", {})
    ni = metrics.get("net_income", {})
    ta = metrics.get("total_assets", {})
    debt = metrics.get("total_debt", {})
    cash = metrics.get("cash_and_equivalents", {})

    rev_val = rev.get("raw") or (f"${rev.get('value'):,.1f}M" if rev.get("value") is not None else None)
    gp_val = gp.get("raw") or (f"${gp.get('value'):,.1f}M" if gp.get("value") is not None else None)
    ebit_val = ebit.get("raw") or (f"${ebit.get('value'):,.1f}M" if ebit.get("value") is not None else None)
    ni_val = ni.get("raw") or (f"${ni.get('value'):,.1f}M" if ni.get("value") is not None else None)
    ta_val = ta.get("raw") or (f"${ta.get('value'):,.1f}M" if ta.get("value") is not None else None)
    debt_val = debt.get("raw") or (f"${debt.get('value'):,.1f}M" if debt.get("value") is not None else None)
    cash_val = cash.get("raw") or (f"${cash.get('value'):,.1f}M" if cash.get("value") is not None else None)

    cr_obj = ratios.get("current_ratio") if ratios else None
    de_obj = ratios.get("debt_to_equity") if ratios else None
    cr_val = f"{cr_obj.result:.2f}x" if (cr_obj and hasattr(cr_obj, "result") and cr_obj.result) else None
    de_val = f"{de_obj.result:.2f}x" if (de_obj and hasattr(de_obj, "result") and de_obj.result) else None

    lines = [
        f"This audited financial report synthesizes verified corporate performance and solvency disclosures for **{document_name}**."
    ]
    if rev_val:
        perf = f"Top-line revenue was audited at **{rev_val}**"
        if gp_val:
            perf += f" with gross profit of **{gp_val}**"
        if ni_val:
            perf += f", delivering a net income of **{ni_val}**."
        else:
            perf += "."
        lines.append(perf)

    if ebit_val:
        lines.append(f"Operating income (EBIT) reached **{ebit_val}**, reflecting underlying core operating viability.")

    if ta_val or debt_val or cash_val:
        bs_items = []
        if ta_val: bs_items.append(f"total assets of **{ta_val}**")
        if cash_val: bs_items.append(f"cash reserves of **{cash_val}**")
        if debt_val: bs_items.append(f"total debt of **{debt_val}**")
        lines.append(f"On the balance sheet, capital structure comprises {', '.join(bs_items)}.")

    if cr_val or de_val:
        solv = []
        if cr_val: solv.append(f"Current Liquidity Ratio of **{cr_val}**")
        if de_val: solv.append(f"Debt-to-Equity gearing of **{de_val}**")
        lines.append(f"Financial leverage and liquidity covenants show a {' and a '.join(solv)}.")

    return "\n\n".join(lines)


def generate_markdown_report(
    document_name: str = "",
    metrics: Dict[str, Any] = None,
    ratios: Dict[str, Any] = None,
    risk_findings: List[Dict[str, Any]] = None,
    financial_summary: str = "",
    validation_notes: List[str] = None,
    query: str = "",
    extra_sections: Dict[str, str] = None,
    **kwargs: Any,
) -> str:
    document_name = document_name or kwargs.get("file_name", "Financial Document")
    t0_start = time.perf_counter()
    metrics = metrics if metrics is not None else kwargs.get("metrics", {})
    ratios = ratios if ratios is not None else kwargs.get("ratios", {})
    risk_findings = risk_findings if risk_findings is not None else kwargs.get("risks", [])
    validation_notes = validation_notes if validation_notes is not None else []
    financial_summary = financial_summary or kwargs.get("financial_summary", "")

    if (
        not financial_summary
        or "demo mode" in financial_summary.lower()
        or "no llm was used" in financial_summary.lower()
        or "no financial summary" in financial_summary.lower()
        or "placeholder" in financial_summary.lower()
    ):
        financial_summary = _synthesize_executive_summary(document_name, metrics, ratios)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra_sections = extra_sections or {}

    md = f"""# 📊 FIN SIGHT AI — Financial Analysis Report

**Document**: {document_name}
**Generated**: {now}
**System**: FIN SIGHT AI v1.0

---

## Executive Summary

{financial_summary}

---

## Key Financial Metrics

{_format_metrics_md(metrics)}

---

## Financial Ratio Analysis

{_format_ratios_md(ratios)}

---

## Risk Analysis

{_format_risks_md(risk_findings)}

---

## Validation Notes

{chr(10).join(f'- {n}' for n in validation_notes) if validation_notes else '*No validation notes.*'}

---

## Data Limitations

- Automatic metric extraction may miss values in non-standard formats or image-based PDFs.
- Growth ratios require at least two reporting periods; single-period documents will show N/A.
- Risk findings are based on rule-based heuristics and should not be treated as definitive financial advice.
- All monetary values are as reported in the document and may use different units (crore, million, etc.).

---

*Report generated by FIN SIGHT AI | For educational and analytical purposes only.*
"""
    t_dur = time.perf_counter() - t0_start
    try:
        from src.monitoring.performance import PerformanceMonitor
        PerformanceMonitor().record_operation(
            operation_type="report_generation",
            operation_name=f"Markdown Report: {document_name}",
            duration_seconds=t_dur,
            status="success",
            details={"document": document_name, "chars": len(md)},
        )
    except Exception as e:
        logger.warning(f"Could not record report generation APM: {e}")
    return md


def save_markdown_report(content: str, filename: str = "") -> Path:
    """Save a Markdown report to disk and return the file path."""
    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fin_sight_report_{ts}.md"
    path = REPORTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    logger.info("Markdown report saved: %s", path)
    return path


def generate_pdf_report(
    document_name: str = "",
    metrics: Dict[str, Any] = None,
    ratios: Dict[str, Any] = None,
    risk_findings: List[Dict[str, Any]] = None,
    financial_summary: str = "",
    validation_notes: List[str] = None,
    **kwargs: Any,
) -> Optional[bytes]:
    """
    Generate a PDF report using fpdf2.

    Returns:
        PDF bytes, or None if pdf generation fails.
    """
    document_name = document_name or kwargs.get("file_name", "Financial Document")
    t0_pdf = time.perf_counter()
    metrics = metrics if metrics is not None else kwargs.get("metrics", {})
    ratios = ratios if ratios is not None else kwargs.get("ratios", {})
    risk_findings = risk_findings if risk_findings is not None else kwargs.get("risks", [])
    validation_notes = validation_notes if validation_notes is not None else []
    financial_summary = financial_summary or kwargs.get("financial_summary", "")
    if (
        not financial_summary
        or "demo mode" in financial_summary.lower()
        or "no llm was used" in financial_summary.lower()
        or "no financial summary" in financial_summary.lower()
        or "placeholder" in financial_summary.lower()
    ):
        financial_summary = _synthesize_executive_summary(document_name, metrics, ratios)
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 12, "FIN SIGHT AI - Financial Analysis Report", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Document: {document_name}", ln=True, align="C")
        pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        pdf.ln(8)

        def section_title(title):
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_fill_color(30, 60, 120)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, title, ln=True, fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 10)
            pdf.ln(2)

        def body_text(text, bold=False):
            pdf.set_font("Helvetica", "B" if bold else "", 10)
            # Clean text for PDF (remove emoji / non-latin chars)
            import re
            text = re.sub(r"[^\x00-\x7F]+", "", text)
            pdf.multi_cell(0, 6, text)
            pdf.ln(1)

        # Executive Summary
        section_title("Executive Summary")
        summary = financial_summary or "No financial summary generated yet."
        # Strip markdown
        import re
        summary = re.sub(r"[#*>`_~]", "", summary)
        body_text(summary[:2000])

        # Metrics
        section_title("Key Financial Metrics")
        if metrics:
            for key, m in metrics.items():
                label = key.replace("_", " ").title()
                val = m.get("raw", str(m.get("value", "N/A")))
                period = m.get("period", "")
                body_text(f"{label}: {val}" + (f" ({period})" if period else ""))
        else:
            body_text("No metrics extracted.")

        # Ratios
        section_title("Financial Ratio Analysis")
        if ratios:
            for name, r in ratios.items():
                if r.result is not None:
                    body_text(f"{name}: {r.result:.2f}{r.unit}", bold=True)
                    body_text(f"  Formula: {r.formula}")
                    if r.interpretation:
                        body_text(f"  {r.interpretation}")
                else:
                    body_text(f"{name}: Not available - {r.error_message}")
        else:
            body_text("No ratios calculated.")

        # Risks
        section_title("Risk Analysis")
        if risk_findings:
            for f in risk_findings:
                body_text(f"[{f['level']}] {f['title']}", bold=True)
                body_text(f"  {f['detail']}")
                body_text(f"  {f['explanation']}")
                pdf.ln(2)
        else:
            body_text("No significant risks identified.")

        # Validation
        section_title("Validation Notes")
        if validation_notes:
            for note in validation_notes:
                note_clean = re.sub(r"[^\x00-\x7F]+", "", note)
                body_text(f"- {note_clean}")
        else:
            body_text("No validation notes.")

        # Footer
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "Generated by FIN SIGHT AI | For educational and analytical purposes only.", align="C")

        pdf_bytes = bytes(pdf.output())
        t_dur_pdf = time.perf_counter() - t0_pdf
        try:
            from src.monitoring.performance import PerformanceMonitor
            PerformanceMonitor().record_operation(
                operation_type="report_generation",
                operation_name=f"PDF Report: {document_name}",
                duration_seconds=t_dur_pdf,
                status="success",
                details={"document": document_name, "bytes": len(pdf_bytes)},
            )
        except Exception as e:
            logger.warning(f"Could not record PDF report APM: {e}")
        return pdf_bytes

    except ImportError:
        logger.warning("fpdf2 not installed. PDF generation unavailable.")
        try:
            from src.monitoring.performance import PerformanceMonitor
            PerformanceMonitor().record_operation(
                operation_type="report_generation",
                operation_name=f"PDF Report: {document_name}",
                duration_seconds=time.perf_counter() - t0_pdf,
                status="failed",
                error_message="fpdf2 not installed",
            )
        except Exception:
            pass
        return None
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        try:
            from src.monitoring.performance import PerformanceMonitor
            PerformanceMonitor().record_operation(
                operation_type="report_generation",
                operation_name=f"PDF Report: {document_name}",
                duration_seconds=time.perf_counter() - t0_pdf,
                status="failed",
                error_message=str(exc),
            )
        except Exception:
            pass
        return None
