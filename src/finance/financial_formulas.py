"""
FIN SIGHT AI - Centralized Financial Formula Library
Pure Python validated arithmetic for all financial ratios and performance indicators.
All calculations provide explicit mathematical formulas, source input values,
units, division-by-zero handling, and step-by-step explanations.
NEVER uses LLMs for financial arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class FormulaEvaluation:
    """Standardized result of any financial formula evaluation."""
    formula_name: str
    formula_expression: str
    input_values: Dict[str, Optional[float]]
    result: Optional[float]
    unit: str  # "%", "x", "currency"
    is_valid: bool
    error_message: str = ""
    step_by_step: str = ""
    assumptions: str = ""
    period: str = ""
    interpretation: str = ""


def _safe_divide(
    num: Optional[float],
    den: Optional[float],
    formula_name: str,
    den_label: str = "Denominator",
) -> tuple[Optional[float], str]:
    """Safely divide two numbers, returning (result, error_msg)."""
    if num is None:
        return None, f"Numerator value is missing or undefined for {formula_name}."
    if den is None:
        return None, f"{den_label} value is missing or undefined for {formula_name}."
    if den == 0:
        return None, f"{den_label} is zero for {formula_name} — division undefined."
    return num / den, ""


# -------------------------------------------------------------------------- #
# 1. Growth Ratios
# -------------------------------------------------------------------------- #

def calculate_revenue_growth(
    current_revenue: Optional[float],
    previous_revenue: Optional[float],
    period: str = "",
) -> FormulaEvaluation:
    """
    Revenue Growth (%) = ((Current Revenue − Previous Revenue) / Previous Revenue) × 100
    If previous revenue is zero or missing, returns undefined result.
    """
    inputs = {"current_revenue": current_revenue, "previous_revenue": previous_revenue}
    formula_expr = "((Current Revenue − Previous Revenue) / Previous Revenue) × 100"

    if current_revenue is None:
        return FormulaEvaluation(
            formula_name="Revenue Growth",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message="Current revenue unavailable.",
            period=period,
        )

    if previous_revenue is None:
        return FormulaEvaluation(
            formula_name="Revenue Growth",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message="Previous revenue unavailable — baseline required for growth calculation.",
            period=period,
        )

    if previous_revenue == 0:
        return FormulaEvaluation(
            formula_name="Revenue Growth",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message="Previous revenue is zero — percentage growth is mathematically undefined.",
            period=period,
        )

    # Base formula uses previous_revenue
    diff = current_revenue - previous_revenue
    growth = (diff / abs(previous_revenue)) * 100

    step = f"({current_revenue:,.2f} − {previous_revenue:,.2f}) / |{previous_revenue:,.2f}| × 100 = {growth:.2f}%"
    interp = f"Revenue {'increased' if growth >= 0 else 'decreased'} by {abs(growth):.2f}% period-over-period."

    return FormulaEvaluation(
        formula_name="Revenue Growth",
        formula_expression=formula_expr,
        input_values=inputs,
        result=growth,
        unit="%",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


# -------------------------------------------------------------------------- #
# 2. Profitability Ratios
# -------------------------------------------------------------------------- #

def calculate_net_profit_margin(
    net_profit: Optional[float],
    revenue: Optional[float],
    period: str = "",
) -> FormulaEvaluation:
    """
    Net Profit Margin (%) = (Net Profit / Revenue) × 100
    """
    inputs = {"net_profit": net_profit, "revenue": revenue}
    formula_expr = "(Net Profit / Revenue) × 100"

    ratio, err = _safe_divide(net_profit, revenue, "Net Profit Margin", "Revenue")
    if err:
        return FormulaEvaluation(
            formula_name="Net Profit Margin",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message=err,
            period=period,
        )

    pct = ratio * 100
    step = f"({net_profit:,.2f} / {revenue:,.2f}) × 100 = {pct:.2f}%"

    if pct >= 20:
        interp = "Strong net profit margin (≥20%)."
    elif pct >= 10:
        interp = "Healthy net profit margin (10%–20%)."
    elif pct >= 0:
        interp = "Low net profit margin (<10%)."
    else:
        interp = "Negative net margin — company operated at a net loss."

    return FormulaEvaluation(
        formula_name="Net Profit Margin",
        formula_expression=formula_expr,
        input_values=inputs,
        result=pct,
        unit="%",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


def calculate_operating_profit_margin(
    operating_profit: Optional[float],
    revenue: Optional[float],
    period: str = "",
) -> FormulaEvaluation:
    """
    Operating Profit Margin (%) = (Operating Profit / Revenue) × 100
    """
    inputs = {"operating_profit": operating_profit, "revenue": revenue}
    formula_expr = "(Operating Profit / Revenue) × 100"

    ratio, err = _safe_divide(operating_profit, revenue, "Operating Profit Margin", "Revenue")
    if err:
        return FormulaEvaluation(
            formula_name="Operating Profit Margin",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message=err,
            period=period,
        )

    pct = ratio * 100
    step = f"({operating_profit:,.2f} / {revenue:,.2f}) × 100 = {pct:.2f}%"
    interp = f"Operating margin of {pct:.2f}% ({'healthy core profitability' if pct >= 15 else 'tight core margin'})."

    return FormulaEvaluation(
        formula_name="Operating Profit Margin",
        formula_expression=formula_expr,
        input_values=inputs,
        result=pct,
        unit="%",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


def calculate_gross_profit_margin(
    revenue: Optional[float],
    cogs: Optional[float],
    gross_profit: Optional[float] = None,
    period: str = "",
) -> FormulaEvaluation:
    """
    Gross Profit Margin (%) = ((Revenue − Cost of Goods Sold) / Revenue) × 100
    If Gross Profit is provided directly, uses Gross Profit / Revenue × 100.
    """
    formula_expr = "((Revenue − Cost of Goods Sold) / Revenue) × 100"
    if gross_profit is None and revenue is not None and cogs is not None:
        gross_profit = revenue - cogs

    inputs = {"revenue": revenue, "cogs": cogs, "gross_profit": gross_profit}
    ratio, err = _safe_divide(gross_profit, revenue, "Gross Profit Margin", "Revenue")
    if err:
        return FormulaEvaluation(
            formula_name="Gross Profit Margin",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message=err,
            period=period,
        )

    pct = ratio * 100
    step = f"({gross_profit:,.2f} / {revenue:,.2f}) × 100 = {pct:.2f}%"
    interp = f"Gross margin of {pct:.2f}% reflects production and direct cost efficiency."

    return FormulaEvaluation(
        formula_name="Gross Profit Margin",
        formula_expression=formula_expr,
        input_values=inputs,
        result=pct,
        unit="%",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


def calculate_return_on_assets(
    net_income: Optional[float],
    closing_assets: Optional[float],
    opening_assets: Optional[float] = None,
    period: str = "",
) -> FormulaEvaluation:
    """
    ROA (%) = (Net Income / Average Total Assets) × 100
    If opening assets not available, uses closing total assets and labels assumption clearly.
    """
    formula_expr = "(Net Income / Average Total Assets) × 100"
    assumptions = ""

    if opening_assets is not None and closing_assets is not None:
        avg_assets = (opening_assets + closing_assets) / 2.0
        assumptions = "Calculated using average total assets: (Opening Assets + Closing Assets) / 2."
    elif closing_assets is not None:
        avg_assets = closing_assets
        assumptions = "Opening assets balance unavailable; closing total assets used as proxy."
    else:
        avg_assets = None

    inputs = {
        "net_income": net_income,
        "closing_assets": closing_assets,
        "opening_assets": opening_assets,
        "assets_denominator_used": avg_assets,
    }

    ratio, err = _safe_divide(net_income, avg_assets, "Return on Assets", "Total Assets")
    if err:
        return FormulaEvaluation(
            formula_name="Return on Assets (ROA)",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message=err,
            period=period,
            assumptions=assumptions,
        )

    pct = ratio * 100
    step = f"({net_income:,.2f} / {avg_assets:,.2f}) × 100 = {pct:.2f}%"
    interp = f"Return on Assets of {pct:.2f}% measures asset capital productivity."

    return FormulaEvaluation(
        formula_name="Return on Assets (ROA)",
        formula_expression=formula_expr,
        input_values=inputs,
        result=pct,
        unit="%",
        is_valid=True,
        step_by_step=step,
        assumptions=assumptions,
        period=period,
        interpretation=interp,
    )


def calculate_return_on_equity(
    net_income: Optional[float],
    closing_equity: Optional[float],
    opening_equity: Optional[float] = None,
    period: str = "",
) -> FormulaEvaluation:
    """
    ROE (%) = (Net Income / Average Shareholders' Equity) × 100
    If opening equity not available, uses closing total equity with clear disclosure.
    """
    formula_expr = "(Net Income / Average Shareholders' Equity) × 100"
    assumptions = ""

    if opening_equity is not None and closing_equity is not None:
        avg_equity = (opening_equity + closing_equity) / 2.0
        assumptions = "Calculated using average equity: (Opening Equity + Closing Equity) / 2."
    elif closing_equity is not None:
        avg_equity = closing_equity
        assumptions = "Opening equity balance unavailable; closing total equity used as proxy."
    else:
        avg_equity = None

    inputs = {
        "net_income": net_income,
        "closing_equity": closing_equity,
        "opening_equity": opening_equity,
        "equity_denominator_used": avg_equity,
    }

    ratio, err = _safe_divide(net_income, avg_equity, "Return on Equity", "Shareholders' Equity")
    if err:
        return FormulaEvaluation(
            formula_name="Return on Equity (ROE)",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="%",
            is_valid=False,
            error_message=err,
            period=period,
            assumptions=assumptions,
        )

    pct = ratio * 100
    step = f"({net_income:,.2f} / {avg_equity:,.2f}) × 100 = {pct:.2f}%"

    if avg_equity is not None and avg_equity < 0:
        interp = "Negative equity environment — ROE percentage is distorted and not economically meaningful."
    else:
        interp = f"Return on Equity of {pct:.2f}% measures net return generated on shareholders' capital."

    return FormulaEvaluation(
        formula_name="Return on Equity (ROE)",
        formula_expression=formula_expr,
        input_values=inputs,
        result=pct,
        unit="%",
        is_valid=True,
        step_by_step=step,
        assumptions=assumptions,
        period=period,
        interpretation=interp,
    )


# -------------------------------------------------------------------------- #
# 3. Liquidity & Working Capital Ratios
# -------------------------------------------------------------------------- #

def calculate_current_ratio(
    current_assets: Optional[float],
    current_liabilities: Optional[float],
    period: str = "",
) -> FormulaEvaluation:
    """
    Current Ratio = Current Assets / Current Liabilities
    """
    inputs = {"current_assets": current_assets, "current_liabilities": current_liabilities}
    formula_expr = "Current Assets / Current Liabilities"

    ratio, err = _safe_divide(current_assets, current_liabilities, "Current Ratio", "Current Liabilities")
    if err:
        return FormulaEvaluation(
            formula_name="Current Ratio",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="x",
            is_valid=False,
            error_message=err,
            period=period,
        )

    step = f"{current_assets:,.2f} / {current_liabilities:,.2f} = {ratio:.2f}x"
    if ratio >= 2.0:
        interp = "Strong short-term liquidity buffer (≥2.0x)."
    elif ratio >= 1.0:
        interp = "Adequate short-term liquidity coverage (1.0x–2.0x)."
    else:
        interp = "Liquidity deficit risk — current assets insufficient to cover short-term liabilities (<1.0x)."

    return FormulaEvaluation(
        formula_name="Current Ratio",
        formula_expression=formula_expr,
        input_values=inputs,
        result=ratio,
        unit="x",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


def calculate_quick_ratio(
    current_assets: Optional[float],
    inventory: Optional[float],
    current_liabilities: Optional[float],
    prepaid_expenses: Optional[float] = 0.0,
    period: str = "",
) -> FormulaEvaluation:
    """
    Quick Ratio = (Current Assets − Inventory − Prepaid Expenses) / Current Liabilities
    """
    formula_expr = "(Current Assets − Inventory − Prepaid Expenses) / Current Liabilities"
    prepaid = prepaid_expenses or 0.0
    assumptions = "Prepaid expenses taken as 0.0 if not explicitly disclosed." if prepaid_expenses in (None, 0.0) else ""

    quick_assets = None
    if current_assets is not None and inventory is not None:
        quick_assets = current_assets - inventory - prepaid
    elif current_assets is not None and inventory is None:
        # Cannot calculate quick ratio without inventory
        quick_assets = None

    inputs = {
        "current_assets": current_assets,
        "inventory": inventory,
        "prepaid_expenses": prepaid,
        "quick_assets_numerator": quick_assets,
        "current_liabilities": current_liabilities,
    }

    if inventory is None:
        return FormulaEvaluation(
            formula_name="Quick Ratio",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="x",
            is_valid=False,
            error_message="Inventory figure unavailable — required to isolate quick liquid assets.",
            assumptions=assumptions,
            period=period,
        )

    ratio, err = _safe_divide(quick_assets, current_liabilities, "Quick Ratio", "Current Liabilities")
    if err:
        return FormulaEvaluation(
            formula_name="Quick Ratio",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="x",
            is_valid=False,
            error_message=err,
            assumptions=assumptions,
            period=period,
        )

    step = f"({current_assets:,.2f} − {inventory:,.2f} − {prepaid:,.2f}) / {current_liabilities:,.2f} = {ratio:.2f}x"
    interp = f"Quick ratio of {ratio:.2f}x ({'satisfactory liquid buffer' if ratio >= 1.0 else 'tight instant liquidity below 1.0x'})."

    return FormulaEvaluation(
        formula_name="Quick Ratio",
        formula_expression=formula_expr,
        input_values=inputs,
        result=ratio,
        unit="x",
        is_valid=True,
        step_by_step=step,
        assumptions=assumptions,
        period=period,
        interpretation=interp,
    )


def calculate_working_capital(
    current_assets: Optional[float],
    current_liabilities: Optional[float],
    period: str = "",
) -> FormulaEvaluation:
    """
    Working Capital = Current Assets − Current Liabilities
    """
    inputs = {"current_assets": current_assets, "current_liabilities": current_liabilities}
    formula_expr = "Current Assets − Current Liabilities"

    if current_assets is None or current_liabilities is None:
        missing = "Current Assets" if current_assets is None else "Current Liabilities"
        return FormulaEvaluation(
            formula_name="Working Capital",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="currency",
            is_valid=False,
            error_message=f"{missing} is unavailable for working capital calculation.",
            period=period,
        )

    wc = current_assets - current_liabilities
    step = f"{current_assets:,.2f} − {current_liabilities:,.2f} = {wc:,.2f}"
    interp = f"Net working capital is {'positive' if wc >= 0 else 'negative'} ({wc:,.2f})."

    return FormulaEvaluation(
        formula_name="Working Capital",
        formula_expression=formula_expr,
        input_values=inputs,
        result=wc,
        unit="currency",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


# -------------------------------------------------------------------------- #
# 4. Solvency & Leverage Ratios
# -------------------------------------------------------------------------- #

def calculate_debt_to_equity(
    total_debt: Optional[float],
    total_equity: Optional[float],
    period: str = "",
    debt_definition: str = "Interest-bearing short-term & long-term borrowings",
) -> FormulaEvaluation:
    """
    Debt-to-Equity = Total Debt / Total Equity
    Explicitly documents debt definition used (does not substitute liabilities without disclosure).
    """
    inputs = {"total_debt": total_debt, "total_equity": total_equity}
    formula_expr = "Total Debt / Total Equity"
    assumptions = f"Debt defined as: {debt_definition}."

    ratio, err = _safe_divide(total_debt, total_equity, "Debt-to-Equity", "Total Equity")
    if err:
        return FormulaEvaluation(
            formula_name="Debt-to-Equity Ratio",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="x",
            is_valid=False,
            error_message=err,
            assumptions=assumptions,
            period=period,
        )

    step = f"{total_debt:,.2f} / {total_equity:,.2f} = {ratio:.2f}x"
    if total_equity is not None and total_equity < 0:
        interp = "Negative equity — Debt-to-Equity ratio is negative and signals severe capital distress."
    elif ratio < 1.0:
        interp = "Conservative financial leverage (D/E < 1.0x)."
    elif ratio <= 2.0:
        interp = "Moderate financial leverage (D/E 1.0x–2.0x)."
    else:
        interp = "Elevated financial leverage (D/E > 2.0x)."

    return FormulaEvaluation(
        formula_name="Debt-to-Equity Ratio",
        formula_expression=formula_expr,
        input_values=inputs,
        result=ratio,
        unit="x",
        is_valid=True,
        step_by_step=step,
        assumptions=assumptions,
        period=period,
        interpretation=interp,
    )


def calculate_debt_ratio(
    total_liabilities: Optional[float],
    total_assets: Optional[float],
    period: str = "",
) -> FormulaEvaluation:
    """
    Debt Ratio = Total Liabilities / Total Assets
    """
    inputs = {"total_liabilities": total_liabilities, "total_assets": total_assets}
    formula_expr = "Total Liabilities / Total Assets"

    ratio, err = _safe_divide(total_liabilities, total_assets, "Debt Ratio", "Total Assets")
    if err:
        return FormulaEvaluation(
            formula_name="Debt Ratio",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="x",
            is_valid=False,
            error_message=err,
            period=period,
        )

    step = f"{total_liabilities:,.2f} / {total_assets:,.2f} = {ratio:.2f}x ({ratio * 100:.1f}%)"
    interp = f"Total liabilities finance {ratio * 100:.1f}% of total assets."

    return FormulaEvaluation(
        formula_name="Debt Ratio",
        formula_expression=formula_expr,
        input_values=inputs,
        result=ratio,
        unit="x",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


def calculate_operating_cash_flow_ratio(
    operating_cash_flow: Optional[float],
    current_liabilities: Optional[float],
    period: str = "",
) -> FormulaEvaluation:
    """
    Operating Cash Flow Ratio = Operating Cash Flow / Current Liabilities
    """
    inputs = {"operating_cash_flow": operating_cash_flow, "current_liabilities": current_liabilities}
    formula_expr = "Operating Cash Flow / Current Liabilities"

    ratio, err = _safe_divide(
        operating_cash_flow, current_liabilities, "Operating Cash Flow Ratio", "Current Liabilities"
    )
    if err:
        return FormulaEvaluation(
            formula_name="Operating Cash Flow Ratio",
            formula_expression=formula_expr,
            input_values=inputs,
            result=None,
            unit="x",
            is_valid=False,
            error_message=err,
            period=period,
        )

    step = f"{operating_cash_flow:,.2f} / {current_liabilities:,.2f} = {ratio:.2f}x"
    interp = f"Cash flow covers {ratio:.2f}x of short-term obligations from operating operations."

    return FormulaEvaluation(
        formula_name="Operating Cash Flow Ratio",
        formula_expression=formula_expr,
        input_values=inputs,
        result=ratio,
        unit="x",
        is_valid=True,
        step_by_step=step,
        period=period,
        interpretation=interp,
    )


# -------------------------------------------------------------------------- #
# Master Catalog & Batch Evaluator
# -------------------------------------------------------------------------- #

ALL_FORMULA_NAMES = [
    "Revenue Growth",
    "Net Profit Margin",
    "Operating Profit Margin",
    "Gross Profit Margin",
    "Current Ratio",
    "Quick Ratio",
    "Debt-to-Equity Ratio",
    "Debt Ratio",
    "Return on Assets (ROA)",
    "Return on Equity (ROE)",
    "Working Capital",
    "Operating Cash Flow Ratio",
]


def evaluate_all_formulas(metrics_dict: Dict[str, Any], period: str = "") -> Dict[str, FormulaEvaluation]:
    """
    Evaluate all 12 standard financial formulas from a key-value dictionary of metrics.
    """
    def _val(key: str) -> Optional[float]:
        val = metrics_dict.get(key)
        if isinstance(val, dict):
            return val.get("value")
        if isinstance(val, (int, float)):
            return float(val)
        return None

    results: Dict[str, FormulaEvaluation] = {}

    # Extract standard metrics
    rev = _val("revenue")
    prior_rev = _val("prior_revenue") or _val("previous_revenue")
    net_p = _val("net_profit") or _val("net_income")
    op_p = _val("operating_profit")
    cogs = _val("cogs") or _val("cost_of_goods_sold")
    gross_p = _val("gross_profit")
    ca = _val("current_assets")
    cl = _val("current_liabilities")
    inv = _val("inventory")
    prepaid = _val("prepaid_expenses")
    debt = _val("total_debt")
    equity = _val("total_equity")
    prior_equity = _val("prior_total_equity")
    assets = _val("total_assets")
    prior_assets = _val("prior_total_assets")
    liab = _val("total_liabilities")
    ocf = _val("operating_cash_flow") or _val("cash_flow")

    results["Revenue Growth"] = calculate_revenue_growth(rev, prior_rev, period)
    results["Net Profit Margin"] = calculate_net_profit_margin(net_p, rev, period)
    results["Operating Profit Margin"] = calculate_operating_profit_margin(op_p, rev, period)
    results["Gross Profit Margin"] = calculate_gross_profit_margin(rev, cogs, gross_p, period)
    results["Current Ratio"] = calculate_current_ratio(ca, cl, period)
    results["Quick Ratio"] = calculate_quick_ratio(ca, inv, cl, prepaid, period)
    results["Debt-to-Equity Ratio"] = calculate_debt_to_equity(debt, equity, period)
    results["Debt Ratio"] = calculate_debt_ratio(liab, assets, period)
    results["Return on Assets (ROA)"] = calculate_return_on_assets(net_p, assets, prior_assets, period)
    results["Return on Equity (ROE)"] = calculate_return_on_equity(net_p, equity, prior_equity, period)
    results["Working Capital"] = calculate_working_capital(ca, cl, period)
    results["Operating Cash Flow Ratio"] = calculate_operating_cash_flow_ratio(ocf, cl, period)

    return results
