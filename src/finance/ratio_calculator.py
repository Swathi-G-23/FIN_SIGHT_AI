"""
FIN SIGHT AI - Financial Ratio Calculator
Pure Python calculations for common financial ratios.
All arithmetic is performed here, not by any LLM.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RatioResult:
    """Result of a single ratio calculation."""
    ratio_name: str
    formula: str
    numerator_label: str
    denominator_label: str
    numerator_value: Optional[float]
    denominator_value: Optional[float]
    result: Optional[float]
    unit: str = ""          # e.g. "%" or "x"
    period: str = ""
    is_valid: bool = True
    error_message: str = ""
    interpretation: str = ""


def _safe_divide(
    numerator: Optional[float],
    denominator: Optional[float],
    ratio_name: str,
) -> tuple[Optional[float], str]:
    """
    Safely divide two numbers, returning (result, error_message).
    """
    if numerator is None:
        return None, f"Numerator unavailable for {ratio_name}."
    if denominator is None:
        return None, f"Denominator unavailable for {ratio_name}."
    if denominator == 0:
        return None, f"Denominator is zero for {ratio_name} — division not possible."
    return numerator / denominator, ""


class FinancialRatioCalculator:
    """
    Calculate standard financial ratios from extracted metrics.

    All calculations use Python arithmetic. No LLM is involved.
    """

    # ------------------------------------------------------------------ #
    # Profitability Ratios
    # ------------------------------------------------------------------ #

    def net_profit_margin(
        self,
        net_profit: Optional[float],
        revenue: Optional[float],
        period: str = "",
    ) -> RatioResult:
        result, err = _safe_divide(net_profit, revenue, "Net Profit Margin")
        pct = result * 100 if result is not None else None
        interp = ""
        if pct is not None:
            if pct >= 20:
                interp = "Strong profit margin (≥20%)"
            elif pct >= 10:
                interp = "Healthy profit margin (10–20%)"
            elif pct >= 0:
                interp = "Low profit margin (<10%)"
            else:
                interp = "Negative profit margin — company is loss-making"

        return RatioResult(
            ratio_name="Net Profit Margin",
            formula="Net Profit / Revenue × 100",
            numerator_label="Net Profit",
            denominator_label="Revenue",
            numerator_value=net_profit,
            denominator_value=revenue,
            result=pct,
            unit="%",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    def operating_profit_margin(
        self,
        operating_profit: Optional[float],
        revenue: Optional[float],
        period: str = "",
    ) -> RatioResult:
        result, err = _safe_divide(operating_profit, revenue, "Operating Profit Margin")
        pct = result * 100 if result is not None else None
        interp = ""
        if pct is not None:
            interp = f"Operating margin of {pct:.1f}% {'is healthy' if pct > 10 else 'is low'}."

        return RatioResult(
            ratio_name="Operating Profit Margin",
            formula="Operating Profit / Revenue × 100",
            numerator_label="Operating Profit",
            denominator_label="Revenue",
            numerator_value=operating_profit,
            denominator_value=revenue,
            result=pct,
            unit="%",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    # ------------------------------------------------------------------ #
    # Liquidity Ratios
    # ------------------------------------------------------------------ #

    def current_ratio(
        self,
        current_assets: Optional[float],
        current_liabilities: Optional[float],
        period: str = "",
    ) -> RatioResult:
        result, err = _safe_divide(current_assets, current_liabilities, "Current Ratio")
        interp = ""
        if result is not None:
            if result >= 2:
                interp = "Strong liquidity (≥2.0)"
            elif result >= 1:
                interp = "Adequate liquidity (1.0–2.0)"
            else:
                interp = "Potential liquidity risk — current ratio below 1.0"

        return RatioResult(
            ratio_name="Current Ratio",
            formula="Current Assets / Current Liabilities",
            numerator_label="Current Assets",
            denominator_label="Current Liabilities",
            numerator_value=current_assets,
            denominator_value=current_liabilities,
            result=result,
            unit="x",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    # ------------------------------------------------------------------ #
    # Leverage Ratios
    # ------------------------------------------------------------------ #

    def debt_to_equity(
        self,
        total_debt: Optional[float],
        total_equity: Optional[float],
        period: str = "",
    ) -> RatioResult:
        result, err = _safe_divide(total_debt, total_equity, "Debt-to-Equity")
        interp = ""
        if result is not None:
            if result < 1:
                interp = "Conservative leverage (D/E < 1)"
            elif result < 2:
                interp = "Moderate leverage (D/E 1–2)"
            else:
                interp = "High leverage — significant debt relative to equity"
            if total_equity is not None and total_equity < 0:
                interp = "Negative equity — D/E ratio may be misleading"

        return RatioResult(
            ratio_name="Debt-to-Equity Ratio",
            formula="Total Debt / Total Equity",
            numerator_label="Total Debt",
            denominator_label="Total Equity",
            numerator_value=total_debt,
            denominator_value=total_equity,
            result=result,
            unit="x",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    # ------------------------------------------------------------------ #
    # Growth Ratios
    # ------------------------------------------------------------------ #

    def revenue_growth(
        self,
        current_revenue: Optional[float],
        previous_revenue: Optional[float],
        current_period: str = "",
        previous_period: str = "",
    ) -> RatioResult:
        if current_revenue is None:
            err = "Current revenue unavailable."
            return RatioResult(
                "Revenue Growth", "(Current - Prior) / Prior × 100",
                "Current Revenue", "Prior Revenue",
                None, previous_revenue, None, "%",
                current_period, False, err,
            )
        result, err = _safe_divide(
            (current_revenue - (previous_revenue or 0)),
            previous_revenue,
            "Revenue Growth",
        )
        pct = result * 100 if result is not None else None
        interp = ""
        if pct is not None:
            direction = "grew" if pct >= 0 else "declined"
            interp = f"Revenue {direction} by {abs(pct):.1f}% year-on-year."

        period = f"{previous_period}→{current_period}" if previous_period else current_period

        return RatioResult(
            ratio_name="Revenue Growth",
            formula="(Current Revenue − Prior Revenue) / Prior Revenue × 100",
            numerator_label="Revenue Change",
            denominator_label="Prior Revenue",
            numerator_value=current_revenue,
            denominator_value=previous_revenue,
            result=pct,
            unit="%",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    def net_profit_growth(
        self,
        current_profit: Optional[float],
        previous_profit: Optional[float],
        current_period: str = "",
        previous_period: str = "",
    ) -> RatioResult:
        if current_profit is None:
            err = "Current net profit unavailable."
            return RatioResult(
                "Net Profit Growth", "(Current - Prior) / |Prior| × 100",
                "Current Net Profit", "Prior Net Profit",
                None, previous_profit, None, "%",
                current_period, False, err,
            )

        base = abs(previous_profit) if previous_profit else None
        result, err = _safe_divide(
            (current_profit - (previous_profit or 0)),
            base,
            "Net Profit Growth",
        )
        pct = result * 100 if result is not None else None
        interp = ""
        if pct is not None:
            direction = "grew" if pct >= 0 else "declined"
            interp = f"Net profit {direction} by {abs(pct):.1f}% year-on-year."

        period = f"{previous_period}→{current_period}" if previous_period else current_period

        return RatioResult(
            ratio_name="Net Profit Growth",
            formula="(Current Net Profit − Prior Net Profit) / |Prior Net Profit| × 100",
            numerator_label="Net Profit Change",
            denominator_label="|Prior Net Profit|",
            numerator_value=current_profit,
            denominator_value=previous_profit,
            result=pct,
            unit="%",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    # ------------------------------------------------------------------ #
    # Additional Solvency, Efficiency & Liquidity Ratios
    # ------------------------------------------------------------------ #

    def quick_ratio(
        self,
        current_assets: Optional[float],
        inventory: Optional[float],
        current_liabilities: Optional[float],
        prepaid_expenses: Optional[float] = 0.0,
        period: str = "",
    ) -> RatioResult:
        prepaid = prepaid_expenses or 0.0
        if current_assets is None or inventory is None or current_liabilities is None:
            err = "Required inputs missing for Quick Ratio (Current Assets, Inventory, or Current Liabilities)."
            return RatioResult(
                ratio_name="Quick Ratio",
                formula="(Current Assets − Inventory − Prepaid Expenses) / Current Liabilities",
                numerator_label="Quick Liquid Assets",
                denominator_label="Current Liabilities",
                numerator_value=None,
                denominator_value=current_liabilities,
                result=None,
                unit="x",
                period=period,
                is_valid=False,
                error_message=err,
            )
        quick_assets = current_assets - inventory - prepaid
        res, err = _safe_divide(quick_assets, current_liabilities, "Quick Ratio")
        interp = ""
        if res is not None:
            interp = f"Quick ratio of {res:.2f}x ({'sound liquid buffer' if res >= 1.0 else 'tight instant coverage'})."

        return RatioResult(
            ratio_name="Quick Ratio",
            formula="(Current Assets − Inventory − Prepaid Expenses) / Current Liabilities",
            numerator_label="Quick Assets",
            denominator_label="Current Liabilities",
            numerator_value=quick_assets,
            denominator_value=current_liabilities,
            result=res,
            unit="x",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    def debt_ratio(
        self,
        total_liabilities: Optional[float],
        total_assets: Optional[float],
        period: str = "",
    ) -> RatioResult:
        res, err = _safe_divide(total_liabilities, total_assets, "Debt Ratio")
        interp = f"Liabilities finance {res * 100:.1f}% of total assets." if res is not None else ""
        return RatioResult(
            ratio_name="Debt Ratio",
            formula="Total Liabilities / Total Assets",
            numerator_label="Total Liabilities",
            denominator_label="Total Assets",
            numerator_value=total_liabilities,
            denominator_value=total_assets,
            result=res,
            unit="x",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    def return_on_assets(
        self,
        net_income: Optional[float],
        closing_assets: Optional[float],
        opening_assets: Optional[float] = None,
        period: str = "",
    ) -> RatioResult:
        avg_assets = (opening_assets + closing_assets) / 2.0 if (opening_assets is not None and closing_assets is not None) else closing_assets
        res, err = _safe_divide(net_income, avg_assets, "Return on Assets")
        pct = res * 100 if res is not None else None
        interp = f"ROA of {pct:.2f}% measures asset capital productivity." if pct is not None else ""
        return RatioResult(
            ratio_name="Return on Assets (ROA)",
            formula="(Net Income / Average Total Assets) × 100",
            numerator_label="Net Income",
            denominator_label="Average Total Assets",
            numerator_value=net_income,
            denominator_value=avg_assets,
            result=pct,
            unit="%",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    def return_on_equity(
        self,
        net_income: Optional[float],
        closing_equity: Optional[float],
        opening_equity: Optional[float] = None,
        period: str = "",
    ) -> RatioResult:
        avg_equity = (opening_equity + closing_equity) / 2.0 if (opening_equity is not None and closing_equity is not None) else closing_equity
        res, err = _safe_divide(net_income, avg_equity, "Return on Equity")
        pct = res * 100 if res is not None else None
        interp = f"ROE of {pct:.2f}% measures shareholder return." if pct is not None else ""
        return RatioResult(
            ratio_name="Return on Equity (ROE)",
            formula="(Net Income / Average Shareholders' Equity) × 100",
            numerator_label="Net Income",
            denominator_label="Average Equity",
            numerator_value=net_income,
            denominator_value=avg_equity,
            result=pct,
            unit="%",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    def working_capital(
        self,
        current_assets: Optional[float],
        current_liabilities: Optional[float],
        period: str = "",
    ) -> RatioResult:
        if current_assets is None or current_liabilities is None:
            return RatioResult(
                ratio_name="Working Capital",
                formula="Current Assets − Current Liabilities",
                numerator_label="Current Assets",
                denominator_label="Current Liabilities",
                numerator_value=current_assets,
                denominator_value=current_liabilities,
                result=None,
                unit="currency",
                period=period,
                is_valid=False,
                error_message="Current assets or liabilities unavailable.",
            )
        wc = current_assets - current_liabilities
        return RatioResult(
            ratio_name="Working Capital",
            formula="Current Assets − Current Liabilities",
            numerator_label="Current Assets",
            denominator_label="Current Liabilities",
            numerator_value=current_assets,
            denominator_value=current_liabilities,
            result=wc,
            unit="currency",
            period=period,
            is_valid=True,
            interpretation=f"Working capital of {wc:,.2f}.",
        )

    def operating_cash_flow_ratio(
        self,
        operating_cash_flow: Optional[float],
        current_liabilities: Optional[float],
        period: str = "",
    ) -> RatioResult:
        res, err = _safe_divide(operating_cash_flow, current_liabilities, "Operating Cash Flow Ratio")
        interp = f"Operating cash flow covers {res:.2f}x of short term liabilities." if res is not None else ""
        return RatioResult(
            ratio_name="Operating Cash Flow Ratio",
            formula="Operating Cash Flow / Current Liabilities",
            numerator_label="Operating Cash Flow",
            denominator_label="Current Liabilities",
            numerator_value=operating_cash_flow,
            denominator_value=current_liabilities,
            result=res,
            unit="x",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    def gross_profit_margin(
        self,
        revenue: Optional[float],
        cogs: Optional[float],
        gross_profit: Optional[float] = None,
        period: str = "",
    ) -> RatioResult:
        gp = gross_profit if gross_profit is not None else ((revenue - cogs) if (revenue is not None and cogs is not None) else None)
        res, err = _safe_divide(gp, revenue, "Gross Profit Margin")
        pct = res * 100 if res is not None else None
        interp = f"Gross margin of {pct:.2f}% reflects direct production markup." if pct is not None else ""
        return RatioResult(
            ratio_name="Gross Profit Margin",
            formula="((Revenue − Cost of Goods Sold) / Revenue) × 100",
            numerator_label="Gross Profit",
            denominator_label="Revenue",
            numerator_value=gp,
            denominator_value=revenue,
            result=pct,
            unit="%",
            period=period,
            is_valid=not bool(err),
            error_message=err,
            interpretation=interp,
        )

    # ------------------------------------------------------------------ #
    # Batch calculate all available ratios
    # ------------------------------------------------------------------ #

    def calculate_all(
        self, metrics: Dict[str, Any]
    ) -> Dict[str, RatioResult]:
        """
        Calculate all supported ratios from a metrics summary dict.

        Args:
            metrics: Dict from metrics_summary() — keys are metric_key strings,
                     values are dicts with 'value' and 'period'.

        Returns:
            Dict mapping ratio_name → RatioResult.
        """
        def v(key):
            m = metrics.get(key)
            if isinstance(m, dict):
                return m.get("value")
            if isinstance(m, (int, float)):
                return float(m)
            return None

        def p(key):
            m = metrics.get(key)
            return m.get("period", "") if isinstance(m, dict) else ""

        results: Dict[str, RatioResult] = {}

        r = self.net_profit_margin(v("net_profit"), v("revenue"), p("net_profit"))
        results[r.ratio_name] = r

        r = self.operating_profit_margin(v("operating_profit"), v("revenue"), p("operating_profit"))
        results[r.ratio_name] = r

        r = self.gross_profit_margin(v("revenue"), v("cogs"), v("gross_profit"), p("revenue"))
        results[r.ratio_name] = r

        r = self.current_ratio(v("current_assets"), v("current_liabilities"), p("current_assets"))
        results[r.ratio_name] = r

        r = self.quick_ratio(v("current_assets"), v("inventory"), v("current_liabilities"), v("prepaid_expenses"), p("current_assets"))
        results[r.ratio_name] = r

        r = self.working_capital(v("current_assets"), v("current_liabilities"), p("current_assets"))
        results[r.ratio_name] = r

        r = self.debt_to_equity(v("total_debt"), v("total_equity"), p("total_debt"))
        results[r.ratio_name] = r

        r = self.debt_ratio(v("total_liabilities"), v("total_assets"), p("total_liabilities"))
        results[r.ratio_name] = r

        r = self.return_on_assets(v("net_profit"), v("total_assets"), v("prior_total_assets"), p("net_profit"))
        results[r.ratio_name] = r

        r = self.return_on_equity(v("net_profit"), v("total_equity"), v("prior_total_equity"), p("net_profit"))
        results[r.ratio_name] = r

        r = self.operating_cash_flow_ratio(v("operating_cash_flow") or v("cash_flow"), v("current_liabilities"), p("current_liabilities"))
        results[r.ratio_name] = r

        # Growth: requires 2 periods — placeholder if only 1 available
        revenue_list = metrics.get("_revenue_all", [])
        profit_list = metrics.get("_net_profit_all", [])

        r = self.revenue_growth(v("revenue"), None)
        results[r.ratio_name] = r

        r = self.net_profit_growth(v("net_profit"), None)
        results[r.ratio_name] = r

        return results
