"""
FIN SIGHT AI - Page 9: Dedicated Performance & Observability Dashboard
Comprehensive Application Performance Monitoring (APM), AI Multi-Agent Telemetry,
Empirical Hardware Utilization, Bottleneck Detection, and LangSmith Integration.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Performance Monitoring | FIN SIGHT AI",
    page_icon="⚡",
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

import importlib
import src.monitoring.performance as perf_module
import src.monitoring.agent_telemetry as telemetry_module

perf_module = importlib.reload(perf_module)
telemetry_module = importlib.reload(telemetry_module)

PerformanceMonitor = perf_module.PerformanceMonitor
agent_telemetry_store = telemetry_module.agent_telemetry_store

# Ensure singleton has latest methods even if Streamlit cached previous module
if PerformanceMonitor._instance is not None and not hasattr(PerformanceMonitor._instance, "get_application_health"):
    PerformanceMonitor._instance = None

monitor = PerformanceMonitor()

# ── 1. Top Controls Bar: Refresh & Action Buttons ─────────────────────────────
now_str = datetime.now().strftime("%H:%M:%S")
if "last_refresh_time" not in st.session_state:
    st.session_state["last_refresh_time"] = now_str

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2, 1.1, 1.5, 1.3])

with ctrl_col1:
    time_window_label = st.selectbox(
        "⏱️ Telemetry Time Window:",
        ["Last 1 Hour", "Last 24 Hours", "Last 7 Days", "All Time"],
        index=3,
        help="Filter performance metrics and agent traces by recency."
    )

window_map = {
    "Last 1 Hour": 1,
    "Last 24 Hours": 24,
    "Last 7 Days": 168,
    "All Time": None,
}
selected_hours = window_map[time_window_label]

with ctrl_col2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh", use_container_width=True, help="Reload latest metrics from database"):
        st.session_state["last_refresh_time"] = datetime.now().strftime("%H:%M:%S")
        st.toast(f"🔄 Telemetry refreshed at {st.session_state['last_refresh_time']}!")
        st.rerun()

with ctrl_col3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("🤖 Simulate Agent Run", type="primary", use_container_width=True, help="Simulate a live multi-agent execution pipeline to observe metrics update in real-time"):
        import time, uuid, random
        from src.monitoring.agent_telemetry import AgentExecutionRecord

        run_id = f"sim_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now().isoformat()

        # Realistic agent latencies
        dur_router = round(random.uniform(0.012, 0.028), 3)
        dur_research = round(random.uniform(0.085, 0.175), 3)
        dur_ratio = round(random.uniform(0.045, 0.088), 3)
        dur_val = round(random.uniform(0.022, 0.048), 3)
        dur_report = round(random.uniform(0.065, 0.135), 3)
        total_dur = round(dur_router + dur_research + dur_ratio + dur_val + dur_report, 3)

        # Log active agents
        for name, d, inp, out in [
            ("router", dur_router, "Classified query intent as numerical calculation", "Route to research -> ratio"),
            ("research", dur_research, "Retrieved 4 chunks from income statement", "Found revenue, gross profit, net income"),
            ("ratio", dur_ratio, "Calculated Gross Margin, Net Margin, Operating Margin", "Ratios calculated successfully"),
            ("validation", dur_val, "Audited 3 financial formulas against reported numbers", "Passed: 100% claims verified"),
            ("report", dur_report, "Compiled verified financial briefing", "Generated 4-paragraph executive summary"),
        ]:
            agent_telemetry_store.record_agent_execution(AgentExecutionRecord(
                run_id=run_id, agent_name=name, start_time=now_iso, end_time=now_iso,
                duration_seconds=d, status="completed", query="Simulated Query: Margin Analysis",
                intent="numerical", input_summary=inp, output_summary=out, validation_passed=True,
                claims_count=3, supported_claims_count=3, evidence_coverage_pct=100.0,
            ))

        # Log skipped agent (risk agent skipped for numerical intent)
        agent_telemetry_store.record_skipped_agent(
            run_id=run_id, agent_name="risk",
            reason="Intent 'numerical' focused on profitability margins; risk analysis bypassed.",
            query="Simulated Query: Margin Analysis"
        )

        # Log application operation in APM
        monitor.record_operation(
            operation_type="chat_query",
            operation_name="Simulated Multi-Agent Run: Margin Analysis",
            duration_seconds=total_dur,
            status="success",
            details={"run_id": run_id, "simulated": True, "agents_count": 5},
        )

        st.session_state["last_refresh_time"] = datetime.now().strftime("%H:%M:%S")
        st.session_state["last_action_banner"] = f"⚡ **Simulated Multi-Agent Workflow ({run_id}) Completed in {total_dur}s!** Agent metrics, charts, and execution traces have updated."
        st.toast("⚡ Multi-Agent run completed & logged!")
        st.rerun()

with ctrl_col4:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("⚠️ Test Error Log", use_container_width=True, help="Simulate a diagnostic failure to verify error logging"):
        monitor.record_operation(
            operation_type="diagnostic_test",
            operation_name="Simulated Ingestion Timeout",
            duration_seconds=1.45,
            status="failed",
            error_message="Simulated ConnectionResetError during PDF stream parsing (test event)",
            details={"test": True},
        )
        st.session_state["last_refresh_time"] = datetime.now().strftime("%H:%M:%S")
        st.session_state["last_action_banner"] = "⚠️ **Simulated Failure Event Logged!** Check **Tab 4 (Error Logs & Failures)** to inspect the recorded failure trace."
        st.toast("⚠️ Test failure event logged!")
        st.rerun()

# Display refresh status badge and action banners
status_col, time_col = st.columns([3, 1])
with time_col:
    st.caption(f"🕒 *Last Refreshed: {st.session_state.get('last_refresh_time', now_str)}*")

if "last_action_banner" in st.session_state:
    st.success(st.session_state.pop("last_action_banner"))

# ── 2. Data Retrieval ────────────────────────────────────────────────────────
health = monitor.get_application_health()
summary = monitor.get_performance_summary(hours=selected_hours)
agent_metrics = agent_telemetry_store.get_agent_metrics(hours=selected_hours)
bottleneck_info = agent_telemetry_store.get_bottleneck_agent(hours=selected_hours)
sys_res = monitor.get_system_resources()
recent_records = agent_telemetry_store.get_recent_executions(limit=40, hours=selected_hours)
op_breakdown = monitor.get_operation_breakdown(hours=selected_hours)
latency_hist = monitor.get_latency_history(hours=selected_hours, limit=60)
error_logs = monitor.get_error_logs(hours=selected_hours, limit=30)
langsmith_status = monitor.get_langsmith_status()

# ── 3. Executive KPI Metric Cards (Row 1) ────────────────────────────────────
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

with kpi1:
    st.metric(
        "Application Health",
        health["badge"],
        delta=f"Uptime: {health['uptime_formatted']}",
        delta_color="normal",
        help=health["description"]
    )

with kpi2:
    tot_reqs = summary["total_requests"]
    succ_rate = summary["success_rate_pct"]
    st.metric(
        "Total Operations",
        f"{tot_reqs:,}",
        delta=f"{succ_rate:.1f}% Success Rate",
        delta_color="normal" if succ_rate >= 95.0 else "inverse",
        help=f"Successful: {summary['successful_requests']}, Failed: {summary['failed_requests']}"
    )

with kpi3:
    avg_resp = summary["avg_response_time"]
    max_resp = summary["max_response_time"]
    st.metric(
        "Avg Response Time",
        f"{avg_resp:.2f}s" if tot_reqs > 0 else "N/A",
        delta=f"Max: {max_resp:.2f}s" if tot_reqs > 0 else None,
        delta_color="inverse",
        help="Average execution duration across all application requests."
    )

with kpi4:
    if bottleneck_info:
        b_name = bottleneck_info["bottleneck_agent"].replace("_", " ").title()
        b_share = bottleneck_info["share_pct"]
        st.metric(
            "Primary Bottleneck",
            b_name,
            delta=f"{b_share}% of Agent Latency",
            delta_color="inverse",
            help="Agent specialist accounting for the highest cumulative execution duration."
        )
    else:
        st.metric(
            "Primary Bottleneck",
            "None Detected",
            delta="Awaiting Runs",
            delta_color="off",
            help="No bottleneck identified in the selected time window."
        )

with kpi5:
    cpu_p = sys_res["process_cpu_percent"]
    mem_mb = sys_res["process_memory_mb"]
    st.metric(
        "Process Memory / CPU",
        f"{mem_mb:.1f} MB",
        delta=f"CPU: {cpu_p:.1f}%",
        delta_color="off",
        help="Resident Set Size (RAM) and CPU percentage utilized by the Python process."
    )

with kpi6:
    st.metric(
        "LangSmith Tracing",
        "Active" if langsmith_status["enabled"] else "Standby (Local)",
        delta=langsmith_status["project"] if langsmith_status["enabled"] else "Embedded APM",
        delta_color="normal" if langsmith_status["enabled"] else "off",
        help="LangSmith LangGraph tracing status configured in .env."
    )

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
st.markdown("---")

# ── 4. In-Depth Monitoring Tabs ──────────────────────────────────────────────
tab_agents, tab_pipeline, tab_hardware, tab_errors, tab_tools, tab_bench = st.tabs([
    "🤖 AI Multi-Agent Observability",
    "⏱️ Application & Pipeline Latency",
    "💻 System Hardware Utilization",
    "⚠️ Error Logs & Failures",
    "🛠️ Tool Selection & Architecture",
    "⚡ Synthetic Scaling Benchmark",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: AI Multi-Agent Observability
# ─────────────────────────────────────────────────────────────────────────────
with tab_agents:
    st.markdown("### 🤖 Multi-Agent Execution Telemetry")
    st.caption("Empirical measurements for all six financial intelligence agents and intent routing.")

    # Bottleneck Callout Banner
    if bottleneck_info:
        st.warning(
            f"⚠️ **Primary Pipeline Bottleneck:** The **{bottleneck_info['bottleneck_agent'].upper()}** specialist "
            f"accounts for **{bottleneck_info['share_pct']}%** of total multi-agent execution duration "
            f"(Avg: **{bottleneck_info['avg_duration_seconds']:.2f}s**, P95: **{bottleneck_info['p95_duration_seconds']:.2f}s**, "
            f"across {bottleneck_info['total_executions']} executions). "
            f"Optimization Recommendation: Leverage cached embeddings or adjust retrieval top-k."
        )
    else:
        st.info("ℹ️ Execute a query in **3_Financial_Chat** to record live multi-agent execution telemetry.")

    # Agent Metrics Table
    if agent_metrics:
        agent_table_rows = []
        for m in agent_metrics:
            agent_table_rows.append({
                "Agent Specialist": m.agent_name.replace("_", " ").title(),
                "Total Runs": m.total_executions,
                "Completed": m.successful_executions,
                "Failed": m.failed_executions,
                "Skipped": m.skipped_executions,
                "Success Rate": f"{m.success_rate_pct:.1f}%",
                "Avg Latency (s)": round(m.avg_duration_seconds, 3),
                "Median (s)": round(m.median_duration_seconds, 3),
                "P95 Latency (s)": round(m.p95_duration_seconds, 3),
                "Validation Pass Rate": f"{m.validation_pass_rate_pct:.1f}%",
                "Last Status": m.last_status.upper(),
            })
        df_agents = pd.DataFrame(agent_table_rows)
        st.dataframe(df_agents, use_container_width=True)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            # Latency Bar Chart
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=[m.agent_name.replace("_", " ").title() for m in agent_metrics],
                y=[m.avg_duration_seconds for m in agent_metrics],
                name="Avg Duration (s)",
                marker_color="#1E3A8A",
            ))
            fig_bar.add_trace(go.Bar(
                x=[m.agent_name.replace("_", " ").title() for m in agent_metrics],
                y=[m.p95_duration_seconds for m in agent_metrics],
                name="P95 Duration (s)",
                marker_color="#D97706",
            ))
            fig_bar.update_layout(
                title="Agent Execution Latency (Average vs. P95)",
                barmode="group",
                height=320,
                margin=dict(l=35, r=35, t=40, b=40),
                xaxis_title="Agent Specialist",
                yaxis_title="Duration (seconds)",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_c2:
            # Execution Status Distribution
            tot_completed = sum(m.successful_executions for m in agent_metrics)
            tot_failed = sum(m.failed_executions for m in agent_metrics)
            tot_skipped = sum(m.skipped_executions for m in agent_metrics)

            fig_donut = go.Figure(data=[go.Pie(
                labels=["Completed", "Skipped", "Failed"],
                values=[tot_completed, tot_skipped, tot_failed],
                hole=0.45,
                marker=dict(colors=["#059669", "#64748B", "#DC2626"]),
            )])
            fig_donut.update_layout(
                title="Agent Execution Status Distribution",
                height=320,
                margin=dict(l=35, r=35, t=40, b=40),
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    # Recent Execution Logs
    if recent_records:
        st.markdown("#### 📜 Recent Multi-Agent Execution Traces")
        trace_rows = []
        for r in recent_records:
            st_time = str(r.get("start_time", ""))[:19].replace("T", " ")
            trace_rows.append({
                "Timestamp": st_time,
                "Run ID": str(r.get("run_id", ""))[:12],
                "Agent": str(r.get("agent_name", "")).replace("_", " ").title(),
                "Duration (s)": round(float(r.get("duration_seconds", 0.0)), 3),
                "Status": str(r.get("status", "")).upper(),
                "Intent": str(r.get("intent", "N/A")),
                "Claims Evaluated": r.get("claims_count", 0),
                "Validated": "✅ Pass" if r.get("validation_passed") else "⚠️ Flagged",
                "Summary / Reason": (r.get("input_summary") or r.get("output_summary") or "")[:120],
            })
        st.dataframe(pd.DataFrame(trace_rows), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Application & Pipeline Latency
# ─────────────────────────────────────────────────────────────────────────────
with tab_pipeline:
    st.markdown("### ⏱️ Application Performance Monitoring (APM)")
    st.caption("Chronological latency profiling across document ingestion, extraction, indexing, querying, and report generation.")

    # Chronological Latency Trend Chart
    if latency_hist:
        df_lat = pd.DataFrame(latency_hist)
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=[str(t)[:19].replace("T", " ") for t in df_lat["timestamp"]],
            y=df_lat["duration_seconds"],
            mode="lines+markers",
            name="Latency (s)",
            line=dict(color="#2563EB", width=2),
            marker=dict(
                size=7,
                color=["#DC2626" if s == "failed" else "#10B981" for s in df_lat["status"]],
            ),
            text=[f"{r['operation_name']} ({r['status']})" for r in latency_hist],
        ))
        fig_trend.update_layout(
            title="Chronological Operation Latencies (Recent 60 Events)",
            height=320,
            margin=dict(l=35, r=35, t=40, b=40),
            xaxis_title="Timestamp",
            yaxis_title="Duration (seconds)",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # Operations Breakdown Table
    if op_breakdown:
        st.markdown("#### 📊 Operation Type Performance Breakdown")
        df_ops = pd.DataFrame(op_breakdown)
        df_ops.columns = ["Operation Type", "Total Executions", "Avg Latency (s)", "Max Latency (s)", "Failures", "Success Rate (%)"]
        st.dataframe(df_ops, use_container_width=True)
    else:
        st.info("No application operations recorded in the selected time window.")

    # Active Document Telemetry
    doc_session = st.session_state.get("document_session")
    if doc_session:
        st.markdown("#### 📄 Active Ingested Document Latency Profile")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            st.metric("Document", doc_session.file_name[:26])
        with col_d2:
            st.metric("Total Ingestion Latency", f"{doc_session.processing_time_seconds:.2f}s")
        with col_d3:
            st.metric("Sections / Chunks Created", doc_session.chunk_count)
        with col_d4:
            st.metric("Financial Metrics Extracted", doc_session.metrics_found)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: System Hardware Utilization
# ─────────────────────────────────────────────────────────────────────────────
with tab_hardware:
    st.markdown("### 💻 Operating System & Process Hardware Utilization")
    st.caption("Live empirical metrics sampled directly from the local operating system via psutil.")

    h_col1, h_col2, h_col3 = st.columns(3)

    with h_col1:
        # Gauge Process CPU
        cpu_val = sys_res["process_cpu_percent"]
        fig_cpu = go.Figure(go.Indicator(
            mode="gauge+number",
            value=cpu_val,
            title={"text": "Process CPU Load (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#1E3A8A"},
                "steps": [
                    {"range": [0, 50], "color": "#D1FAE5"},
                    {"range": [50, 80], "color": "#FEF3C7"},
                    {"range": [80, 100], "color": "#FEE2E2"},
                ],
            }
        ))
        fig_cpu.update_layout(height=260, margin=dict(l=25, r=25, t=30, b=20))
        st.plotly_chart(fig_cpu, use_container_width=True)

    with h_col2:
        # Gauge Host RAM Percent
        mem_pct = sys_res["system_memory_used_percent"]
        fig_mem = go.Figure(go.Indicator(
            mode="gauge+number",
            value=mem_pct,
            title={"text": "Host RAM Used (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#059669"},
                "steps": [
                    {"range": [0, 60], "color": "#D1FAE5"},
                    {"range": [60, 85], "color": "#FEF3C7"},
                    {"range": [85, 100], "color": "#FEE2E2"},
                ],
            }
        ))
        fig_mem.update_layout(height=260, margin=dict(l=25, r=25, t=30, b=20))
        st.plotly_chart(fig_mem, use_container_width=True)

    with h_col3:
        st.markdown("#### 🖥️ Server Specifications")
        st.markdown(f"- **Process Memory (RSS):** `{sys_res['process_memory_mb']:.1f} MB`")
        st.markdown(f"- **System Memory Total:** `{sys_res['system_total_memory_gb']:.1f} GB`")
        st.markdown(f"- **System Memory Used:** `{sys_res['system_memory_used_gb']:.1f} GB`")
        st.markdown(f"- **Logical CPU Cores:** `{sys_res['cpu_count_logical']}`")
        st.markdown(f"- **Physical CPU Cores:** `{sys_res['cpu_count_physical']}`")
        st.markdown(f"- **Telemetry Database:** `data/agent_telemetry.db` (Persistent SQLite)")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: Error Logs & Failures
# ─────────────────────────────────────────────────────────────────────────────
with tab_errors:
    st.markdown("### ⚠️ Application Error Logs & Failure Analysis")
    st.caption("Centralized audit of operation failures, agent exceptions, and error messages.")

    if error_logs:
        st.error(f"Found **{len(error_logs)}** recorded failure events in the selected time window.")
        err_table_rows = []
        for e in error_logs:
            err_table_rows.append({
                "Timestamp": str(e.get("timestamp", ""))[:19].replace("T", " "),
                "Operation Type": e.get("operation_type", "general"),
                "Operation Name": e.get("operation_name", "N/A"),
                "Duration (s)": round(float(e.get("duration_seconds", 0.0)), 3),
                "Error Message": e.get("error_message", "Unknown error"),
            })
        st.dataframe(pd.DataFrame(err_table_rows), use_container_width=True)
    else:
        st.success("🎉 **Zero failures recorded!** All operations in the selected time window executed successfully.")

    st.markdown("---")
    st.markdown("#### 💡 Troubleshooting Guidelines")
    st.markdown("""
    - **PDF Extraction / OCR Errors:** Verify that uploaded documents are valid PDF/image files and that Tesseract OCR is installed on the host.
    - **FAISS Indexing Errors:** Ensure sufficient RAM is allocated. Vector indices require ~1 MB per 500 chunks.
    - **Timeout / Slow Queries:** Check if large document size (>100 pages) is causing excessive BM25 search latency.
    """)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: Tool Selection & Architecture
# ─────────────────────────────────────────────────────────────────────────────
with tab_tools:
    st.markdown("### 🛠️ Observability Tool Selection & Architectural Rationale")
    
    col_t1, col_t2 = st.columns([3, 2])

    with col_t1:
        st.markdown("""
        #### Tool Architecture Decision
        For **FIN SIGHT AI**, a **hybrid monitoring architecture** was selected:

        1. **Embedded SQLite + psutil APM (Primary, Active by Default)**
           - **Why it fits:** Zero-overhead, zero-credential, local-first performance monitoring.
           - **Benefits:** No requirement to deploy heavy Docker containers (Prometheus + Grafana) or incur SaaS cloud costs. All metrics survive application restarts via persistent SQLite storage in `data/agent_telemetry.db`.
           - **Capabilities:** Response times, success/fail counts, agent bottlenecks, hardware RSS memory, CPU percent, and failure logging.

        2. **Native LangSmith Integration (Opt-in for Deep LLM Tracing)**
           - **Why it fits:** FIN SIGHT AI is built on **LangChain and LangGraph**. LangSmith provides native, code-free distributed tracing of conditional agent transitions, token counts, and LLM reasoning steps.
           - **Activation:** Simply populate `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in your `.env` file. The application automatically sends traces to LangSmith without any code modification.

        3. **Why Prometheus / MLflow were not forced:**
           - *Prometheus + Grafana* requires external container infrastructure unsuitable for local desktop evaluation.
           - *MLflow* is tailored for offline model weight training/experiment comparison, whereas FIN SIGHT AI is a production multi-agent RAG inference system.
        """)

    with col_t2:
        st.markdown("#### 🔗 LangSmith Connection Status")
        if langsmith_status["enabled"]:
            st.success(f"✅ **LangSmith Cloud Tracing is ACTIVE**")
            st.markdown(f"- **Project:** `{langsmith_status['project']}`")
            st.markdown(f"- **Endpoint:** `{langsmith_status['endpoint']}`")
        else:
            st.info("ℹ️ **LangSmith is currently in STANDBY (Local APM active)**")
            st.markdown("""
            To enable cloud agent tracing:
            ```bash
            # Add to your .env file:
            LANGCHAIN_TRACING_V2=true
            LANGCHAIN_API_KEY="your-langsmith-key"
            LANGCHAIN_PROJECT="fin-sight-ai"
            ```
            Restart Streamlit and traces will stream directly to your LangSmith dashboard!
            """)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6: Synthetic Scaling Benchmark
# ─────────────────────────────────────────────────────────────────────────────
with tab_bench:
    st.markdown("### ⚡ Repeatable Document Scaling Benchmark")
    st.caption("Run reproducible synthetic stress tests to measure chunking and indexing latency under load.")

    col_b1, col_b2 = st.columns([1, 2])
    with col_b1:
        test_pages = st.selectbox("Benchmark Document Size (Pages):", [10, 25, 50, 100], index=1)
        run_bench = st.button("🚀 Run Scaling Benchmark", type="primary")

    with col_b2:
        if run_bench:
            with st.spinner(f"Simulating extraction & indexing of a {test_pages}-page corporate report..."):
                res = monitor.run_document_scaling_benchmark(page_counts=[test_pages])
                st.success(f"Benchmark finished: Processed {test_pages} pages in {res.get('total_duration', 0.8):.2f}s!")
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Chunks Generated", f"{res.get('chunk_count', 0)}")
                with m2:
                    st.metric("Ingestion & Indexing", f"{res.get('ingestion_time', 0.0):.3f}s")
                with m3:
                    st.metric("Retrieval Latency", f"{res.get('retrieval_latency_ms', 0.0):.1f} ms")

# ── Standard Page Navigation ─────────────────────────────────────────────────
render_page_navigation(
    prev_page="pages/8_Report_Generation.py",
    next_page="pages/10_Backup_Recovery.py",
    prev_label="Report Generation",
    next_label="Backup & Recovery",
)
