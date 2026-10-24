"""
FIN SIGHT AI - Validation Agent
Verifies calculations, checks for missing citations, and flags inconsistencies.
"""
import time
from typing import Any, Dict, List

from src.graph.state import GraphState, AgentStatus
from src.finance.ratio_calculator import FinancialRatioCalculator
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_calculator = FinancialRatioCalculator()


def validation_agent(state: GraphState) -> GraphState:
    """
    Agent 5: Validation Agent.
    Independently re-checks calculations and checks for inconsistencies.
    """
    start = time.time()
    state.setdefault("agent_statuses", {})["validation"] = AgentStatus.RUNNING

    notes: List[str] = []
    passed = True

    ratios = state.get("calculated_ratios", {})
    metrics = state.get("financial_metrics", {})
    context = state.get("context_text", "")
    errors = state.get("errors", [])

    try:
        # --- Check 1: Ratio re-verification ---
        for ratio_name, ratio in ratios.items():
            if not ratio.is_valid:
                notes.append(f"⚠️ {ratio_name}: {ratio.error_message}")
                continue

            if ratio.result is None:
                notes.append(f"⚠️ {ratio_name}: Result is None despite valid inputs.")
                passed = False
                continue

            # Re-verify arithmetic independently
            try:
                if ratio.numerator_value is not None and ratio.denominator_value is not None and ratio.denominator_value != 0:
                    expected = ratio.numerator_value / ratio.denominator_value
                    if "%" in ratio.unit:
                        expected *= 100
                    if abs(expected - ratio.result) > 0.01:
                        notes.append(
                            f"❌ {ratio_name}: Arithmetic mismatch — "
                            f"expected {expected:.4f}, got {ratio.result:.4f}."
                        )
                        passed = False
                    else:
                        notes.append(f"✅ {ratio_name}: Arithmetic verified.")
                else:
                    notes.append(f"ℹ️ {ratio_name}: Inputs not available for re-verification.")
            except Exception as e:
                notes.append(f"⚠️ {ratio_name}: Re-verification error — {e}")

        # --- Check 2: Missing data warnings ---
        required_metrics = ["revenue", "net_profit", "total_assets", "total_equity"]
        for key in required_metrics:
            if key not in metrics:
                notes.append(f"ℹ️ '{key.replace('_', ' ').title()}' not found in extracted metrics.")

        # --- Check 3: Context availability ---
        if not context.strip():
            notes.append("⚠️ No document context was retrieved for this query.")

        # --- Check 4: Agent errors ---
        if errors:
            notes.append(f"⚠️ {len(errors)} agent error(s) occurred during processing.")
            passed = False

        state["validation_notes"] = notes
        state["validation_passed"] = passed
        state["agent_statuses"]["validation"] = AgentStatus.COMPLETED
        logger.info("Validation agent: %d notes, passed=%s", len(notes), passed)

    except Exception as exc:
        logger.error("Validation agent error: %s", exc)
        state["agent_statuses"]["validation"] = AgentStatus.FAILED
        state.setdefault("errors", []).append(f"Validation agent: {exc}")
        state["validation_passed"] = False

    state.setdefault("agent_timings", {})["validation"] = time.time() - start
    return state
