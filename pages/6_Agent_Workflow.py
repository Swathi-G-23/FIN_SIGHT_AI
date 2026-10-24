"""
FIN SIGHT AI - Page 6: LangGraph Agent Workflow Visualizer
Interactive execution graph displaying real-time agent routing, execution latencies,
and state transitions across the six specialized financial intelligence agents.
Displays actual execution outcomes (Completed, Skipped, or Failed) with zero permanent pending states.
"""
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="Agent Workflow | FIN SIGHT AI",
    page_icon="🔄",
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

from src.graph.state import AgentStatus

render_page_header(
    title="LangGraph Multi-Agent Orchestration Visualizer",
    subtitle="Live multi-agent execution map, conditional routing inspection, and latency profiling across all specialized agents."
)

STATUS_COLORS = {
    AgentStatus.COMPLETED: "#24865B",
    AgentStatus.RUNNING: "#D99020",
    AgentStatus.FAILED: "#C74440",
    AgentStatus.SKIPPED: "#94A3B8",
    AgentStatus.PENDING: "#CBD5E1",
}

STATUS_SYMBOLS = {
    AgentStatus.COMPLETED: "✅ Completed",
    AgentStatus.RUNNING: "⚡ Running",
    AgentStatus.FAILED: "❌ Failed",
    AgentStatus.SKIPPED: "⏭️ Skipped (Bypassed by router)",
    AgentStatus.PENDING: "⏳ Ready / Standby",
}

AGENT_META = {
    "router":     {"name": "Intent Router",     "icon": "🎯", "desc": "Classifies query intent (Numerical, Risk, Comparison, Simulation, Recommendation)"},
    "research":   {"name": "Research Agent",    "icon": "🔍", "desc": "Retrieves audited disclosures via FAISS + BM25 RRF fusion"},
    "ratio":      {"name": "Ratio Agent",       "icon": "🔢", "desc": "Calculates standardized financial ratios in verified Python"},
    "analysis":   {"name": "Analysis Agent",    "icon": "📊", "desc": "Synthesizes statement performance, margins, and trends"},
    "risk":       {"name": "Risk Agent",        "icon": "⚠️", "desc": "Detects liquidity, leverage, and solvency vulnerabilities"},
    "validation": {"name": "Validation Agent",  "icon": "✅", "desc": "Verifies arithmetic integrity and balance sheet identity"},
    "report":     {"name": "Report Agent",      "icon": "📋", "desc": "Assembles input-specific final answer with page citations"},
}

last_state = st.session_state.get("last_workflow_state")
agent_statuses = last_state.get("agent_statuses", {}) if last_state else {}
agent_timings = last_state.get("agent_timings", {}) if last_state else {}
agent_skip_reasons = last_state.get("agent_skip_reasons", {}) if last_state else {}

# ── Dynamic Pipeline Execution Map ───────────────────────────────────────────
st.markdown("### 🗺️ Dynamic Multi-Agent Execution Architecture")
st.caption("Green nodes executed during the last query; grey nodes were intentionally bypassed by conditional routing logic.")

node_x = [0.0, 1.5, 3.0, 3.0, 3.0, 4.5, 6.0]
node_y = [1.0, 1.0, 2.0, 1.0, 0.0, 1.0, 1.0]
node_keys = ["router", "research", "analysis", "ratio", "risk", "validation", "report"]

edge_x = []
edge_y = []
edges = [
    (0, 1), # Router -> Research
    (1, 2), # Research -> Analysis
    (1, 3), # Research -> Ratio
    (1, 4), # Research -> Risk
    (2, 5), # Analysis -> Validation
    (3, 5), # Ratio -> Validation
    (4, 5), # Risk -> Validation
    (5, 6), # Validation -> Report
]

for start_idx, end_idx in edges:
    edge_x.extend([node_x[start_idx], node_x[end_idx], None])
    edge_y.extend([node_y[start_idx], node_y[end_idx], None])

node_colors = []
hover_texts = []
for k in node_keys:
    st_val = agent_statuses.get(k, AgentStatus.PENDING)
    node_colors.append(STATUS_COLORS.get(st_val, "#CBD5E1"))
    timing = agent_timings.get(k)
    timing_str = f"{timing:.3f}s" if timing else "N/A"
    status_str = st_val.value.upper() if hasattr(st_val, "value") else str(st_val).upper()
    skip_reason = f"<br>Reason: {agent_skip_reasons[k]}" if k in agent_skip_reasons else ""
    hover_texts.append(f"<b>{AGENT_META[k]['name']}</b><br>Status: {status_str}<br>Latency: {timing_str}{skip_reason}")

fig_workflow = go.Figure()
fig_workflow.add_trace(
    go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(color="#CBD5E1", width=2.5),
        hoverinfo="none",
    )
)
fig_workflow.add_trace(
    go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(
            size=44,
            color=node_colors,
            line=dict(color="#17365D", width=2),
        ),
        text=[AGENT_META[k]["name"] for k in node_keys],
        textposition="top center",
        hovertext=hover_texts,
        hoverinfo="text",
    )
)
fig_workflow.update_layout(
    showlegend=False,
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    height=360,
    margin=dict(l=30, r=30, t=40, b=30),
)
st.plotly_chart(fig_workflow, use_container_width=True)

# ── Agent Execution Status Cards ─────────────────────────────────────────────
st.markdown("### 📋 Agent Status & Empirical Latencies")

cards_col1, cards_col2 = st.columns(2)

for i, (k, meta) in enumerate(AGENT_META.items()):
    col = cards_col1 if i % 2 == 0 else cards_col2
    with col:
        status = agent_statuses.get(k, AgentStatus.PENDING)
        timing = agent_timings.get(k)
        timing_str = f" · Latency: **{timing:.3f}s**" if timing else ""
        if status == AgentStatus.SKIPPED:
            badge_symbol = "⏭️ Skipped"
            reason_text = agent_skip_reasons.get(k, "Bypassed by router for this query intent")
            reason_html = f"<div style='font-size: 12px; color: #64748B; margin-top: 5px; font-style: italic;'><b>Route Notice:</b> {reason_text}</div>"
        else:
            badge_symbol = STATUS_SYMBOLS.get(status, "⏳ Ready")
            reason_html = ""

        st.markdown(
            f"""
            <div class="fin-card" style="padding: 14px 18px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 600; color: #17365D; font-size: 15px;">
                        {meta['icon']} {meta['name']}
                    </div>
                    <span style="font-size: 12px; font-weight: 600; color: {STATUS_COLORS.get(status, '#697586')};">
                        {badge_symbol}
                    </span>
                </div>
                <div style="font-size: 13px; color: #697586; margin-top: 6px; line-height: 1.4;">
                    {meta['desc']}{timing_str}
                </div>
                {reason_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Last Query Details ───────────────────────────────────────────────────────
if last_state:
    with st.expander("🔍 Inspect Last Workflow Query State", expanded=False):
        st.write(f"**Query:** {last_state.get('query')}")
        st.write(f"**Intent:** `{last_state.get('intent')}`")
        st.write(f"**Retrieved Chunks:** {len(last_state.get('retrieved_chunks', []))}")
        st.write(f"**Calculated Ratios:** {list(last_state.get('calculated_ratios', {}).keys())}")
        st.write(f"**Validation Passed:** {last_state.get('validation_passed')}")

# ── Standard Page Navigation ─────────────────────────────────────────────────
render_page_navigation(
    prev_page="pages/5_ML_Forecasting.py",
    next_page="pages/7_Evidence_Explorer.py",
    prev_label="ML Forecasting",
    next_label="Evidence Explorer",
)
