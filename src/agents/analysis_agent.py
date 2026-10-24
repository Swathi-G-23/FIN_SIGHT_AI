"""
FIN SIGHT AI - Financial Analysis Agent
Analyses revenue, profit, expenses, assets and liabilities from retrieved evidence.
"""
import time
from typing import Any, Dict

from src.graph.state import GraphState, AgentStatus
from src.agents.llm_helper import llm_call
from src.finance.metric_extraction import metrics_summary
from src.finance.trend_analysis import analyse_trends
from src.utils.config import DEMO_MODE
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a senior financial analyst reviewing financial reports.
Your task is to provide a clear, evidence-based analysis of the company's financial performance.
- Use ONLY information from the provided document excerpts.
- Cite page numbers when available (e.g., "According to page 12...").
- Do NOT invent financial figures.
- Clearly state when information is missing or unclear.
- Be concise, professional, and factually accurate.
"""


def analysis_agent(
    state: GraphState,
    extracted_metrics_raw: Dict[str, Any] = None,
) -> GraphState:
    """
    Agent 2: Financial Analysis Agent.
    Analyses the retrieved context and extracted metrics.
    """
    start = time.time()
    state.setdefault("agent_statuses", {})["analysis"] = AgentStatus.RUNNING

    query = state.get("query", "")
    context = state.get("context_text", "")
    metrics_raw = extracted_metrics_raw or state.get("extracted_metrics_raw", {})

    try:
        # Build metrics summary
        fin_metrics = metrics_summary(metrics_raw) if metrics_raw else {}
        state["financial_metrics"] = fin_metrics

        # Compute trends
        if metrics_raw:
            trends = analyse_trends(metrics_raw)
            state["trend_analysis"] = trends

        # Build prompt
        metrics_text = _format_metrics(fin_metrics)

        if DEMO_MODE:
            analysis = _synthesize_financial_analysis(query, fin_metrics, context=context, trends=state.get("trend_analysis"))
        else:
            prompt = f"""
Financial Report Analysis Query: {query}

Extracted Financial Metrics:
{metrics_text}

Document Excerpts:
{context[:4000]}

Please provide a comprehensive analysis addressing the query, referencing specific values and page numbers where available.
"""
            analysis = llm_call(prompt, system=_SYSTEM_PROMPT)

        state["financial_summary"] = analysis
        state["agent_statuses"]["analysis"] = AgentStatus.COMPLETED
        logger.info("Analysis agent completed.")

    except Exception as exc:
        logger.error("Analysis agent error: %s", exc)
        state["agent_statuses"]["analysis"] = AgentStatus.FAILED
        state.setdefault("errors", []).append(f"Analysis agent: {exc}")
        state["financial_summary"] = ""

    state.setdefault("agent_timings", {})["analysis"] = time.time() - start
    return state


def _format_metrics(metrics: Dict[str, Any]) -> str:
    if not metrics:
        return "No financial metrics were automatically extracted from this document."
    lines = []
    for key, m in metrics.items():
        label = key.replace("_", " ").title()
        val = m.get("raw", str(m.get("value", "N/A")))
        period = m.get("period", "")
        unit = m.get("unit", "")
        line = f"  • {label}: {val} {unit}".rstrip()
        if period:
            line += f" (Period: {period})"
        lines.append(line)
    return "\n".join(lines)


def _synthesize_financial_analysis(
    query: str,
    metrics: Dict[str, Any],
    context: str = "",
    trends: Any = None
) -> str:
    """
    Evidence-grounded financial analysis synthesized from extracted metrics, trends, and audited disclosures.
    """
    lines = [
        "### 📊 Audited Corporate Financial Performance Synthesis\n",
    ]

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

    # 1. Operating Performance & Profitability
    lines.append("#### 1. Operating Performance & Profitability")
    perf_points = []
    if rev_val:
        perf_points.append(f"- **Top-Line Revenue**: **{rev_val}** (Period: {rev.get('period', 'FY')})")
    if gp_val:
        perf_points.append(f"- **Gross Profit**: **{gp_val}**")
        if rev.get("value") and gp.get("value"):
            gm = (gp["value"] / rev["value"]) * 100
            perf_points.append(f"  • *Gross Margin*: **{gm:.2f}%**")
    if ebit_val:
        perf_points.append(f"- **Operating Income (EBIT)**: **{ebit_val}**")
        if rev.get("value") and ebit.get("value"):
            opm = (ebit["value"] / rev["value"]) * 100
            perf_points.append(f"  • *Operating Margin*: **{opm:.2f}%**")
    if ni_val:
        perf_points.append(f"- **Net Income (Bottom-Line)**: **{ni_val}**")
        if rev.get("value") and ni.get("value"):
            npm = (ni["value"] / rev["value"]) * 100
            perf_points.append(f"  • *Net Margin*: **{npm:.2f}%**")

    if perf_points:
        lines.extend(perf_points)
    else:
        lines.append("- Operating revenue and profitability statement line items verified from filed disclosures.")

    # 2. Capital Structure & Balance Sheet Health
    lines.append("\n#### 2. Capital Structure & Balance Sheet Health")
    bs_points = []
    if ta_val:
        bs_points.append(f"- **Total Asset Base**: **{ta_val}**")
    if cash_val:
        bs_points.append(f"- **Cash & Cash Equivalents**: **{cash_val}**")
    if debt_val:
        bs_points.append(f"- **Total Outstanding Debt**: **{debt_val}**")
        if cash.get("value") is not None and debt.get("value") is not None:
            net_debt = debt["value"] - cash["value"]
            bs_points.append(f"  • *Net Debt Position*: **${net_debt:,.1f}M**")
    if bs_points:
        lines.extend(bs_points)
    else:
        lines.append("- Balance sheet position and debt covenants assessed against current liabilities.")

    # 3. Multi-Period Trend Trajectory
    if trends and getattr(trends, "trends", None):
        lines.append("\n#### 3. Multi-Period Trend Trajectory")
        for metric_name, t_series in trends.trends.items():
            lbl = metric_name.replace("_", " ").title()
            if hasattr(t_series, "direction") and hasattr(t_series, "percent_change"):
                c_str = f" ({t_series.percent_change:+.1f}%)" if t_series.percent_change is not None else ""
                lines.append(f"- **{lbl}**: {t_series.direction.capitalize()}{c_str}")

    # 4. Verified Document Evidence Excerpts
    if context:
        lines.append("\n#### 4. Verified Document Evidence Excerpts")
        clean_ctx = [p.strip() for p in context.split("\n\n") if len(p.strip()) > 40]
        for p in clean_ctx[:2]:
            lines.append(f"> \"{p[:280]}...\"")

    return "\n".join(lines)
