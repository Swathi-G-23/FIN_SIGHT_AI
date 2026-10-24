"""
FIN SIGHT AI - Document Session Manager
Unified ingestion and state management supporting multimodal inputs:
PDF, Excel (.xlsx, .xls), CSV, Images (OCR), and Manual Financial Data Entry.
Integrates performance metrics, storage adapters, and multi-period financial records.
"""
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.ingestion.pdf_extractor import PDFExtractor, DocumentContent, PageContent
from src.ingestion.excel_extractor import ExcelExtractor, ExcelExtractionResult
from src.ingestion.csv_extractor import CSVExtractor, CSVExtractionResult
from src.ingestion.image_ocr_extractor import ImageOCRExtractor, ImageOCRExtractionResult
from src.ingestion.manual_entry import ManualDataEntryManager, ManualEntryValidationResult
from src.ingestion.models import FinancialPeriodRecord, InputSourceType, SourceProvenance
from src.ingestion.chunker import TextChunker, TextChunk
from src.retrieval.embeddings import EmbeddingGenerator
from src.retrieval.vector_store import FAISSVectorStore, VectorStoreFactory
from src.retrieval.keyword_search import KeywordSearcher
from src.retrieval.hybrid_retriever import HybridRetriever
from src.finance.metric_extraction import extract_financial_metrics, ExtractedMetric
from src.monitoring.performance import PerformanceMonitor
from src.storage.storage_adapter import get_storage_adapter
from src.utils.config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentSession:
    """Holds all state for a processed document."""
    document_id: str
    file_name: str
    document_content: DocumentContent
    chunks: List[TextChunk]
    vector_store: FAISSVectorStore
    keyword_searcher: KeywordSearcher
    retriever: HybridRetriever
    extracted_metrics_raw: Dict[str, Any]
    processing_time_seconds: float
    chunk_count: int
    page_count: int
    metrics_found: int
    source_type: InputSourceType = InputSourceType.PDF
    financial_records: List[FinancialPeriodRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    provenance_map: Dict[str, SourceProvenance] = field(default_factory=dict)
    company_name: str = "Company"

    @property
    def document_name(self) -> str:
        return self.file_name

    @property
    def extracted_metrics(self) -> Dict[str, Any]:
        """Provides backward-compatible and summary dictionary of extracted metrics."""
        from src.finance.metric_extraction import metrics_summary
        return {"metrics_summary": metrics_summary(self.extracted_metrics_raw)}


def detect_company_name(file_name: str, full_text: str = "") -> str:
    """Intelligently detects corporate name from file name or front page text."""
    clean_stem = Path(file_name).stem.replace("_", " ").replace("-", " ")
    for stop_word in ["FY20", "FY 20", "202", "Annual Report", "Financial Report", "Earnings Release", "Report", "10-K", "10K"]:
        if stop_word.lower() in clean_stem.lower():
            idx = clean_stem.lower().find(stop_word.lower())
            candidate = clean_stem[:idx].strip()
            if len(candidate) >= 3:
                return candidate
    if full_text:
        lines = [line.strip() for line in full_text.split("\n")[:12] if line.strip()]
        for line in lines:
            if any(term in line.lower() for term in ["inc", "corp", "corporation", "ltd", "limited", "technologies", "holdings", "group", "co."]):
                if 3 <= len(line) <= 50:
                    return line
    return clean_stem[:30] if clean_stem else "Company"


def convert_extracted_metrics_to_financial_records(
    extracted_metrics: Dict[str, List[ExtractedMetric]],
    company_name: str,
    file_name: str,
    default_period: str = "FY2023",
) -> List[FinancialPeriodRecord]:
    """Convert ExtractedMetric dictionary into normalized FinancialPeriodRecord objects."""
    records_by_period: Dict[str, FinancialPeriodRecord] = {}
    attr_map = {
        "revenue": "revenue",
        "total_revenue": "revenue",
        "cogs": "cost_of_goods_sold",
        "cost_of_goods_sold": "cost_of_goods_sold",
        "gross_profit": "gross_profit",
        "operating_expenses": "operating_expenses",
        "opex": "operating_expenses",
        "operating_income": "operating_income",
        "operating_profit": "operating_income",
        "ebit": "operating_income",
        "net_income": "net_income",
        "net_profit": "net_income",
        "profit": "net_income",
        "total_assets": "total_assets",
        "current_assets": "current_assets",
        "cash_and_equivalents": "cash_and_equivalents",
        "cash": "cash_and_equivalents",
        "inventory": "inventory",
        "total_liabilities": "total_liabilities",
        "current_liabilities": "current_liabilities",
        "total_debt": "total_debt",
        "total_equity": "total_equity",
        "shareholders_equity": "total_equity",
        "operating_cash_flow": "operating_cash_flow",
    }
    for key, metrics in extracted_metrics.items():
        attr = attr_map.get(key)
        if not attr:
            continue
        for m in metrics:
            period = m.period or default_period
            if period not in records_by_period:
                records_by_period[period] = FinancialPeriodRecord(
                    company_name=company_name,
                    reporting_period=period,
                    unit=m.unit or "millions",
                )
            rec = records_by_period[period]
            val = m.normalized_value or m.numeric_value
            if val is not None and getattr(rec, attr) is None:
                setattr(rec, attr, float(val))
                rec.provenance[attr] = SourceProvenance(
                    source_type=InputSourceType.PDF,
                    filename=file_name,
                    page_number=m.page_number or 1,
                    confidence=0.95 if m.confidence == "high" else 0.85,
                    notes=m.source_text or f"Extracted from {file_name} Page {m.page_number}",
                )

    records = list(records_by_period.values())
    if not records:
        records = [
            FinancialPeriodRecord(
                company_name=company_name,
                reporting_period=default_period,
            )
        ]
    return records


def compute_document_id(file_name: str, file_size: int) -> str:
    """Generate a stable document ID from the file name and size."""
    raw = f"{file_name}_{file_size}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _build_retrieval_components(
    doc_id: str,
    chunks: List[TextChunk],
    emb_gen: EmbeddingGenerator,
    report_fn: Optional[Callable[[str, float], None]] = None
) -> tuple[FAISSVectorStore, KeywordSearcher, HybridRetriever]:
    """Helper to build FAISS and BM25 indices from chunks."""
    if report_fn:
        report_fn("Generating semantic embeddings…", 0.45)
    
    t0 = time.perf_counter()
    texts = [c.text for c in chunks]
    embeddings = emb_gen.embed_texts(texts, show_progress=False)
    t_emb = time.perf_counter() - t0
    PerformanceMonitor().record_metric("Embedding Generation", t_emb, {"chunk_count": len(chunks)})

    if report_fn:
        report_fn("Building FAISS vector index…", 0.65)
    
    t0 = time.perf_counter()
    vector_store: FAISSVectorStore = VectorStoreFactory.create(doc_id, backend="faiss")
    vector_store.build(embeddings, chunks)
    t_vec = time.perf_counter() - t0
    PerformanceMonitor().record_metric("FAISS Vector Store Build", t_vec, {"embeddings": len(embeddings)})

    if report_fn:
        report_fn("Building BM25 keyword search index…", 0.80)
    
    t0 = time.perf_counter()
    keyword_searcher = KeywordSearcher()
    keyword_searcher.build(vector_store.all_chunks)
    t_bm25 = time.perf_counter() - t0
    PerformanceMonitor().record_metric("BM25 Index Build", t_bm25, {"documents": len(chunks)})

    retriever = HybridRetriever(vector_store, keyword_searcher, emb_gen)
    return vector_store, keyword_searcher, retriever


# ── 1. PDF Processing Pipeline ──────────────────────────────────────────────
def process_document(
    pdf_bytes: bytes,
    file_name: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    progress_callback=None,
) -> DocumentSession:
    """Full ingestion pipeline for a PDF document."""
    overall_start = time.time()
    monitor = PerformanceMonitor()

    def report(step: str, pct: float):
        logger.info("[%.0f%%] %s", pct * 100, step)
        if progress_callback:
            progress_callback(step, pct)

    report("Extracting text and tables from PDF…", 0.05)
    t_extract_start = time.perf_counter()
    extractor = PDFExtractor()
    doc_content = extractor.extract_from_bytes(pdf_bytes, file_name)
    t_extract = time.perf_counter() - t_extract_start
    monitor.record_metric("PDF Extraction", t_extract, {"pages": doc_content.total_pages, "size_bytes": len(pdf_bytes)})

    if not doc_content.full_text.strip():
        raise ValueError(
            "No readable text extracted. The PDF may be scanned or encrypted. "
            "Please upload readable text or an image using the OCR / Manual tab."
        )

    doc_id = compute_document_id(file_name, len(pdf_bytes))

    # Persist via storage adapter
    try:
        storage = get_storage_adapter()
        storage.save_file(pdf_bytes, f"data/uploads/{doc_id}_{file_name}")
    except Exception as e:
        logger.warning(f"Could not persist PDF copy: {e}")

    report("Splitting text into overlapping chunks…", 0.25)
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = chunker.chunk_document(
        document_id=doc_id,
        pages=doc_content.pages,
        doc_metadata={"file_name": file_name, "document_id": doc_id, "source_type": "pdf"},
    )

    if not chunks:
        raise ValueError("Text chunking produced no chunks. The document may be empty after cleaning.")

    emb_gen = EmbeddingGenerator(model_name=EMBEDDING_MODEL)
    vector_store, keyword_searcher, retriever = _build_retrieval_components(
        doc_id=doc_id, chunks=chunks, emb_gen=emb_gen, report_fn=report
    )

    report("Extracting financial metrics…", 0.90)
    extracted_metrics_raw = extract_financial_metrics(doc_content.pages)
    metrics_found = sum(1 for v in extracted_metrics_raw.values() if v)

    comp_name = detect_company_name(file_name, doc_content.full_text)
    financial_records = convert_extracted_metrics_to_financial_records(
        extracted_metrics_raw,
        company_name=comp_name,
        file_name=file_name,
    )

    elapsed = time.time() - overall_start
    monitor.record_metric("Total PDF Ingestion", elapsed, {"document_id": doc_id, "chunks": len(chunks)})
    report("Processing complete!", 1.0)

    return DocumentSession(
        document_id=doc_id,
        file_name=file_name,
        document_content=doc_content,
        chunks=chunks,
        vector_store=vector_store,
        keyword_searcher=keyword_searcher,
        retriever=retriever,
        extracted_metrics_raw=extracted_metrics_raw,
        processing_time_seconds=elapsed,
        chunk_count=len(chunks),
        page_count=doc_content.total_pages,
        metrics_found=metrics_found,
        source_type=InputSourceType.PDF,
        financial_records=financial_records,
        warnings=doc_content.extraction_warnings,
        company_name=comp_name,
    )


def convert_financial_records_to_extracted_metrics(records: List[FinancialPeriodRecord]) -> Dict[str, List[ExtractedMetric]]:
    """Convert structured FinancialPeriodRecords into normalized ExtractedMetric objects."""
    out: Dict[str, List[ExtractedMetric]] = {}
    attr_to_keys = {
        "revenue": ["revenue", "total_revenue"],
        "cost_of_goods_sold": ["cogs", "cost_of_goods_sold"],
        "gross_profit": ["gross_profit"],
        "operating_expenses": ["operating_expenses", "opex"],
        "operating_income": ["operating_income", "operating_profit", "ebit"],
        "net_income": ["net_income", "net_profit", "profit"],
        "total_assets": ["total_assets"],
        "current_assets": ["current_assets"],
        "cash_and_equivalents": ["cash_and_equivalents", "cash"],
        "inventory": ["inventory"],
        "total_liabilities": ["total_liabilities"],
        "current_liabilities": ["current_liabilities"],
        "total_debt": ["total_debt"],
        "total_equity": ["total_equity", "shareholders_equity"],
        "operating_cash_flow": ["operating_cash_flow", "cash_flow"],
    }
    for rec in records:
        for attr, keys in attr_to_keys.items():
            val = getattr(rec, attr, None)
            if val is not None and val != 0.0:
                metric_obj = ExtractedMetric(
                    metric_key=keys[0],
                    metric_label=attr.replace("_", " ").title(),
                    raw_value=f"{val:,.2f}",
                    numeric_value=float(val),
                    unit=rec.currency or "USD",
                    unit_multiplier=1.0,
                    normalized_value=float(val),
                    period=rec.reporting_period or "",
                    page_number=1,
                    confidence="high",
                    is_extracted=True,
                    source_text=f"{rec.company_name} {rec.reporting_period} {attr}: {val:,.2f}",
                )
                for k in keys:
                    out.setdefault(k, []).append(metric_obj)
    return out


# ── 2. Excel Processing Pipeline ────────────────────────────────────────────
def process_excel_document(
    file_bytes: bytes,
    file_name: str,
    sheet_name: Optional[str] = None,
    company_name: str = "Company",
    progress_callback=None,
) -> tuple[DocumentSession, ExcelExtractionResult]:
    """Ingestion pipeline for Excel spreadsheets (.xlsx, .xls)."""
    overall_start = time.time()
    monitor = PerformanceMonitor()

    def report(step: str, pct: float):
        logger.info("[%.0f%%] %s", pct * 100, step)
        if progress_callback:
            progress_callback(step, pct)

    report("Parsing Excel sheets and tables…", 0.10)
    doc_id = compute_document_id(file_name, len(file_bytes))

    # Save to temp path for Excel parsing
    temp_dir = Path("data/uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{doc_id}_{file_name}"
    temp_path.write_bytes(file_bytes)

    extractor = ExcelExtractor()
    excel_result = extractor.extract(temp_path, sheet_name=sheet_name, company_name=company_name)

    # Wrap in PageContent for compatibility
    pages = [PageContent(page_number=1, text=excel_result.text_content)]
    doc_content = DocumentContent(
        file_path=str(temp_path),
        file_name=file_name,
        file_size_bytes=len(file_bytes),
        total_pages=1,
        pages=pages,
        full_text=excel_result.text_content,
    )

    report("Chunking tabular content…", 0.30)
    chunker = TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = chunker.chunk_document(
        document_id=doc_id,
        pages=pages,
        doc_metadata={"file_name": file_name, "sheet": excel_result.selected_sheet, "source_type": "excel"},
    )

    emb_gen = EmbeddingGenerator(model_name=EMBEDDING_MODEL)
    vector_store, keyword_searcher, retriever = _build_retrieval_components(
        doc_id=doc_id, chunks=chunks, emb_gen=emb_gen, report_fn=report
    )

    report("Mapping financial metrics…", 0.90)
    extracted_metrics_raw = extract_financial_metrics(pages)
    rec_metrics = convert_financial_records_to_extracted_metrics(excel_result.financial_records)
    for k, v in rec_metrics.items():
        extracted_metrics_raw.setdefault(k, []).extend(v)
    metrics_found = sum(1 for v in extracted_metrics_raw.values() if v)

    elapsed = time.time() - overall_start
    monitor.record_metric("Total Excel Ingestion", elapsed, {"sheet": excel_result.selected_sheet})
    report("Excel processing complete!", 1.0)

    session = DocumentSession(
        document_id=doc_id,
        file_name=file_name,
        document_content=doc_content,
        chunks=chunks,
        vector_store=vector_store,
        keyword_searcher=keyword_searcher,
        retriever=retriever,
        extracted_metrics_raw=extracted_metrics_raw,
        processing_time_seconds=elapsed,
        chunk_count=len(chunks),
        page_count=1,
        metrics_found=metrics_found,
        source_type=InputSourceType.EXCEL,
        financial_records=excel_result.financial_records,
    )
    return session, excel_result


# ── 3. CSV Processing Pipeline ──────────────────────────────────────────────
def process_csv_document(
    file_bytes: bytes,
    file_name: str,
    column_mapping: Optional[Dict[str, str]] = None,
    company_name: str = "Company",
    progress_callback=None,
) -> tuple[DocumentSession, CSVExtractionResult]:
    """Ingestion pipeline for CSV financial datasets."""
    overall_start = time.time()
    monitor = PerformanceMonitor()

    def report(step: str, pct: float):
        logger.info("[%.0f%%] %s", pct * 100, step)
        if progress_callback:
            progress_callback(step, pct)

    report("Loading and validating CSV dataset…", 0.10)
    doc_id = compute_document_id(file_name, len(file_bytes))

    temp_dir = Path("data/uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{doc_id}_{file_name}"
    temp_path.write_bytes(file_bytes)

    extractor = CSVExtractor()
    csv_result = extractor.extract(temp_path, column_mapping=column_mapping, default_company=company_name)

    pages = [PageContent(page_number=1, text=csv_result.text_content)]
    doc_content = DocumentContent(
        file_path=str(temp_path),
        file_name=file_name,
        file_size_bytes=len(file_bytes),
        total_pages=1,
        pages=pages,
        full_text=csv_result.text_content,
    )

    report("Chunking dataset records…", 0.30)
    chunker = TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = chunker.chunk_document(
        document_id=doc_id,
        pages=pages,
        doc_metadata={"file_name": file_name, "source_type": "csv"},
    )

    emb_gen = EmbeddingGenerator(model_name=EMBEDDING_MODEL)
    vector_store, keyword_searcher, retriever = _build_retrieval_components(
        doc_id=doc_id, chunks=chunks, emb_gen=emb_gen, report_fn=report
    )

    extracted_metrics_raw = extract_financial_metrics(pages)
    rec_metrics = convert_financial_records_to_extracted_metrics(csv_result.financial_records)
    for k, v in rec_metrics.items():
        extracted_metrics_raw.setdefault(k, []).extend(v)
    metrics_found = sum(1 for v in extracted_metrics_raw.values() if v)

    elapsed = time.time() - overall_start
    monitor.record_metric("Total CSV Ingestion", elapsed, {"rows": csv_result.validation.total_rows})
    report("CSV dataset indexed!", 1.0)

    session = DocumentSession(
        document_id=doc_id,
        file_name=file_name,
        document_content=doc_content,
        chunks=chunks,
        vector_store=vector_store,
        keyword_searcher=keyword_searcher,
        retriever=retriever,
        extracted_metrics_raw=extracted_metrics_raw,
        processing_time_seconds=elapsed,
        chunk_count=len(chunks),
        page_count=1,
        metrics_found=metrics_found,
        source_type=InputSourceType.CSV,
        financial_records=csv_result.financial_records,
        warnings=csv_result.validation.warnings,
    )
    return session, csv_result


# ── 4. Image OCR Processing Pipeline ────────────────────────────────────────
def process_image_document(
    file_bytes: bytes,
    file_name: str,
    company_name: str = "Company",
    reporting_period: str = "FY2023",
    progress_callback=None,
) -> tuple[Optional[DocumentSession], ImageOCRExtractionResult]:
    """Ingestion pipeline for statement images (PNG, JPG) via OCR."""
    overall_start = time.time()
    monitor = PerformanceMonitor()

    def report(step: str, pct: float):
        logger.info("[%.0f%%] %s", pct * 100, step)
        if progress_callback:
            progress_callback(step, pct)

    report("Running OCR on financial statement image…", 0.15)
    doc_id = compute_document_id(file_name, len(file_bytes))

    temp_dir = Path("data/uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{doc_id}_{file_name}"
    temp_path.write_bytes(file_bytes)

    extractor = ImageOCRExtractor()
    ocr_result = extractor.extract(temp_path, company_name=company_name, reporting_period=reporting_period)

    if not ocr_result.extracted_text.strip():
        return None, ocr_result

    pages = [PageContent(page_number=1, text=ocr_result.extracted_text)]
    doc_content = DocumentContent(
        file_path=str(temp_path),
        file_name=file_name,
        file_size_bytes=len(file_bytes),
        total_pages=1,
        pages=pages,
        full_text=ocr_result.extracted_text,
    )

    report("Chunking OCR text…", 0.35)
    chunker = TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = chunker.chunk_document(
        document_id=doc_id,
        pages=pages,
        doc_metadata={"file_name": file_name, "source_type": "image", "confidence": ocr_result.confidence_score},
    )

    emb_gen = EmbeddingGenerator(model_name=EMBEDDING_MODEL)
    vector_store, keyword_searcher, retriever = _build_retrieval_components(
        doc_id=doc_id, chunks=chunks, emb_gen=emb_gen, report_fn=report
    )

    extracted_metrics_raw = extract_financial_metrics(pages)
    records = [ocr_result.financial_record] if ocr_result.financial_record else []
    rec_metrics = convert_financial_records_to_extracted_metrics(records)
    for k, v in rec_metrics.items():
        extracted_metrics_raw.setdefault(k, []).extend(v)
    metrics_found = sum(1 for v in extracted_metrics_raw.values() if v)

    elapsed = time.time() - overall_start
    monitor.record_metric("Total Image OCR Ingestion", elapsed, {"conf": ocr_result.confidence_score})
    report("Image text and metrics indexed!", 1.0)

    session = DocumentSession(
        document_id=doc_id,
        file_name=file_name,
        document_content=doc_content,
        chunks=chunks,
        vector_store=vector_store,
        keyword_searcher=keyword_searcher,
        retriever=retriever,
        extracted_metrics_raw=extracted_metrics_raw,
        processing_time_seconds=elapsed,
        chunk_count=len(chunks),
        page_count=1,
        metrics_found=metrics_found,
        source_type=InputSourceType.IMAGE,
        financial_records=records,
        warnings=ocr_result.uncertain_lines,
    )
    return session, ocr_result


# ── 5. Manual Financial Record Pipeline ─────────────────────────────────────
def process_manual_financial_record(
    record: FinancialPeriodRecord,
) -> DocumentSession:
    """Creates a full DocumentSession from a manually entered financial record."""
    overall_start = time.time()
    monitor = PerformanceMonitor()

    doc_name = f"Manual_{record.company_name}_{record.reporting_period}"
    doc_id = hashlib.md5(f"{doc_name}_{time.time()}".encode()).hexdigest()[:16]

    pages = [PageContent(page_number=1, text=record.raw_text)]
    doc_content = DocumentContent(
        file_path=doc_name,
        file_name=doc_name,
        file_size_bytes=len(record.raw_text.encode()),
        total_pages=1,
        pages=pages,
        full_text=record.raw_text,
    )

    chunker = TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = chunker.chunk_document(
        document_id=doc_id,
        pages=pages,
        doc_metadata={"file_name": doc_name, "source_type": "manual", "company": record.company_name},
    )

    emb_gen = EmbeddingGenerator(model_name=EMBEDDING_MODEL)
    vector_store, keyword_searcher, retriever = _build_retrieval_components(
        doc_id=doc_id, chunks=chunks, emb_gen=emb_gen
    )

    extracted_metrics_raw = extract_financial_metrics(pages)
    rec_metrics = convert_financial_records_to_extracted_metrics([record])
    for k, v in rec_metrics.items():
        extracted_metrics_raw.setdefault(k, []).extend(v)
    metrics_found = sum(1 for v in extracted_metrics_raw.values() if v)

    elapsed = time.time() - overall_start
    monitor.record_metric("Manual Ingestion", elapsed, {"company": record.company_name, "period": record.reporting_period})

    return DocumentSession(
        document_id=doc_id,
        file_name=doc_name,
        document_content=doc_content,
        chunks=chunks,
        vector_store=vector_store,
        keyword_searcher=keyword_searcher,
        retriever=retriever,
        extracted_metrics_raw=extracted_metrics_raw,
        processing_time_seconds=elapsed,
        chunk_count=len(chunks),
        page_count=1,
        metrics_found=metrics_found,
        source_type=InputSourceType.MANUAL,
        financial_records=[record],
        provenance_map=record.provenance,
    )
