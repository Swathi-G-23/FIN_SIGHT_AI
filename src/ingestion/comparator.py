"""
FIN SIGHT AI - Multiple Document & Period Comparator
Compares financial metrics across reporting periods and companies.
Ensures company isolation, computes growth deltas, and preserves provenance.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.ingestion.models import FinancialPeriodRecord, SourceProvenance
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetricComparisonRow:
    metric_name: str
    values_by_period: Dict[str, Optional[float]]
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    unit: str = "millions"
    provenance_by_period: Dict[str, Optional[SourceProvenance]] = field(default_factory=dict)


@dataclass
class MultiPeriodComparisonResult:
    company_name: str
    periods: List[str]
    metric_rows: List[MetricComparisonRow]
    ratio_rows: List[MetricComparisonRow]
    summary_insights: List[str]
    has_comparable_data: bool

    def to_dataframe(self) -> pd.DataFrame:
        """Converts the comparison result into a clean tabular DataFrame."""
        rows = []
        for r in self.metric_rows + self.ratio_rows:
            row_dict = {"Financial Metric": r.metric_name, "Unit": r.unit}
            for p in self.periods:
                val = r.values_by_period.get(p)
                if val is not None:
                    row_dict[p] = f"{val:,.2f}" if r.unit != "%" else f"{val:.2f}%"
                else:
                    row_dict[p] = "—"
            row_dict["Abs Change"] = f"{r.absolute_change:+,.2f}" if r.absolute_change is not None else "—"
            row_dict["% Change"] = f"{r.percentage_change:+.2f}%" if r.percentage_change is not None else "—"
            rows.append(row_dict)
        return pd.DataFrame(rows)


class FinancialComparator:
    """Performs multi-period and multi-document comparison."""

    def __init__(self):
        pass

    def compare_periods(
        self,
        records: List[FinancialPeriodRecord],
        target_company: Optional[str] = None
    ) -> MultiPeriodComparisonResult:
        """
        Compares records for a given company across multiple sorted reporting periods.
        Safeguards: filters out records for other companies.
        """
        if not records:
            return MultiPeriodComparisonResult(
                company_name=target_company or "Unknown",
                periods=[],
                metric_rows=[],
                ratio_rows=[],
                summary_insights=["No financial records available for comparison."],
                has_comparable_data=False,
            )

        # Determine target company
        company = target_company or records[0].company_name
        company_records = [r for r in records if r.company_name.lower() == company.lower()]

        if not company_records:
            return MultiPeriodComparisonResult(
                company_name=company,
                periods=[],
                metric_rows=[],
                ratio_rows=[],
                summary_insights=[f"No records found specifically for {company}."],
                has_comparable_data=False,
            )

        # Sort periods chronologically (or by string)
        company_records.sort(key=lambda r: r.reporting_period)
        periods = [r.reporting_period for r in company_records]

        # Key financial metrics to compare
        tracked_metrics = [
            ("Revenue", "revenue"),
            ("Gross Profit", "gross_profit"),
            ("Operating Income (EBIT)", "operating_income"),
            ("Net Income", "net_income"),
            ("Total Assets", "total_assets"),
            ("Current Assets", "current_assets"),
            ("Total Liabilities", "total_liabilities"),
            ("Current Liabilities", "current_liabilities"),
            ("Total Debt", "total_debt"),
            ("Total Equity", "total_equity"),
            ("Operating Cash Flow", "operating_cash_flow"),
        ]

        metric_rows: List[MetricComparisonRow] = []
        for display_name, attr_name in tracked_metrics:
            vals: Dict[str, Optional[float]] = {}
            provs: Dict[str, Optional[SourceProvenance]] = {}
            for r in company_records:
                val = getattr(r, attr_name, None)
                vals[r.reporting_period] = val
                provs[r.reporting_period] = r.provenance.get(attr_name)

            abs_change = None
            pct_change = None
            valid_vals = [vals[p] for p in periods if vals[p] is not None]
            if len(valid_vals) >= 2:
                first_val, last_val = valid_vals[0], valid_vals[-1]
                abs_change = round(last_val - first_val, 2)
                if first_val != 0:
                    pct_change = round((abs_change / abs(first_val)) * 100, 2)

            metric_rows.append(
                MetricComparisonRow(
                    metric_name=display_name,
                    values_by_period=vals,
                    absolute_change=abs_change,
                    percentage_change=pct_change,
                    unit=company_records[0].unit,
                    provenance_by_period=provs,
                )
            )

        # Ratio comparisons
        tracked_ratios = [
            ("Net Profit Margin (%)", "net_profit_margin"),
            ("Operating Margin (%)", "operating_margin"),
            ("Gross Margin (%)", "gross_margin"),
            ("Current Ratio (x)", "current_ratio"),
            ("Debt-to-Equity (x)", "debt_to_equity"),
        ]

        ratio_rows: List[MetricComparisonRow] = []
        for display_name, ratio_key in tracked_ratios:
            vals = {}
            for r in company_records:
                vals[r.reporting_period] = r.get_ratio(ratio_key)

            abs_change = None
            pct_change = None
            valid_vals = [vals[p] for p in periods if vals[p] is not None]
            if len(valid_vals) >= 2:
                first_val, last_val = valid_vals[0], valid_vals[-1]
                abs_change = round(last_val - first_val, 2)
                if first_val != 0:
                    pct_change = round((abs_change / abs(first_val)) * 100, 2)

            ratio_rows.append(
                MetricComparisonRow(
                    metric_name=display_name,
                    values_by_period=vals,
                    absolute_change=abs_change,
                    percentage_change=pct_change,
                    unit="%",
                )
            )

        # Generate summary insights
        insights = []
        rev_row = next((m for m in metric_rows if m.metric_name == "Revenue"), None)
        if rev_row and rev_row.percentage_change is not None:
            direction = "expanded by" if rev_row.percentage_change >= 0 else "contracted by"
            insights.append(
                f"Revenue {direction} {abs(rev_row.percentage_change)}% over the analyzed periods "
                f"({periods[0]} to {periods[-1]})."
            )

        npm_row = next((r for r in ratio_rows if "Net Profit Margin" in r.metric_name), None)
        if npm_row and npm_row.absolute_change is not None:
            direction = "increased by" if npm_row.absolute_change >= 0 else "decreased by"
            insights.append(
                f"Net Profit Margin {direction} {abs(npm_row.absolute_change):.2f} percentage points."
            )

        cr_row = next((r for r in ratio_rows if "Current Ratio" in r.metric_name), None)
        if cr_row and cr_row.values_by_period.get(periods[-1]) is not None:
            latest_cr = cr_row.values_by_period[periods[-1]]
            status = "healthy short-term liquidity" if latest_cr >= 1.5 else ("adequate" if latest_cr >= 1.0 else "potential liquidity constraint (< 1.0x)")
            insights.append(f"Latest Current Ratio stands at {latest_cr:.2f}x, reflecting {status}.")

        return MultiPeriodComparisonResult(
            company_name=company,
            periods=periods,
            metric_rows=metric_rows,
            ratio_rows=ratio_rows,
            summary_insights=insights,
            has_comparable_data=len(periods) >= 1,
        )
