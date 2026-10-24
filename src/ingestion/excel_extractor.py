"""
FIN SIGHT AI - Excel Financial Extractor
Reads .xlsx and .xls financial models and statements.
Extracts sheet structures, cell coordinates, and maps financial line items.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from src.ingestion.models import FinancialPeriodRecord, InputSourceType, SourceProvenance
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ExcelSheetData:
    sheet_name: str
    row_count: int
    column_count: int
    columns: List[str]
    preview_df: pd.DataFrame
    raw_df: pd.DataFrame


@dataclass
class ExcelExtractionResult:
    filename: str
    sheets: Dict[str, ExcelSheetData]
    selected_sheet: str
    text_content: str
    financial_records: List[FinancialPeriodRecord] = field(default_factory=list)
    detected_periods: List[str] = field(default_factory=list)


# Fuzzy keywords to map Excel row labels to standard financial fields
FINANCIAL_LABEL_PATTERNS = {
    "revenue": ["revenue", "total revenue", "turnover", "sales", "net sales"],
    "cost_of_goods_sold": ["cost of goods sold", "cogs", "cost of revenue", "cost of sales"],
    "gross_profit": ["gross profit", "gross margin", "gross income"],
    "operating_expenses": ["operating expenses", "total operating expenses", "opex", "sga", "sg&a"],
    "operating_income": ["operating income", "operating profit", "ebit", "operating earnings"],
    "net_income": ["net income", "net profit", "profit after tax", "pat", "net earnings"],
    "total_assets": ["total assets", "assets total"],
    "current_assets": ["current assets", "total current assets"],
    "cash_and_equivalents": ["cash and cash equivalents", "cash & cash equivalents", "cash"],
    "total_liabilities": ["total liabilities", "liabilities total"],
    "current_liabilities": ["current liabilities", "total current liabilities"],
    "total_debt": ["total debt", "total borrowings", "short and long term debt"],
    "total_equity": ["total equity", "stockholders equity", "shareholders equity", "total stockholders equity"],
    "operating_cash_flow": ["operating cash flow", "cash from operations", "cash flow from operating activities"],
}


class ExcelExtractor:
    """Extracts financial data, metadata, and tables from Excel workbooks."""

    def __init__(self):
        pass

    def inspect_sheets(self, file_path: str | Path) -> List[str]:
        """Returns list of sheet names in the Excel file."""
        xl = pd.ExcelFile(file_path)
        return xl.sheet_names

    def extract(
        self,
        file_path: str | Path,
        sheet_name: Optional[str] = None,
        company_name: str = "Unknown Company"
    ) -> ExcelExtractionResult:
        """
        Extracts tabular data and financial statements from an Excel file.
        If sheet_name is None, defaults to the first sheet or tries to auto-detect a financial sheet.
        """
        path = Path(file_path)
        filename = path.name
        xl = pd.ExcelFile(path)
        all_sheet_names = xl.sheet_names

        sheets_data: Dict[str, ExcelSheetData] = {}
        for s in all_sheet_names:
            try:
                df = xl.parse(s)
                # Fill or clean blank column names
                cleaned_cols = [str(c).strip() if not str(c).startswith("Unnamed:") else f"Col_{idx}" 
                                for idx, c in enumerate(df.columns)]
                df.columns = cleaned_cols
                sheets_data[s] = ExcelSheetData(
                    sheet_name=s,
                    row_count=len(df),
                    column_count=len(df.columns),
                    columns=cleaned_cols,
                    preview_df=df.head(10),
                    raw_df=df,
                )
            except Exception as e:
                logger.warning(f"Could not parse sheet {s}: {e}")

        # Choose sheet
        selected_sheet = sheet_name or all_sheet_names[0]
        if selected_sheet not in sheets_data and all_sheet_names:
            selected_sheet = all_sheet_names[0]

        active_sheet_data = sheets_data.get(selected_sheet)
        if not active_sheet_data:
            return ExcelExtractionResult(
                filename=filename,
                sheets=sheets_data,
                selected_sheet=selected_sheet,
                text_content="",
                financial_records=[],
            )

        df = active_sheet_data.raw_df

        # Generate text representation for RAG
        text_lines = [f"=== EXCEL REPORT: {filename} | SHEET: {selected_sheet} ==="]
        for row_idx, row in df.iterrows():
            row_items = []
            for col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).strip() != "":
                    row_items.append(f"{col}: {val}")
            if row_items:
                text_lines.append(f"[Sheet: {selected_sheet}, Row {row_idx + 1}] " + " | ".join(row_items))

        text_content = "\n".join(text_lines)

        # Attempt to map rows to structured financial record
        records = self._parse_financial_table(
            df=df,
            filename=filename,
            sheet_name=selected_sheet,
            company_name=company_name
        )

        detected_periods = [r.reporting_period for r in records]

        return ExcelExtractionResult(
            filename=filename,
            sheets=sheets_data,
            selected_sheet=selected_sheet,
            text_content=text_content,
            financial_records=records,
            detected_periods=detected_periods,
        )

    def _parse_financial_table(
        self,
        df: pd.DataFrame,
        filename: str,
        sheet_name: str,
        company_name: str
    ) -> List[FinancialPeriodRecord]:
        """
        Parses financial line items where the first column contains line labels,
        and subsequent columns represent periods (e.g., FY2023, FY2022).
        """
        if df.empty or len(df.columns) < 2:
            return []

        # Find the label column (typically col 0 or first string-heavy column)
        label_col = df.columns[0]
        period_cols = [c for c in df.columns[1:] if not str(c).startswith("Col_")]
        if not period_cols:
            period_cols = list(df.columns[1:])

        records_by_period: Dict[str, FinancialPeriodRecord] = {}
        for p in period_cols:
            p_str = str(p).strip()
            records_by_period[p_str] = FinancialPeriodRecord(
                company_name=company_name,
                reporting_period=p_str,
            )

        # Scan rows
        for row_idx, row in df.iterrows():
            label_val = str(row[label_col]).strip().lower()
            if not label_val or label_val == "nan":
                continue

            matched_field = None
            for f_name, patterns in FINANCIAL_LABEL_PATTERNS.items():
                if any(p in label_val for p in patterns):
                    matched_field = f_name
                    break

            if matched_field:
                for p_col in period_cols:
                    p_str = str(p_col).strip()
                    val = row[p_col]
                    clean_val = self._clean_numeric_value(val)
                    if clean_val is not None:
                        rec = records_by_period[p_str]
                        setattr(rec, matched_field, clean_val)
                        rec.provenance[matched_field] = SourceProvenance(
                            source_type=InputSourceType.EXCEL,
                            filename=filename,
                            sheet_name=sheet_name,
                            row_index=row_idx + 1,
                            column_name=str(p_col),
                            confidence=0.98,
                            notes=f"Extracted from Excel cell [{p_col}, Row {row_idx + 1}]",
                        )

        # Only return records that have at least one valid key metric
        valid_records = []
        for rec in records_by_period.values():
            if rec.revenue is not None or rec.net_income is not None or rec.total_assets is not None:
                valid_records.append(rec)

        return valid_records

    @staticmethod
    def _clean_numeric_value(val: Any) -> Optional[float]:
        """Converts Excel cell values (including strings with $, commas, brackets) to float."""
        if pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip()
        # Handle negative in parentheses e.g. (150.0) -> -150.0
        is_negative = False
        if val_str.startswith("(") and val_str.endswith(")"):
            is_negative = True
            val_str = val_str[1:-1].strip()
        elif val_str.startswith("-"):
            is_negative = True
            val_str = val_str[1:].strip()

        # Remove currency symbols and formatting commas
        for char in ["$", "€", "£", "¥", ",", " "]:
            val_str = val_str.replace(char, "")

        try:
            num = float(val_str)
            return -num if is_negative else num
        except ValueError:
            return None
