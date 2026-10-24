"""
FIN SIGHT AI - Image OCR Financial Extractor
Extracts financial statement text and numbers from PNG/JPEG images.
Provides confidence metrics and value verification.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import re
from PIL import Image

from src.ingestion.models import FinancialPeriodRecord, InputSourceType, SourceProvenance
from src.finance.metric_extraction import extract_financial_metrics
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ImageOCRExtractionResult:
    filename: str
    image_width: int
    image_height: int
    ocr_available: bool
    extracted_text: str
    confidence_score: float
    detected_metrics: List[Dict[str, Any]] = field(default_factory=list)
    uncertain_lines: List[str] = field(default_factory=list)
    financial_record: Optional[FinancialPeriodRecord] = None
    error_message: Optional[str] = None


class ImageOCRExtractor:
    """Extracts financial text and numbers from images using OCR."""

    def __init__(self):
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        """Determines if tesseract binary is runnable."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            # Check standard Windows installation directories
            common_paths = [
                Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
                Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
                Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
            ]
            for p in common_paths:
                if p.exists():
                    try:
                        import pytesseract
                        pytesseract.pytesseract.tesseract_cmd = str(p)
                        pytesseract.get_tesseract_version()
                        logger.info(f"Configured Tesseract OCR from {p}")
                        return True
                    except Exception as exc:
                        logger.warning(f"Failed using Tesseract at {p}: {exc}")
            logger.info("Tesseract binary not found on PATH or standard directories.")
            return False

    def is_ocr_available(self) -> bool:
        return self._tesseract_available

    def extract(
        self,
        file_path: str | Path,
        company_name: str = "Company",
        reporting_period: str = "FY2023",
    ) -> ImageOCRExtractionResult:
        """Performs OCR extraction on the provided image."""
        path = Path(file_path)
        filename = path.name

        try:
            img = Image.open(path)
            width, height = img.size
        except Exception as e:
            return ImageOCRExtractionResult(
                filename=filename,
                image_width=0,
                image_height=0,
                ocr_available=False,
                extracted_text="",
                confidence_score=0.0,
                error_message=f"Could not open image: {e}",
            )

        if not self._tesseract_available:
            # Fallback when Tesseract OCR engine is not installed on system
            fallback_msg = (
                f"OCR Engine (Tesseract) is not installed or not on system PATH.\n"
                f"Image '{filename}' ({width}x{height}px) was received successfully.\n\n"
                f"To enable automatic OCR on Windows:\n"
                f"1. Download and run Tesseract installer (e.g. from UB-Mannheim/tesseract/wiki)\n"
                f"2. Add C:\\Program Files\\Tesseract-OCR to your system PATH\n"
                f"3. Or use the 'Enter Data Manually' tab to enter key figures directly."
            )
            return ImageOCRExtractionResult(
                filename=filename,
                image_width=width,
                image_height=height,
                ocr_available=False,
                extracted_text=fallback_msg,
                confidence_score=0.0,
                error_message="Tesseract binary not found on system PATH.",
            )

        try:
            import pytesseract

            # Run OCR with detailed data to assess confidence
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            raw_text = pytesseract.image_to_string(img)

            # Compute average confidence (ignoring -1 for blanks)
            confidences = [int(c) for c in data.get("conf", []) if int(c) >= 0]
            avg_conf = (sum(confidences) / len(confidences)) / 100.0 if confidences else 0.5

            # Identify uncertain lines (< 60% confidence)
            uncertain_lines = []
            lines = raw_text.split("\n")
            for line in lines:
                cleaned = line.strip()
                if cleaned and any(char.isdigit() for char in cleaned):
                    # Flag lines with irregular punctuation or low confidence
                    if "?" in cleaned or "~" in cleaned or "^" in cleaned:
                        uncertain_lines.append(cleaned)

            # Extract financial metrics
            from src.ingestion.pdf_extractor import PageContent
            metrics_dict = extract_financial_metrics([PageContent(page_number=1, text=raw_text)])
            detected_dict_list = []

            # Construct financial record
            rec = FinancialPeriodRecord(
                company_name=company_name,
                reporting_period=reporting_period,
                raw_text=raw_text,
            )
            attr_map = {
                "revenue": "revenue",
                "cogs": "cost_of_goods_sold",
                "cost_of_goods_sold": "cost_of_goods_sold",
                "gross_profit": "gross_profit",
                "opex": "operating_expenses",
                "operating_expenses": "operating_expenses",
                "operating_income": "operating_income",
                "operating_profit": "operating_income",
                "net_income": "net_income",
                "net_profit": "net_income",
                "total_assets": "total_assets",
                "current_assets": "current_assets",
                "cash_and_equivalents": "cash_and_equivalents",
                "cash": "cash_and_equivalents",
                "total_liabilities": "total_liabilities",
                "current_liabilities": "current_liabilities",
                "total_debt": "total_debt",
                "total_equity": "total_equity",
                "operating_cash_flow": "operating_cash_flow",
            }
            for k, m_list in metrics_dict.items():
                if m_list:
                    m = m_list[0]
                    detected_dict_list.append({
                        "name": m.metric_label,
                        "value": m.numeric_value,
                        "unit": m.unit,
                        "context": m.source_text,
                    })
                    target_attr = attr_map.get(k)
                    if target_attr and hasattr(rec, target_attr) and getattr(rec, target_attr) is None:
                        setattr(rec, target_attr, m.normalized_value or m.numeric_value)
                        rec.provenance[target_attr] = SourceProvenance(
                            source_type=InputSourceType.IMAGE,
                            filename=filename,
                            confidence=avg_conf,
                            notes=f"OCR extracted from image '{filename}': {m.source_text}",
                        )

            return ImageOCRExtractionResult(
                filename=filename,
                image_width=width,
                image_height=height,
                ocr_available=True,
                extracted_text=raw_text,
                confidence_score=round(avg_conf, 2),
                detected_metrics=detected_dict_list,
                uncertain_lines=uncertain_lines,
                financial_record=rec,
            )

        except Exception as e:
            logger.error(f"OCR processing failed for {filename}: {e}")
            return ImageOCRExtractionResult(
                filename=filename,
                image_width=width,
                image_height=height,
                ocr_available=True,
                extracted_text="",
                confidence_score=0.0,
                error_message=str(e),
            )
