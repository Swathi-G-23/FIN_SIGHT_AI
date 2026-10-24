"""
FIN SIGHT AI - Trend Analysis
Analyses financial trends across available reporting periods.
"""
from typing import List, Dict, Any, Optional, Tuple

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def compute_trend(
    values: List[Tuple[str, float]],
) -> Dict[str, Any]:
    """
    Compute basic trend statistics for a metric over time.

    Args:
        values: List of (period_label, numeric_value) tuples, sorted oldest first.

    Returns:
        Dict with keys: direction, pct_change, cagr, values.
    """
    if not values:
        return {"direction": "unknown", "values": []}

    if len(values) == 1:
        return {
            "direction": "single_period",
            "values": values,
            "note": "Only one period available — trend cannot be computed.",
        }

    periods = [v[0] for v in values]
    nums = [v[1] for v in values]

    first = nums[0]
    last = nums[-1]

    direction = "increasing" if last > first else "decreasing" if last < first else "flat"

    pct_change = None
    if first and first != 0:
        pct_change = (last - first) / abs(first) * 100

    # Simple CAGR if we have years
    n_periods = len(nums) - 1
    cagr = None
    if first and first > 0 and last > 0 and n_periods > 0:
        import math
        try:
            cagr = (math.pow(last / first, 1 / n_periods) - 1) * 100
        except Exception:
            pass

    return {
        "direction": direction,
        "values": values,
        "periods": periods,
        "first_value": first,
        "last_value": last,
        "pct_change": pct_change,
        "cagr": cagr,
        "n_periods": n_periods,
    }


def analyse_trends(
    metrics: Dict[str, List[Any]],  # metric_key → List[ExtractedMetric]
) -> Dict[str, Dict[str, Any]]:
    """
    Analyse trends for all available metrics that have multiple periods.

    Returns:
        Dict mapping metric_key → trend result dict.
    """
    from src.finance.metric_extraction import ExtractedMetric

    trends = {}
    for key, metric_list in metrics.items():
        if not metric_list:
            continue

        # Group by period
        period_values: Dict[str, float] = {}
        for m in metric_list:
            if m.numeric_value is not None and m.period:
                # Use normalized value if available
                val = m.normalized_value if m.normalized_value is not None else m.numeric_value
                if m.period not in period_values:
                    period_values[m.period] = val

        if not period_values:
            continue

        # Sort by period label (lexicographic — works for YYYY and FY2023)
        sorted_vals = sorted(period_values.items(), key=lambda x: x[0])
        trends[key] = compute_trend(sorted_vals)

    return trends


def identify_risks_from_trends(
    trends: Dict[str, Dict[str, Any]],
    ratios: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Apply rule-based heuristics to identify potential financial warning signs.

    Args:
        trends: Output from analyse_trends().
        ratios: Dict of RatioResult objects from the ratio calculator.

    Returns:
        List of risk finding dicts.
    """
    risks = []

    # --- Revenue decline ---
    rev_trend = trends.get("revenue", {})
    if rev_trend.get("direction") == "decreasing":
        pct = rev_trend.get("pct_change")
        risks.append({
            "category": "Revenue",
            "level": "High" if pct and pct < -10 else "Medium",
            "title": "Declining Revenue",
            "detail": f"Revenue decreased by {abs(pct):.1f}% over the available periods." if pct else "Revenue shows a declining trend.",
            "indicator_values": rev_trend.get("values", []),
            "explanation": "Sustained revenue decline may indicate weakening demand, competitive pressure, or loss of key clients.",
        })

    # --- Profit margin decline ---
    npm_ratio = ratios.get("Net Profit Margin")
    if npm_ratio and npm_ratio.result is not None and npm_ratio.result < 0:
        risks.append({
            "category": "Profitability",
            "level": "High",
            "title": "Negative Net Profit Margin",
            "detail": f"Net Profit Margin is {npm_ratio.result:.1f}%.",
            "indicator_values": [("Net Profit Margin", npm_ratio.result)],
            "explanation": "A negative margin means the company is spending more than it earns.",
        })
    elif npm_ratio and npm_ratio.result is not None and npm_ratio.result < 5:
        risks.append({
            "category": "Profitability",
            "level": "Medium",
            "title": "Low Net Profit Margin",
            "detail": f"Net Profit Margin is {npm_ratio.result:.1f}%, below 5%.",
            "indicator_values": [("Net Profit Margin", npm_ratio.result)],
            "explanation": "Low margins leave little buffer for unexpected costs or economic downturns.",
        })

    # --- Current ratio ---
    cr_ratio = ratios.get("Current Ratio")
    if cr_ratio and cr_ratio.result is not None:
        if cr_ratio.result < 1.0:
            risks.append({
                "category": "Liquidity",
                "level": "High",
                "title": "Current Ratio Below 1.0",
                "detail": f"Current Ratio = {cr_ratio.result:.2f}x (current liabilities exceed current assets).",
                "indicator_values": [("Current Ratio", cr_ratio.result)],
                "explanation": "A current ratio below 1.0 indicates the company may struggle to meet short-term obligations.",
            })
        elif cr_ratio.result < 1.5:
            risks.append({
                "category": "Liquidity",
                "level": "Low",
                "title": "Low Current Ratio",
                "detail": f"Current Ratio = {cr_ratio.result:.2f}x.",
                "indicator_values": [("Current Ratio", cr_ratio.result)],
                "explanation": "A current ratio below 1.5 warrants monitoring, depending on industry norms.",
            })

    # --- High leverage ---
    de_ratio = ratios.get("Debt-to-Equity Ratio")
    if de_ratio and de_ratio.result is not None and de_ratio.result > 2.0:
        risks.append({
            "category": "Leverage",
            "level": "Medium",
            "title": "High Debt-to-Equity Ratio",
            "detail": f"D/E = {de_ratio.result:.2f}x.",
            "indicator_values": [("Debt-to-Equity", de_ratio.result)],
            "explanation": "High leverage increases financial risk, especially during periods of rising interest rates or declining revenues.",
        })

    if not risks:
        risks.append({
            "category": "General",
            "level": "Info",
            "title": "No Major Rule-Based Risks Identified",
            "detail": "The rule-based checks did not flag any significant warning signs based on available data.",
            "indicator_values": [],
            "explanation": "This analysis is limited to available extracted data. A full risk assessment requires a complete set of financial statements.",
        })

    return risks
