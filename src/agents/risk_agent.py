"""
FIN SIGHT AI - Risk Agent
Identifies potential financial warning signs using transparent rule-based analysis
and optional LLM-generated explanations.
"""
import time
from typing import Any, Dict

from src.graph.state import GraphState, AgentStatus
from src.finance.trend_analysis import identify_risks_from_trends
from src.agents.llm_helper import llm_call
from src.utils.config import DEMO_MODE
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_RISK_SYSTEM = """You are a risk analyst reviewing financial reports.
Your task is to identify and explain potential financial warning signs.
- Base all findings on the data provided.
- Distinguish between rule-based findings and interpretations.
- Avoid definitive statements about solvency without full context.
- Be clear and professional. Use specific numbers.
"""


def risk_agent(state: GraphState) -> GraphState:
    """
    Agent 4: Risk Agent.
    Applies rule-based risk rules and optionally enriches with LLM explanations.
    """
    start = time.time()
    state.setdefault("agent_statuses", {})["risk"] = AgentStatus.RUNNING

    trends = state.get("trend_analysis", {})
    ratios = state.get("calculated_ratios", {})
    context = state.get("context_text", "")
    query = state.get("query", "")

    try:
        # Always run rule-based analysis
        rule_findings = identify_risks_from_trends(trends, ratios)
        state["risk_findings"] = rule_findings

        # Optionally enhance with LLM
        if not DEMO_MODE and context:
            risk_summary_text = _format_risk_findings(rule_findings)
            prompt = f"""
Query: {query}

Rule-based risk findings:
{risk_summary_text}

Document context:
{context[:3000]}

Please provide additional qualitative risk insights based on the document context,
referencing specific data points or page numbers where possible.
"""
            llm_risk = llm_call(prompt, system=_RISK_SYSTEM)
            state.setdefault("agent_outputs", {})["risk_llm"] = llm_risk

        state["agent_statuses"]["risk"] = AgentStatus.COMPLETED
        logger.info("Risk agent: %d findings identified.", len(rule_findings))

    except Exception as exc:
        logger.error("Risk agent error: %s", exc)
        state["agent_statuses"]["risk"] = AgentStatus.FAILED
        state.setdefault("errors", []).append(f"Risk agent: {exc}")

    state.setdefault("agent_timings", {})["risk"] = time.time() - start
    return state


def _format_risk_findings(findings):
    lines = []
    for f in findings:
        lines.append(f"- [{f['level']}] {f['title']}: {f['detail']}")
    return "\n".join(lines)
