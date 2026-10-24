"""
FIN SIGHT AI - PDF Extractor
Extracts text and basic table content from PDF files using PyMuPDF.
Preserves page numbers and document metadata.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from src.utils.config import MAX_FILE_SIZE_BYTES
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PageContent:
    """Content extracted from a single PDF page."""
    page_number: int          # 1-indexed
    text: str
    tables: List[List[str]] = field(default_factory=list)
    word_count: int = 0
    char_count: int = 0


@dataclass
class DocumentContent:
    """All content extracted from a document (PDF, Excel, CSV, Image, Manual)."""
    file_path: str = ""
    file_name: str = ""
    total_pages: int = 1
    pages: List[PageContent] = field(default_factory=list)
    full_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    extraction_time_seconds: float = 0.0
    extraction_warnings: List[str] = field(default_factory=list)
    file_size_bytes: int = 0


class PDFExtractor:
    """Extract text and tables from PDF files using PyMuPDF."""

    def __init__(self):
        self.max_file_size = MAX_FILE_SIZE_BYTES

    def validate_file(self, file_path: str) -> Optional[str]:
        """
        Validate the PDF file before extraction.
        Returns an error message string if invalid, or None if valid.
        """
        path = Path(file_path)

        if not path.exists():
            return f"File not found: {file_path}"

        if path.suffix.lower() != ".pdf":
            return f"File must be a PDF. Got: {path.suffix}"

        size = path.stat().st_size
        if size == 0:
            return "File is empty (0 bytes)."

        max_mb = self.max_file_size / (1024 * 1024)
        if size > self.max_file_size:
            return f"File size ({size / (1024*1024):.1f} MB) exceeds limit ({max_mb:.0f} MB)."

        return None

    def extract(self, file_path: str) -> DocumentContent:
        """
        Extract text from all pages of a PDF file.

        Args:
            file_path: Absolute path to the PDF file.

        Returns:
            DocumentContent with page-level text and metadata.

        Raises:
            ValueError: For invalid or unreadable files.
            RuntimeError: For PyMuPDF errors.
        """
        start = time.time()
        path = Path(file_path)

        # Validate
        error = self.validate_file(file_path)
        if error:
            raise ValueError(error)

        logger.info("Starting PDF extraction: %s", path.name)

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise RuntimeError(f"Cannot open PDF: {exc}") from exc

        if doc.page_count == 0:
            doc.close()
            raise ValueError("PDF has no pages.")

        # Extract PDF metadata
        meta = doc.metadata or {}
        metadata = {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "creation_date": meta.get("creationDate", ""),
            "mod_date": meta.get("modDate", ""),
            "total_pages": doc.page_count,
            "file_size_bytes": path.stat().st_size,
        }

        pages: List[PageContent] = []
        warnings: List[str] = []
        all_text_parts: List[str] = []

        for page_idx in range(doc.page_count):
            page_num = page_idx + 1
            page = doc[page_idx]

            try:
                raw_text = page.get_text("text")
            except Exception as exc:
                warnings.append(f"Page {page_num}: text extraction failed – {exc}")
                raw_text = ""

            # Extract tables using PyMuPDF's table finder
            tables = []
            try:
                table_finder = page.find_tables()
                for tbl in table_finder.tables:
                    extracted = tbl.extract()
                    if extracted:
                        # Convert None cells to empty strings
                        cleaned = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in extracted
                        ]
                        tables.append(cleaned)
            except Exception:
                pass  # table extraction is best-effort

            pc = PageContent(
                page_number=page_num,
                text=raw_text,
                tables=tables,
                word_count=len(raw_text.split()),
                char_count=len(raw_text),
            )
            pages.append(pc)

            # Build page header for full-text so we can trace back
            page_header = f"\n\n--- PAGE {page_num} ---\n"
            all_text_parts.append(page_header + raw_text)

        doc.close()

        full_text = "\n".join(all_text_parts)
        elapsed = time.time() - start

        if not full_text.strip():
            warnings.append(
                "No readable text was found. The PDF may be image-based or encrypted."
            )

        result = DocumentContent(
            file_path=file_path,
            file_name=path.name,
            total_pages=len(pages),
            pages=pages,
            full_text=full_text,
            metadata=metadata,
            extraction_time_seconds=elapsed,
            extraction_warnings=warnings,
            file_size_bytes=path.stat().st_size if path.exists() else 0,
        )

        logger.info(
            "Extraction complete: %d pages, %d chars, %.2fs",
            result.total_pages,
            len(result.full_text),
            elapsed,
        )
        return result

    def extract_from_bytes(self, pdf_bytes: bytes, file_name: str) -> DocumentContent:
        """
        Extract text from PDF or TXT bytes (e.g., from a Streamlit upload).

        Args:
            pdf_bytes: Raw PDF or text file bytes.
            file_name: Original filename for metadata.

        Returns:
            DocumentContent.
        """
        if file_name.lower().endswith((".txt", ".text", ".md", ".log", ".json")):
            try:
                raw_text = pdf_bytes.decode("utf-8", errors="replace")
            except Exception:
                raw_text = str(pdf_bytes)
            pages = [
                PageContent(
                    page_number=1,
                    text=raw_text,
                    tables=[],
                    word_count=len(raw_text.split()),
                    char_count=len(raw_text),
                )
            ]
            return DocumentContent(
                file_path=file_name,
                file_name=file_name,
                total_pages=1,
                pages=pages,
                full_text=raw_text,
                metadata={"title": file_name, "format": "text"},
                extraction_time_seconds=0.01,
                extraction_warnings=[],
                file_size_bytes=len(pdf_bytes),
            )

        import tempfile
        import os

        # Write to a temp file and extract
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            content = self.extract(tmp_path)
            content.file_name = file_name  # restore original name
            content.file_size_bytes = len(pdf_bytes)
            return content
        finally:
            os.unlink(tmp_path)
