"""
FIN SIGHT AI - Page 1: Financial Document Ingestion Portal
Unified multimodal input hub supporting PDF, TXT, Excel, CSV, Image (OCR),
and Manual Financial Statement Data Entry.
Clear, non-technical interface with plain-English processing explanations.
"""
from pathlib import Path
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Upload Financial Report | FIN SIGHT AI",
    page_icon="📥",
    layout="wide"
)

from src.ui.theme import (
    apply_light_theme,
    render_sidebar_brand,
    render_page_header,
    render_page_navigation,
)
apply_light_theme()
render_sidebar_brand()

from src.utils.config import MAX_FILE_SIZE_MB
from src.utils.session_manager import (
    process_document,
    process_excel_document,
    process_csv_document,
    process_image_document,
    process_manual_financial_record,
)
from src.ingestion.excel_extractor import ExcelExtractor
from src.ingestion.image_ocr_extractor import ImageOCRExtractor
from src.ingestion.comparator import FinancialComparator
from src.ingestion.models import FinancialPeriodRecord, InputSourceType

render_page_header(
    title="Financial Document Ingestion Portal",
    subtitle="Upload corporate filings, balance sheets, spreadsheets, or input audited metrics directly for multi-agent intelligence."
)

# ── Sample Test Files Expander ───────────────────────────────────────────────
with st.expander("📁 Need Sample Test Files? (Click to view & download all sample formats)", expanded=False):
    st.markdown("All pre-built sample test files are located in your project's `sample_inputs/` folder. You can download them directly below or drag-and-drop them into any tab:")
    c1, c2, c3 = st.columns(3)
    sample_dir = Path("sample_inputs")

    with c1:
        st.markdown("**📄 Document Reports (Tab 1)**")
        p_pdf = sample_dir / "Apex_Technologies_FY2023_Annual_Report.pdf"
        if p_pdf.exists():
            st.download_button("⬇️ Download Sample PDF", data=p_pdf.read_bytes(), file_name=p_pdf.name, mime="application/pdf", key="dl_pdf_sample")
        p_txt = sample_dir / "Apex_Technologies_FY2023_Earnings_Release.txt"
        if p_txt.exists():
            st.download_button("⬇️ Download Sample TXT", data=p_txt.read_bytes(), file_name=p_txt.name, mime="text/plain", key="dl_txt_sample")

    with c2:
        st.markdown("**📊 Spreadsheets (Tabs 2 & 3)**")
        p_xlsx = sample_dir / "Apex_Technologies_Financial_Model_FY2021_FY2023.xlsx"
        if p_xlsx.exists():
            st.download_button("⬇️ Download Sample Excel (.xlsx)", data=p_xlsx.read_bytes(), file_name=p_xlsx.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx_sample")
        p_csv = sample_dir / "Apex_Technologies_Financial_Metrics_FY2020_FY2023.csv"
        if p_csv.exists():
            st.download_button("⬇️ Download Financial Metrics CSV", data=p_csv.read_bytes(), file_name=p_csv.name, mime="text/csv", key="dl_csv_sample")
        p_peer = sample_dir / "Tech_Sector_Peer_Comparison_FY2023.csv"
        if p_peer.exists():
            st.download_button("⬇️ Download Peer Comparison CSV", data=p_peer.read_bytes(), file_name=p_peer.name, mime="text/csv", key="dl_peer_csv_sample")

    with c3:
        st.markdown("**🖼️ Vision & Structured (Tabs 4 & API)**")
        p_img = sample_dir / "Apex_Technologies_Balance_Sheet_Scan.png"
        if p_img.exists():
            st.download_button("⬇️ Download OCR Scan (.png)", data=p_img.read_bytes(), file_name=p_img.name, mime="image/png", key="dl_img_sample")
        p_json = sample_dir / "Apex_Technologies_Financial_Summary.json"
        if p_json.exists():
            st.download_button("⬇️ Download Financial JSON", data=p_json.read_bytes(), file_name=p_json.name, mime="application/json", key="dl_json_sample")

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ── Explanation of Document Processing ──────────────────────────────────────
with st.expander("ℹ️ How document processing works", expanded=False):
    st.markdown(
        """
        Your financial report is divided into smaller, coherent sections so the AI can find the most relevant disclosures, 
        balance sheet line items, and footnotes when answering your questions.

        - **Direct PDF & Text reading:** Text-based filings and statements are parsed directly with exact page references.
        - **Spreadsheet Line Items:** Excel and CSV files are parsed row by row with cell coordinates and accounting classifications.
        - **Scanned Reports & OCR:** If an image is uploaded, text recognition extracts table figures for verification.
        - **Integrity Guarantee:** Every extracted figure is tracked with its provenance (source file, page, or worksheet).
        """
    )

# ── Tab Navigation for Ingestion Methods ─────────────────────────────────────
tab_pdf, tab_excel, tab_csv, tab_img, tab_manual, tab_compare = st.tabs([
    "📄 1. Upload PDF / TXT",
    "📊 2. Upload Excel",
    "📑 3. Upload CSV",
    "🖼️ 4. Upload Image (OCR)",
    "✍️ 5. Enter Data Manually",
    "🔄 6. Compare Multiple Reports",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: PDF & TXT UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
with tab_pdf:
    st.markdown("### 📄 Annual Reports & Financial Statements (PDF / TXT)")
    st.markdown(
        "Upload corporate 10-K, 10-Q, annual reports, or plain text earnings releases. "
        "The system parses text and tables, and constructs semantic search indexes."
    )

    col_up, col_info = st.columns([2, 1])

    with col_info:
        st.markdown("<div class='fin-card'>", unsafe_allow_html=True)
        st.markdown("<div class='fin-card-header'>Processing Notice</div>", unsafe_allow_html=True)
        st.markdown(
            f"**File limit:** Up to {MAX_FILE_SIZE_MB} MB.<br>"
            "Text-based PDFs are processed immediately. If your PDF contains scanned pages without selectable text, "
            "the system falls back to text recognition (OCR) where configured.",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("⚙️ Advanced Processing Settings", expanded=False):
            chunk_size = st.slider("Section size (approx. text grouped together)", 500, 2000, 1000, 100, key="pdf_chunk_size")
            chunk_overlap = st.slider("Overlap between sections (preserves context)", 50, 400, 150, 50, key="pdf_chunk_overlap")

    with col_up:
        pdf_file = st.file_uploader(
            "Select corporate PDF or TXT financial report",
            type=["pdf", "txt", "text", "md"],
            key="pdf_uploader",
            help="Upload 10-K, 10-Q, Annual Report, or Earnings Release"
        )

        if pdf_file is not None:
            file_bytes = pdf_file.read()
            size_mb = len(file_bytes) / (1024 * 1024)
            st.info(f"📁 Selected: **{pdf_file.name}** ({size_mb:.2f} MB)")

            if st.button("🚀 Ingest & Index Document", type="primary", key="btn_pdf_ingest"):
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def update_progress(msg: str, pct: float):
                    progress_bar.progress(pct)
                    status_text.markdown(f"**Status:** {msg}")

                try:
                    # Invalidate stale cache
                    st.session_state.analysis_cache = {}
                    session = process_document(
                        pdf_bytes=file_bytes,
                        file_name=pdf_file.name,
                        chunk_size=chunk_size if "chunk_size" in locals() else 1000,
                        chunk_overlap=chunk_overlap if "chunk_overlap" in locals() else 150,
                        progress_callback=update_progress,
                    )
                    st.session_state.document_session = session
                    st.session_state.selected_company = getattr(session, "company_name", "Apex Technologies")
                    st.session_state.all_records = list(session.financial_records)
                    st.session_state.last_workflow_state = None
                    st.session_state.chat_history = []
                    st.session_state.messages = []
                    st.success(f"✅ Successfully indexed **{pdf_file.name}** in {session.processing_time_seconds:.2f}s!")

                    st.markdown(
                        f"""
                        <div class="callout-box" style="background:#E6F4EA; border-left-color:#24865B; color:#137333;">
                            <b>Indexing Complete:</b> {session.page_count} pages extracted, {session.chunk_count} semantic sections indexed, and {session.metrics_found} audited metric fields detected.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: EXCEL UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
with tab_excel:
    st.markdown("### 📊 Excel Financial Models & Workbooks (.xlsx, .xls)")
    st.markdown("Inspect multiple worksheets, extract structured accounting items with row coordinates, and index for analysis.")

    excel_file = st.file_uploader(
        "Upload Excel financial model or statement",
        type=["xlsx", "xls"],
        key="excel_uploader"
    )

    if excel_file is not None:
        file_bytes = excel_file.read()
        size_mb = len(file_bytes) / (1024 * 1024)
        st.info(f"📊 Selected: **{excel_file.name}** ({size_mb:.2f} MB)")

        temp_dir = Path("data/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_p = temp_dir / excel_file.name
        temp_p.write_bytes(file_bytes)

        extractor = ExcelExtractor()
        sheet_names = extractor.inspect_sheets(temp_p)

        col_sh, col_comp = st.columns(2)
        with col_sh:
            selected_sheet = st.selectbox("Select Worksheet to Analyze", sheet_names)
        with col_comp:
            company_name_excel = st.text_input("Company Name", value="Apex Technologies", key="excel_company")

        xl_df = pd.read_excel(temp_p, sheet_name=selected_sheet)
        st.markdown(f"**Worksheet Preview ({selected_sheet}):** {len(xl_df)} rows × {len(xl_df.columns)} columns")
        st.dataframe(xl_df.head(8), use_container_width=True)

        if st.button("🚀 Ingest & Index Excel Worksheet", type="primary", key="btn_excel_ingest"):
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def update_progress_excel(msg: str, pct: float):
                progress_bar.progress(pct)
                status_text.markdown(f"**Status:** {msg}")

            try:
                st.session_state.analysis_cache = {}
                session, result = process_excel_document(
                    file_bytes=file_bytes,
                    file_name=excel_file.name,
                    sheet_name=selected_sheet,
                    company_name=company_name_excel,
                    progress_callback=update_progress_excel,
                )
                st.session_state.document_session = session
                st.session_state.selected_company = company_name_excel
                st.session_state.all_records = list(result.financial_records)

                st.success(f"✅ Excel worksheet **{selected_sheet}** indexed with {len(result.financial_records)} period records found!")
            except Exception as e:
                st.error(f"Excel extraction failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: CSV UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
with tab_csv:
    st.markdown("### 📑 Financial Datasets & Historical Time Series (CSV)")
    st.markdown("Accepts tabular CSVs, verifies data quality, and maps columns to revenue, expenses, profit, and balance sheet items.")

    csv_file = st.file_uploader(
        "Upload CSV financial dataset",
        type=["csv"],
        key="csv_uploader"
    )

    if csv_file is not None:
        file_bytes = csv_file.read()
        import io
        csv_df = pd.read_csv(io.BytesIO(file_bytes))

        st.markdown(f"**Dataset Preview:** {len(csv_df)} rows × {len(csv_df.columns)} columns")
        st.dataframe(csv_df.head(6), use_container_width=True)

        col_cname, col_btn = st.columns([2, 1])
        with col_cname:
            csv_company = st.text_input("Default Company Name", value="Apex Technologies", key="csv_company")

        from src.ingestion.csv_extractor import CSVExtractor
        csv_ext = CSVExtractor()
        auto_map = csv_ext.auto_detect_columns(csv_df)

        with st.expander("🛠️ Review Detected Column Mappings", expanded=False):
            st.json(auto_map)

        if st.button("🚀 Ingest & Index CSV Dataset", type="primary", key="btn_csv_ingest"):
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def update_progress_csv(msg: str, pct: float):
                progress_bar.progress(pct)
                status_text.markdown(f"**Status:** {msg}")

            try:
                st.session_state.analysis_cache = {}
                session, csv_res = process_csv_document(
                    file_bytes=file_bytes,
                    file_name=csv_file.name,
                    column_mapping=auto_map,
                    company_name=csv_company,
                    progress_callback=update_progress_csv,
                )
                st.session_state.document_session = session
                st.session_state.selected_company = csv_company
                st.session_state.all_records = list(csv_res.financial_records)

                st.success(f"✅ CSV successfully validated! Ingested {len(csv_res.financial_records)} period records.")
                if csv_res.validation.warnings:
                    for w in csv_res.validation.warnings:
                        st.warning(f"Quality notice: {w}")
            except Exception as e:
                st.error(f"CSV ingestion error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: IMAGE OCR UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
with tab_img:
    st.markdown("### 🖼️ Financial Statement Images (PNG, JPG, JPEG)")
    st.markdown("Extract text and financial figures from scanned balance sheets or income statements using OCR.")

    ocr_checker = ImageOCRExtractor()
    ocr_avail = ocr_checker.is_ocr_available()
    if not ocr_avail:
        st.markdown(
            """
            <div class="callout-box" style="background:#FEF7E0; border-left-color:#D99020; color:#B06000;">
                <b>OCR Notice:</b> The Python OCR bridge is ready. When Tesseract OCR is installed on your system PATH, 
                image statement text extraction is automatic. You can also view image previews and enter metrics directly in Tab 5.
            </div>
            """,
            unsafe_allow_html=True,
        )

    img_file = st.file_uploader(
        "Upload image of financial statement",
        type=["png", "jpg", "jpeg"],
        key="image_uploader"
    )

    if img_file is not None:
        img_bytes = img_file.read()
        col_img_view, col_img_meta = st.columns([1, 1])
        with col_img_view:
            st.image(img_bytes, caption=img_file.name, use_container_width=True)

        with col_img_meta:
            img_company = st.text_input("Company Name", value="Apex Technologies", key="img_comp")
            img_period = st.text_input("Reporting Period", value="FY2023", key="img_period")

            if st.button("🔍 Extract Text & Metrics via OCR", type="primary", key="btn_img_ocr"):
                with st.spinner("Processing image via OCR engine…"):
                    try:
                        session, ocr_res = process_image_document(
                            file_bytes=img_bytes,
                            file_name=img_file.name,
                            company_name=img_company,
                            reporting_period=img_period,
                        )
                        if session:
                            st.session_state.analysis_cache = {}
                            st.session_state.document_session = session
                            st.session_state.selected_company = img_company
                            st.session_state.selected_period = img_period
                            if ocr_res and ocr_res.financial_record:
                                st.session_state.all_records = [ocr_res.financial_record]
                            st.success(f"✅ Image statement successfully processed! OCR Confidence: {ocr_res.confidence_score:.0%}")
                        elif ocr_res:
                            st.info(ocr_res.extracted_text)
                    except Exception as e:
                        st.error(f"Image extraction error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: MANUAL FINANCIAL DATA ENTRY
# ─────────────────────────────────────────────────────────────────────────────
with tab_manual:
    st.markdown("### ✍️ Manual Financial Statement Data Entry")
    st.markdown("Input audited metrics directly. Includes mathematical validation and balance sheet identity checks.")

    with st.form("manual_entry_form"):
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            m_company = st.text_input("Company Name *", value="Apex Technologies")
        with col_m2:
            m_period = st.text_input("Reporting Period *", value="FY2023")
        with col_m3:
            m_currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "INR", "JPY"])
        with col_m4:
            m_unit = st.selectbox("Reporting Unit", ["millions", "billions", "thousands", "raw"])

        st.markdown("#### 1. Income Statement Line Items")
        col_i1, col_i2, col_i3, col_i4 = st.columns(4)
        with col_i1:
            m_revenue = st.number_input("Total Revenue ($M)", value=124.8, step=1.0)
        with col_i2:
            m_cogs = st.number_input("Cost of Goods Sold (COGS) ($M)", value=50.5, step=1.0)
        with col_i3:
            m_opex = st.number_input("Operating Expenses ($M)", value=51.2, step=1.0)
        with col_i4:
            m_net_income = st.number_input("Net Income / Profit ($M)", value=17.06, step=1.0)

        st.markdown("#### 2. Balance Sheet Line Items")
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1:
            m_assets = st.number_input("Total Assets ($M)", value=145.0, step=1.0)
        with col_b2:
            m_curr_assets = st.number_input("Current Assets ($M)", value=64.4, step=1.0)
        with col_b3:
            m_cash = st.number_input("Cash & Cash Equivalents ($M)", value=28.2, step=1.0)
        with col_b4:
            m_inventory = st.number_input("Inventory ($M)", value=14.2, step=1.0)

        col_b5, col_b6, col_b7, col_b8 = st.columns(4)
        with col_b5:
            m_liab = st.number_input("Total Liabilities ($M)", value=61.0, step=1.0)
        with col_b6:
            m_curr_liab = st.number_input("Current Liabilities ($M)", value=35.6, step=1.0)
        with col_b7:
            m_debt = st.number_input("Total Debt ($M)", value=30.4, step=1.0)
        with col_b8:
            m_equity = st.number_input("Shareholders' Equity ($M)", value=84.0, step=1.0)

        st.markdown("#### 3. Cash Flow")
        m_cash_flow = st.number_input("Operating Cash Flow ($M)", value=26.4, step=1.0)

        submit_manual = st.form_submit_button("🚀 Submit & Ingest Financial Record", type="primary")

    if submit_manual:
        from src.ingestion.manual_entry import ManualDataEntryManager
        manager = ManualDataEntryManager()
        raw_dict = {
            "company_name": m_company,
            "reporting_period": m_period,
            "currency": m_currency,
            "scale": m_unit,
            "revenue": m_revenue,
            "cost_of_goods_sold": m_cogs,
            "operating_expenses": m_opex,
            "net_income": m_net_income,
            "total_assets": m_assets,
            "current_assets": m_curr_assets,
            "cash_and_equivalents": m_cash,
            "inventory": m_inventory,
            "total_liabilities": m_liab,
            "current_liabilities": m_curr_liab,
            "total_debt": m_debt,
            "total_equity": m_equity,
            "operating_cash_flow": m_cash_flow,
        }
        record, validation = manager.create_record_from_form(raw_dict)
        if record:
            st.session_state.analysis_cache = {}
            session = process_manual_financial_record(record)
            st.session_state.document_session = session
            st.session_state.selected_company = m_company
            st.session_state.selected_period = m_period
            st.session_state.all_records = [record]
            st.success(f"✅ Record for **{m_company}** ({m_period}) ingested successfully!")
            if validation.warnings:
                for w in validation.warnings:
                    st.warning(f"Validation note: {w}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6: COMPARE MULTIPLE REPORTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_compare:
    st.markdown("### 🔄 Cross-Period & Peer Financial Comparison")
    st.markdown("Compare performance across multiple ingested statements or period records.")

    records = st.session_state.get("all_records", [])
    if len(records) >= 2:
        all_comps = sorted(list(set(r.company_name for r in records if getattr(r, "company_name", None))))
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            sel_comp = st.selectbox("Company to Analyze", all_comps, index=0)
        with col_c2:
            st.caption(f"Comparing {len([r for r in records if r.company_name == sel_comp])} reporting periods for {sel_comp}.")

        comparator = FinancialComparator()
        comp_res = comparator.compare_periods(records, target_company=sel_comp)
        if comp_res.has_comparable_data:
            st.dataframe(comp_res.to_dataframe(), use_container_width=True)
            if comp_res.summary_insights:
                st.markdown("#### Key Analytical Observations:")
                for ins in comp_res.summary_insights:
                    st.markdown(f"- {ins}")
        else:
            st.warning("Selected records do not share comparable reporting periods or metrics.")
    else:
        st.info("Ingest at least two financial records or a multi-year CSV/Excel model to view automated comparative matrices.")
        if st.button("📊 Load Multi-Year Comparison Sample (Apex Technologies FY2020–FY2023)", key="btn_load_sample_csv_comp"):
            sample_csv = Path("sample_inputs/Apex_Technologies_Financial_Metrics_FY2020_FY2023.csv")
            if sample_csv.exists():
                session, csv_res = process_csv_document(
                    file_bytes=sample_csv.read_bytes(),
                    file_name=sample_csv.name,
                    company_name="Apex Technologies",
                )
                st.session_state.document_session = session
                st.session_state.all_records = list(csv_res.financial_records)
                st.session_state.selected_company = "Apex Technologies"
                st.rerun()

# ── Standard Navigation Button at Bottom ─────────────────────────────────────
render_page_navigation(
    next_page="pages/2_Financial_Analysis.py",
    next_label="Financial Analysis",
)
