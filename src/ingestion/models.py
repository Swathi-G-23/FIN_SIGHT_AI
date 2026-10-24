"""
FIN SIGHT AI - Unified Ingestion Data Models
Defines internal representations and source provenance across all input modalities:
PDF, Excel, CSV, Images, and Manual Financial Entry.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InputSourceType(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    IMAGE = "image"
    MANUAL = "manual"


@dataclass
class SourceProvenance:
    """Tracks exact source location of financial data."""
    source_type: InputSourceType
    filename: str
    page_number: Optional[int] = None       # For PDF
    sheet_name: Optional[str] = None        # For Excel
    row_index: Optional[int] = None         # For CSV/Excel
    column_name: Optional[str] = None      # For CSV/Excel
    confidence: float = 1.0                 # 0.0 to 1.0 (lower for OCR)
    notes: str = ""

    def to_citation(self) -> str:
        """Formatted human-readable citation string."""
        if self.source_type == InputSourceType.PDF:
            return f"[{self.filename} - Page {self.page_number}]" if self.page_number else f"[{self.filename}]"
        elif self.source_type == InputSourceType.EXCEL:
            parts = [self.filename]
            if self.sheet_name:
                parts.append(f"Sheet: {self.sheet_name}")
            if self.row_index is not None:
                parts.append(f"Row: {self.row_index}")
            return f"[{' - '.join(parts)}]"
        elif self.source_type == InputSourceType.CSV:
            return f"[{self.filename} - Row {self.row_index}]" if self.row_index is not None else f"[{self.filename}]"
        elif self.source_type == InputSourceType.IMAGE:
            return f"[{self.filename} (OCR image, conf: {self.confidence:.0%})]"
        elif self.source_type == InputSourceType.MANUAL:
            return f"[Manual Entry - {self.filename}]"
        return f"[{self.filename}]"


@dataclass
class FinancialPeriodRecord:
    """Standardized representation of a single company's financial figures for one reporting period."""
    company_name: str
    reporting_period: str                   # e.g., "FY2023", "Q3 2023"
    currency: str = "USD"
    unit: str = "millions"                  # e.g., "millions", "billions", "raw"
    
    # Income Statement
    revenue: Optional[float] = None
    cost_of_goods_sold: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_expenses: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    tax_expense: Optional[float] = None
    interest_expense: Optional[float] = None
    
    # Balance Sheet
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_debt: Optional[float] = None
    total_equity: Optional[float] = None
    
    # Cash Flow
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None

    # Provenance and Metadata
    provenance: Dict[str, SourceProvenance] = field(default_factory=dict)
    raw_text: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_ratio(self, name: str) -> Optional[float]:
        """Calculates standard financial ratio if underlying values are present."""
        if name == "net_profit_margin" and self.revenue and self.net_income is not None:
            return round((self.net_income / self.revenue) * 100, 2)
        elif name == "operating_margin" and self.revenue and self.operating_income is not None:
            return round((self.operating_income / self.revenue) * 100, 2)
        elif name == "gross_margin" and self.revenue and self.gross_profit is not None:
            return round((self.gross_profit / self.revenue) * 100, 2)
        elif name == "current_ratio" and self.current_liabilities and self.current_assets is not None:
            return round(self.current_assets / self.current_liabilities, 2)
        elif name == "debt_to_equity" and self.total_equity and self.total_debt is not None:
            return round(self.total_debt / self.total_equity, 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name,
            "reporting_period": self.reporting_period,
            "currency": self.currency,
            "unit": self.unit,
            "revenue": self.revenue,
            "cost_of_goods_sold": self.cost_of_goods_sold,
            "gross_profit": self.gross_profit,
            "operating_expenses": self.operating_expenses,
            "operating_income": self.operating_income,
            "net_income": self.net_income,
            "total_assets": self.total_assets,
            "current_assets": self.current_assets,
            "cash_and_equivalents": self.cash_and_equivalents,
            "total_liabilities": self.total_liabilities,
            "current_liabilities": self.current_liabilities,
            "total_debt": self.total_debt,
            "total_equity": self.total_equity,
            "operating_cash_flow": self.operating_cash_flow,
            "investing_cash_flow": self.investing_cash_flow,
            "financing_cash_flow": self.financing_cash_flow,
        }
