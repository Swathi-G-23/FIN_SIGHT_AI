"""
FIN SIGHT AI - Manual Financial Data Entry
Validates, checks arithmetic consistency, and converts manual user entries
into standardized FinancialPeriodRecord objects with complete provenance.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.ingestion.models import FinancialPeriodRecord, InputSourceType, SourceProvenance
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ManualEntryValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    record: Optional[FinancialPeriodRecord] = None


class ManualDataEntryManager:
    """Handles and validates manual financial input from the user interface."""

    def __init__(self):
        pass

    def create_record(
        self,
        company_name: str,
        reporting_period: str,
        currency: str = "USD",
        unit: str = "millions",
        # Income Statement
        revenue: Optional[float] = None,
        cost_of_goods_sold: Optional[float] = None,
        gross_profit: Optional[float] = None,
        operating_expenses: Optional[float] = None,
        operating_income: Optional[float] = None,
        net_income: Optional[float] = None,
        tax_expense: Optional[float] = None,
        interest_expense: Optional[float] = None,
        # Balance Sheet
        total_assets: Optional[float] = None,
        current_assets: Optional[float] = None,
        cash_and_equivalents: Optional[float] = None,
        total_liabilities: Optional[float] = None,
        current_liabilities: Optional[float] = None,
        total_debt: Optional[float] = None,
        total_equity: Optional[float] = None,
        # Cash Flow
        operating_cash_flow: Optional[float] = None,
        investing_cash_flow: Optional[float] = None,
        financing_cash_flow: Optional[float] = None,
    ) -> ManualEntryValidationResult:
        """Validates numerical ranges and balance sheet relationships."""
        errors: List[str] = []
        warnings: List[str] = []

        if not company_name or not company_name.strip():
            errors.append("Company name is required.")
        if not reporting_period or not reporting_period.strip():
            errors.append("Reporting period is required (e.g. FY2023, Q3 2023).")

        # Range checks
        if revenue is not None and revenue < 0:
            warnings.append("Revenue is entered as negative. Please verify if this represents a net contra-revenue.")

        if total_assets is not None and total_assets < 0:
            errors.append("Total Assets cannot be negative.")

        if current_assets is not None and total_assets is not None:
            if current_assets > total_assets:
                errors.append(f"Current Assets ({current_assets}) cannot exceed Total Assets ({total_assets}).")

        if current_liabilities is not None and total_liabilities is not None:
            if current_liabilities > total_liabilities:
                errors.append(f"Current Liabilities ({current_liabilities}) cannot exceed Total Liabilities ({total_liabilities}).")

        # Balance sheet identity check: Assets ~= Liabilities + Equity
        if total_assets is not None and total_liabilities is not None and total_equity is not None:
            calc_assets = total_liabilities + total_equity
            diff = abs(total_assets - calc_assets)
            if diff > 1.0: # Allow 1.0 margin for rounding in millions
                warnings.append(
                    f"Balance sheet identity variance: Total Assets ({total_assets}) != "
                    f"Liabilities ({total_liabilities}) + Equity ({total_equity}). Difference: {diff:.2f}"
                )

        # Gross profit check: Revenue - COGS
        if revenue is not None and cost_of_goods_sold is not None and gross_profit is not None:
            expected_gp = revenue - cost_of_goods_sold
            if abs(gross_profit - expected_gp) > 1.0:
                warnings.append(
                    f"Gross Profit ({gross_profit}) differs from Revenue ({revenue}) - COGS ({cost_of_goods_sold}) = {expected_gp:.2f}"
                )

        if errors:
            return ManualEntryValidationResult(is_valid=False, errors=errors, warnings=warnings, record=None)

        # Construct clean record
        source_label = f"Manual Entry - {company_name.strip()} ({reporting_period.strip()})"
        rec = FinancialPeriodRecord(
            company_name=company_name.strip(),
            reporting_period=reporting_period.strip(),
            currency=currency,
            unit=unit,
            revenue=revenue,
            cost_of_goods_sold=cost_of_goods_sold,
            gross_profit=gross_profit,
            operating_expenses=operating_expenses,
            operating_income=operating_income,
            net_income=net_income,
            tax_expense=tax_expense,
            interest_expense=interest_expense,
            total_assets=total_assets,
            current_assets=current_assets,
            cash_and_equivalents=cash_and_equivalents,
            total_liabilities=total_liabilities,
            current_liabilities=current_liabilities,
            total_debt=total_debt,
            total_equity=total_equity,
            operating_cash_flow=operating_cash_flow,
            investing_cash_flow=investing_cash_flow,
            financing_cash_flow=financing_cash_flow,
        )

        # Build provenance for each supplied field
        fields_dict = rec.to_dict()
        for k, v in fields_dict.items():
            if k not in ["company_name", "reporting_period", "currency", "unit"] and v is not None:
                rec.provenance[k] = SourceProvenance(
                    source_type=InputSourceType.MANUAL,
                    filename=source_label,
                    confidence=1.0,
                    notes=f"Manually entered by analyst: {k} = {v} {unit} {currency}",
                )

        # Generate searchable narrative for RAG
        lines = [
            f"=== FINANCIAL STATEMENT: {company_name.strip()} | {reporting_period.strip()} ===",
            f"Company: {company_name.strip()} | Period: {reporting_period.strip()} | Currency: {currency} | Unit: {unit}",
        ]
        if revenue is not None: lines.append(f"Revenue: {revenue} {unit}")
        if cost_of_goods_sold is not None: lines.append(f"Cost of Goods Sold (COGS): {cost_of_goods_sold} {unit}")
        if gross_profit is not None: lines.append(f"Gross Profit: {gross_profit} {unit}")
        if operating_income is not None: lines.append(f"Operating Income (EBIT): {operating_income} {unit}")
        if net_income is not None: lines.append(f"Net Income: {net_income} {unit}")
        if total_assets is not None: lines.append(f"Total Assets: {total_assets} {unit}")
        if current_assets is not None: lines.append(f"Current Assets: {current_assets} {unit}")
        if total_liabilities is not None: lines.append(f"Total Liabilities: {total_liabilities} {unit}")
        if current_liabilities is not None: lines.append(f"Current Liabilities: {current_liabilities} {unit}")
        if total_debt is not None: lines.append(f"Total Debt: {total_debt} {unit}")
        if total_equity is not None: lines.append(f"Total Equity: {total_equity} {unit}")
        if operating_cash_flow is not None: lines.append(f"Operating Cash Flow: {operating_cash_flow} {unit}")

        rec.raw_text = "\n".join(lines)

        return ManualEntryValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            record=rec,
        )

    def create_record_from_form(self, form_dict: Dict[str, Any]) -> Tuple[Optional[FinancialPeriodRecord], ManualEntryValidationResult]:
        """Convenience method accepting raw form dictionary from UI."""
        res = self.create_record(
            company_name=form_dict.get("company_name", ""),
            reporting_period=form_dict.get("reporting_period", ""),
            currency=form_dict.get("currency", "USD"),
            unit=form_dict.get("scale", form_dict.get("unit", "millions")),
            revenue=form_dict.get("revenue"),
            cost_of_goods_sold=form_dict.get("cost_of_goods_sold"),
            gross_profit=form_dict.get("gross_profit"),
            operating_expenses=form_dict.get("operating_expenses"),
            operating_income=form_dict.get("operating_income"),
            net_income=form_dict.get("net_income"),
            total_assets=form_dict.get("total_assets"),
            current_assets=form_dict.get("current_assets"),
            cash_and_equivalents=form_dict.get("cash_and_equivalents"),
            total_liabilities=form_dict.get("total_liabilities"),
            current_liabilities=form_dict.get("current_liabilities"),
            total_debt=form_dict.get("total_debt"),
            total_equity=form_dict.get("total_equity"),
            operating_cash_flow=form_dict.get("operating_cash_flow"),
        )
        return res.record, res
