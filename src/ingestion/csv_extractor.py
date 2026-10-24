"""
FIN SIGHT AI - CSV Financial Dataset Extractor
Ingests CSV financial datasets, validates schema, supports column mapping,
and extracts structured financial records with row provenance.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from src.ingestion.models import FinancialPeriodRecord, InputSourceType, SourceProvenance
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CSVValidationSummary:
    total_rows: int
    total_columns: int
    missing_values_count: int
    duplicate_rows_count: int
    is_valid: bool
    warnings: List[str] = field(default_factory=list)


@dataclass
class CSVExtractionResult:
    filename: str
    preview_df: pd.DataFrame
    raw_df: pd.DataFrame
    validation: CSVValidationSummary
    column_mapping: Dict[str, str]
    financial_records: List[FinancialPeriodRecord] = field(default_factory=list)
    text_content: str = ""


# Standard target fields
CANONICAL_FIELDS = [
    "company_name",
    "reporting_period",
    "revenue",
    "cost_of_goods_sold",
    "gross_profit",
    "operating_expenses",
    "operating_income",
    "net_income",
    "total_assets",
    "current_assets",
    "total_liabilities",
    "current_liabilities",
    "total_debt",
    "total_equity",
    "operating_cash_flow",
]


class CSVExtractor:
    """Extracts, maps, and validates CSV financial data."""

    def __init__(self):
        pass

    def extract(
        self,
        file_path: str | Path,
        column_mapping: Optional[Dict[str, str]] = None,
        default_company: str = "Company",
    ) -> CSVExtractionResult:
        """
        Loads CSV, runs quality validation, applies column mappings,
        and constructs FinancialPeriodRecord objects.
        """
        path = Path(file_path)
        filename = path.name

        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin1")

        # Validation
        validation = self.validate_dataframe(df)

        # Auto-map columns if not provided
        mapping = column_mapping or self.auto_detect_columns(df)

        # Build financial records
        records = self._build_records(df, mapping, filename, default_company)

        # Build text representation for RAG search
        text_lines = [f"=== CSV FINANCIAL DATASET: {filename} ==="]
        for row_idx, row in df.iterrows():
            row_items = []
            for col in df.columns:
                val = row[col]
                if pd.notna(val):
                    row_items.append(f"{col}: {val}")
            text_lines.append(f"[CSV: {filename}, Row {row_idx + 1}] " + " | ".join(row_items))

        text_content = "\n".join(text_lines)

        return CSVExtractionResult(
            filename=filename,
            preview_df=df.head(10),
            raw_df=df,
            validation=validation,
            column_mapping=mapping,
            financial_records=records,
            text_content=text_content,
        )

    def validate_dataframe(self, df: pd.DataFrame) -> CSVValidationSummary:
        """Checks for missing data, duplicates, and anomalies."""
        total_rows = len(df)
        total_columns = len(df.columns)
        missing_count = int(df.isna().sum().sum())
        duplicate_count = int(df.duplicated().sum())
        warnings = []

        if total_rows == 0:
            warnings.append("Dataset is empty.")
        if missing_count > 0:
            warnings.append(f"Found {missing_count} missing cell values across {total_columns} columns.")
        if duplicate_count > 0:
            warnings.append(f"Found {duplicate_count} duplicate rows in dataset.")

        return CSVValidationSummary(
            total_rows=total_rows,
            total_columns=total_columns,
            missing_values_count=missing_count,
            duplicate_rows_count=duplicate_count,
            is_valid=(total_rows > 0 and total_columns > 1),
            warnings=warnings,
        )

    def auto_detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Guesses mapping from df columns to canonical financial fields."""
        mapping: Dict[str, str] = {}
        cols_lower = {col: str(col).lower().strip().replace(" ", "_").replace("-", "_") for col in df.columns}

        keywords = {
            "company_name": ["company", "ticker", "firm", "issuer", "entity"],
            "reporting_period": ["year", "period", "fiscal_year", "date", "quarter", "fy"],
            "revenue": ["revenue", "sales", "total_revenue", "turnover"],
            "gross_profit": ["gross_profit", "gross_margin"],
            "operating_income": ["operating_income", "ebit", "operating_profit"],
            "net_income": ["net_income", "net_profit", "profit", "earnings"],
            "total_assets": ["total_assets", "assets"],
            "current_assets": ["current_assets"],
            "total_liabilities": ["total_liabilities", "liabilities"],
            "current_liabilities": ["current_liabilities"],
            "total_debt": ["total_debt", "debt", "borrowings"],
            "total_equity": ["total_equity", "equity", "shareholders_equity"],
            "operating_cash_flow": ["operating_cash_flow", "cash_flow", "ocf"],
        }

        for canonical, terms in keywords.items():
            for orig_col, clean_col in cols_lower.items():
                if any(t == clean_col or t in clean_col for t in terms):
                    if orig_col not in mapping.values():
                        mapping[canonical] = orig_col
                        break

        return mapping

    def _build_records(
        self,
        df: pd.DataFrame,
        mapping: Dict[str, str],
        filename: str,
        default_company: str,
    ) -> List[FinancialPeriodRecord]:
        """Constructs FinancialPeriodRecord list from mapped dataframe rows."""
        records = []
        company_col = mapping.get("company_name")
        period_col = mapping.get("reporting_period")

        for row_idx, row in df.iterrows():
            company = str(row[company_col]).strip() if company_col and company_col in row and pd.notna(row[company_col]) else default_company
            period = str(row[period_col]).strip() if period_col and period_col in row and pd.notna(row[period_col]) else f"Period_{row_idx + 1}"

            rec = FinancialPeriodRecord(
                company_name=company,
                reporting_period=period,
            )

            for target_field in CANONICAL_FIELDS:
                if target_field in ["company_name", "reporting_period"]:
                    continue
                source_col = mapping.get(target_field)
                if source_col and source_col in row:
                    val = row[source_col]
                    num_val = self._parse_numeric(val)
                    if num_val is not None:
                        setattr(rec, target_field, num_val)
                        rec.provenance[target_field] = SourceProvenance(
                            source_type=InputSourceType.CSV,
                            filename=filename,
                            row_index=row_idx + 1,
                            column_name=source_col,
                            confidence=1.0,
                            notes=f"CSV cell [{source_col}, Row {row_idx + 1}]",
                        )

            if rec.revenue is not None or rec.net_income is not None or rec.total_assets is not None:
                records.append(rec)

        return records

    @staticmethod
    def _parse_numeric(val: Any) -> Optional[float]:
        """Safely parses float from diverse CSV representations."""
        if pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip()
        is_negative = False
        if val_str.startswith("(") and val_str.endswith(")"):
            is_negative = True
            val_str = val_str[1:-1].strip()
        elif val_str.startswith("-"):
            is_negative = True
            val_str = val_str[1:].strip()

        for c in ["$", "€", "£", "¥", ",", " "]:
            val_str = val_str.replace(c, "")

        try:
            num = float(val_str)
            return -num if is_negative else num
        except ValueError:
            return None
