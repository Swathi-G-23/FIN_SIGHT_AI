"""
FIN SIGHT AI - Page 3: Conversational Financial Intelligence
Multi-agent RAG conversational interface with dynamic query answering,
context-aware follow-up reasoning, and grounded 6-part financial recommendations.
"""
from pathlib import Path
import time
import uuid
import streamlit as st

st.set_page_config(
    page_title="Financial Chatbot | FIN SIGHT AI",
    page_icon="💬",
    layout="wide"
)

from src.ui.theme import (
    apply_light_theme,
    render_sidebar_brand,
    render_page_header,
    render_page_navigation,
    render_empty_state,
)
apply_light_theme()
render_sidebar_brand()

render_page_header(
    title="Conversational Financial Intelligence",
    subtitle="Ask specific inquiries regarding revenues, margins, ratios, risks, what-if simulations, or strategic recommendations."
)

doc_session = st.session_state.get("document_session")
if doc_session is None:
    render_empty_state(
        title="No Financial Report Loaded",
        description="Please ingest a financial report, spreadsheet, or load the pre-bundled audited sample report to begin querying.",
        action_label="Go to Ingestion Portal",
        action_page="pages/1_Upload_Report.py"
    )
    st.markdown("<div style='text-align: center; margin-top: 10px;'>", unsafe_allow_html=True)
    if st.button("📄 Load Sample Report (Apex Technologies FY2023)", key="btn_sample_chat"):
        sample_pdf = Path("sample_financial_report.pdf")
        if not sample_pdf.exists():
            sample_pdf = Path("sample_inputs/Apex_Technologies_FY2023_Annual_Report.pdf")
        if sample_pdf.exists():
            with st.spinner("Indexing sample annual report..."):
                from src.utils.session_manager import process_document
                session = process_document(pdf_bytes=sample_pdf.read_bytes(), file_name=sample_pdf.name)
                st.session_state.document_session = session
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

st.caption(f"📄 Active Source: **{doc_session.file_name}** | Chunks: **{doc_session.chunk_count}** | Pages/Sheets: **{doc_session.page_count}**")

# ── Sidebar: Quick-Action Inquiries & Context Controls ───────────────────────
with st.sidebar:
    st.markdown("### 💡 Quick-Action Inquiries")
    quick_queries = [
        "What is the company's total revenue and gross profit?",
        "What was the net profit and profit margin for the year?",
        "What is the current ratio and liquidity buffer?",
        "What are the major financial risks and interest rate exposures?",
        "Compare revenue with the previous year.",
        "What happens if operating expenses increase by 10%?",
        "How can the company improve its profit margin?",
        "What actions could improve working capital?",
    ]
    for q in quick_queries:
        if st.button(q, key=f"ex_{hash(q)}", use_container_width=True):
            st.session_state["pending_question"] = q
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Reset Chat History", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_workflow_state = None
        st.session_state.pop("last_chat_metric", None)
        st.rerun()

# ── Display Chat History ─────────────────────────────────────────────────────
chat_history = st.session_state.get("chat_history", [])
for msg in chat_history:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("evidence"):
            with st.expander("📄 Source Attribution & Grounded Evidence"):
                for ev in msg["evidence"]:
                    pages = ev.get("pages", [])
                    page_ref = f"Page {', '.join(str(p) for p in pages)}" if pages else "Disclosures"
                    st.markdown(f"**Source: {page_ref}**")
                    st.caption(ev.get("text", "")[:320])
                    st.divider()

# ── Input Handling & Multi-Turn Context Tracking ─────────────────────────────
if "pending_question" in st.session_state:
    pending = st.session_state.pop("pending_question")
else:
    pending = None

user_input = st.chat_input("Ask a question about financial metrics, ratios, simulations, or recommendations…") or pending

if user_input:
    # Context resolution for follow-up questions
    effective_query = user_input.strip()
    last_metric = st.session_state.get("last_chat_metric")

    # If follow-up like "What about net profit?", track new metric
    if "net profit" in effective_query.lower() or "net income" in effective_query.lower():
        st.session_state["last_chat_metric"] = "net profit"
    elif "revenue" in effective_query.lower():
        st.session_state["last_chat_metric"] = "revenue"
    elif "current ratio" in effective_query.lower():
        st.session_state["last_chat_metric"] = "current ratio"
    elif "compare it with the previous year" in effective_query.lower() and last_metric:
        effective_query = f"Compare {last_metric} with the previous year"

    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🤖 Coordinating multi-agent financial workflow…"):
            try:
                from src.graph.workflow import run_query
                from src.graph.router import classify_intent

                intent = classify_intent(effective_query)
                start_time = time.time()

                final_state = run_query(
                    query=effective_query,
                    document_id=doc_session.document_id,
                    retriever=doc_session.retriever,
                    extracted_metrics_raw=doc_session.extracted_metrics_raw,
                    session_id=str(uuid.uuid4()),
                    company_name=getattr(doc_session, "company_name", ""),
                    reporting_period=getattr(doc_session, "reporting_period", "FY2023"),
                )

                elapsed = time.time() - start_time
                st.session_state.last_workflow_state = final_state

                answer = final_state.get("final_answer", "⚠️ No response was generated.")
                evidence = final_state.get("supporting_evidence", [])
                errors = final_state.get("errors", [])

                st.markdown(answer)

                if errors:
                    with st.expander("⚠️ Processing Observations"):
                        for err in errors:
                            st.warning(err)

                if evidence:
                    with st.expander("📄 Grounded Source Evidence"):
                        for ev in evidence:
                            pages = ev.get("pages", [])
                            page_ref = f"Page {', '.join(str(p) for p in pages)}" if pages else "Section reference"
                            st.markdown(f"**Source: {page_ref}**")
                            st.caption(ev.get("text", "")[:350])
                            st.divider()

                st.caption(
                    f"⏱️ Response Latency: {elapsed:.2f}s | "
                    f"Intent Classification: `{intent.value}` | "
                    f"Evidence Chunks: {len(final_state.get('retrieved_chunks', []))}"
                )

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "evidence": evidence,
                })

            except Exception as exc:
                err_str = f"⚠️ Analysis failed: {exc}"
                st.error(err_str)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": err_str,
                    "evidence": [],
                })

# ── Standard Page Navigation ─────────────────────────────────────────────────
render_page_navigation(
    prev_page="pages/2_Financial_Analysis.py",
    next_page="pages/4_Scenario_Simulator.py",
    prev_label="Financial Analysis",
    next_label="Scenario Simulator",
)
