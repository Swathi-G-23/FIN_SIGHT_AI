"""
FIN SIGHT AI - Financial Ratio Agent
Calculates financial ratios using Python arithmetic (no LLM arithmetic).
"""
import time
from typing import Any, Dict

from src.graph.state import GraphState, AgentStatus
from src.finance.ratio_calculator import FinancialRatioCalculator
from src.finance.metric_extraction import metrics_summary
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_calculator = FinancialRatioCalculator()


def ratio_agent(
    state: GraphState,
    extracted_metrics_raw: Dict[str, Any] = None,
) -> GraphState:
    """
    Agent 3: Financial Ratio Agent.
    Computes standard financial ratios from extracted metrics.

    All calculations are done in Python; no LLM is involved in arithmetic.
    """
    start = time.time()
    state.setdefault("agent_statuses", {})["ratio"] = AgentStatus.RUNNING

    metrics_raw = extracted_metrics_raw or state.get("extracted_metrics_raw", {})

    try:
        fin_metrics = metrics_summary(metrics_raw) if metrics_raw else {}
        state["financial_metrics"] = fin_metrics

        if not fin_metrics:
            state["agent_statuses"]["ratio"] = AgentStatus.SKIPPED
            state.setdefault("warnings", []).append(
                "Ratio agent: no financial metrics available to calculate ratios."
            )
            state.setdefault("calculated_ratios", {})
        else:
            ratios = _calculator.calculate_all(fin_metrics)
            state["calculated_ratios"] = ratios
            state["agent_statuses"]["ratio"] = AgentStatus.COMPLETED

            valid = [r for r in ratios.values() if r.is_valid and r.result is not None]
            logger.info("Ratio agent: %d ratios calculated, %d valid.", len(ratios), len(valid))

    except Exception as exc:
        logger.error("Ratio agent error: %s", exc)
        state["agent_statuses"]["ratio"] = AgentStatus.FAILED
        state.setdefault("errors", []).append(f"Ratio agent: {exc}")
        state["calculated_ratios"] = {}

    state.setdefault("agent_timings", {})["ratio"] = time.time() - start
    return state
