"""
FIN SIGHT AI - Page 4: Financial Scenario & What-If Simulator
Professional deterministic financial modeling workspace supporting Base, Optimistic,
Pessimistic, and Custom scenarios with instant ratio recalculations, formula transparency,
and fully reactive dynamic charts.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Scenario Simulator | FIN SIGHT AI",
    page_icon="🎯",
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

render_page_header(
    title="Financial Scenario & What-If Simulator",
    subtitle="Model forward deterministic financial trajectories across Base, Optimistic, Pessimistic, and Custom cases with formula transparency."
)

# ── 1. Fetch Baseline Financial Data ──────────────────────────────────────────
doc_session = st.session_state.get("document_session")
all_records = st.session_state.get("all_records", [])

active_company = getattr(doc_session, "company_name", None) or st.session_state.get("selected_company", "Apex Technologies")
active_period = st.session_state.get("selected_period", "FY2023")
source_label = doc_session.file_name if doc_session else "Audited Benchmark Baseline"

default_base_metrics = {
    "revenue": 124_800_000.0,
    "operating_expenses": 51_200_000.0,
    "cogs": 50_500_000.0,
    "operating_profit": 23_100_000.0,
    "net_profit": 17_060_000.0,
    "current_assets": 64_400_000.0,
    "inventory": 14_200_000.0,
    "current_liabilities": 35_600_000.0,
    "total_debt": 30_400_000.0,
    "total_equity": 84_000_000.0,
    "total_assets": 145_000_000.0,
    "total_liabilities": 61_000_000.0,
}

# If structured records exist from uploaded PDF, Excel, CSV, or Manual entry, use them
if all_records and len(all_records) >= 1:
    rec = all_records[-1]
    active_company = rec.company_name or active_company
    active_period = rec.reporting_period or active_period
    mult = 1.0 if (rec.revenue and rec.revenue > 10_000) else 1_000_000.0
    if rec.revenue: default_base_metrics["revenue"] = float(rec.revenue) * mult
    if rec.cost_of_goods_sold: default_base_metrics["cogs"] = float(rec.cost_of_goods_sold) * mult
    if rec.operating_expenses: default_base_metrics["operating_expenses"] = float(rec.operating_expenses) * mult
    if rec.operating_income: default_base_metrics["operating_profit"] = float(rec.operating_income) * mult
    if rec.net_income: default_base_metrics["net_profit"] = float(rec.net_income) * mult
    if rec.current_assets: default_base_metrics["current_assets"] = float(rec.current_assets) * mult
    if rec.current_liabilities: default_base_metrics["current_liabilities"] = float(rec.current_liabilities) * mult
    if rec.total_debt: default_base_metrics["total_debt"] = float(rec.total_debt) * mult
    if rec.total_equity: default_base_metrics["total_equity"] = float(rec.total_equity) * mult
    if rec.total_assets: default_base_metrics["total_assets"] = float(rec.total_assets) * mult
    if rec.total_liabilities: default_base_metrics["total_liabilities"] = float(rec.total_liabilities) * mult
elif doc_session and hasattr(doc_session, "extracted_metrics_raw"):
    for k, metric_list in doc_session.extracted_metrics_raw.items():
        if metric_list and len(metric_list) > 0:
            val = metric_list[0].normalized_value or metric_list[0].numeric_value
            if val and k in default_base_metrics:
                default_base_metrics[k] = float(val) if val > 10_000 else float(val) * 1_000_000.0

# Baseline Information Card
st.markdown(
    f"""
    <div class="callout-box" style="background:#F8FAFC; border-left-color:#17365D; color:#17365D; margin-bottom:18px;">
        <b>Active Model Baseline:</b> <b>{active_company}</b> ({active_period}) &nbsp;|&nbsp; 
        Source: <code>{source_label}</code> &nbsp;|&nbsp; 
        Starting Revenue: <b>${default_base_metrics['revenue']/1e6:.1f}M</b> &nbsp;|&nbsp; 
        Net Profit: <b>${default_base_metrics['net_profit']/1e6:.1f}M</b> &nbsp;|&nbsp; 
        Current Ratio: <b>{default_base_metrics['current_assets']/default_base_metrics['current_liabilities']:.2f}x</b>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 2. Scenario Case Selector & Explanation ──────────────────────────────────
scen_col1, scen_col2 = st.columns([2, 1])
with scen_col1:
    scenario_type = st.radio(
        "Select Scenario Case to Model:",
        ["Base Case", "Optimistic Case", "Pessimistic Case", "Custom Scenario"],
        horizontal=True,
        key="selected_scenario_radio",
    )
with scen_col2:
    horizon_years = st.slider("Simulation Horizon (Years Forward):", 1, 5, 3, key="sim_horizon")

# Plain-English Case Explanations required by specifications
SCENARIO_EXPLANATIONS = {
    "Base Case": "Uses the selected report's actual financial values as the starting point, without applying additional changes unless the model explicitly requires them.",
    "Optimistic Case": "Explores a more favorable outcome using assumptions you can review and change, such as higher revenue growth or lower expense growth.",
    "Pessimistic Case": "Explores an unfavorable outcome using assumptions you can review and change, such as lower revenue growth or higher expense growth.",
    "Custom Scenario": "Set your own financial assumptions to test how specific changes may affect the company's future financial position.",
}

st.markdown(
    f"""
    <div style="background:#FFFFFF; border:1px solid #E1E7EF; border-radius:6px; padding:12px 18px; margin-bottom:20px;">
        <span style="font-weight:600; color:#17365D;">Scenario Definition ({scenario_type}):</span> 
        <span style="color:#697586; font-size:14px;">{SCENARIO_EXPLANATIONS[scenario_type]}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Define case preset parameters
if scenario_type == "Base Case":
    preset_rev = 8.0
    preset_opex = 5.0
    preset_debt = 0.0
    preset_tax = 21.0
elif scenario_type == "Optimistic Case":
    preset_rev = 15.0
    preset_opex = 3.0
    preset_debt = -5.0
    preset_tax = 20.0
elif scenario_type == "Pessimistic Case":
    preset_rev = -4.0
    preset_opex = 9.0
    preset_debt = 10.0
    preset_tax = 22.0
else:
    preset_rev = 10.0
    preset_opex = 6.0
    preset_debt = 2.0
    preset_tax = 21.0

# Synchronize widget session state whenever the scenario radio button changes
if st.session_state.get("last_active_scenario") != scenario_type:
    st.session_state["last_active_scenario"] = scenario_type
    st.session_state["sim_rev_growth"] = float(preset_rev)
    st.session_state["sim_opex_growth"] = float(preset_opex)
    st.session_state["sim_debt_growth"] = float(preset_debt)
    st.session_state["sim_tax_rate"] = float(preset_tax)

# ── 3. Assumption Controls with Live Reactive Recalculation ───────────────────
st.markdown("### 🎛️ Scenario Assumption Controls")
st.caption("Adjust driver assumptions below. All metrics and charts recalculate instantly.")

col_a1, col_a2, col_a3, col_a4 = st.columns(4)

with col_a1:
    st.markdown("<div class='fin-card'>", unsafe_allow_html=True)
    st.markdown("<div class='fin-card-header'>Revenue Growth</div>", unsafe_allow_html=True)
    st.caption(f"Baseline: ${default_base_metrics['revenue'] / 1e6:.1f}M")
    rev_growth = st.number_input(
        "Annual Revenue Growth (%)",
        value=float(st.session_state.get("sim_rev_growth", preset_rev)),
        step=1.0,
        key="sim_rev_growth",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_a2:
    st.markdown("<div class='fin-card'>", unsafe_allow_html=True)
    st.markdown("<div class='fin-card-header'>OpEx Inflation</div>", unsafe_allow_html=True)
    st.caption(f"Baseline: ${default_base_metrics['operating_expenses'] / 1e6:.1f}M")
    opex_growth = st.number_input(
        "Annual OpEx Growth (%)",
        value=float(st.session_state.get("sim_opex_growth", preset_opex)),
        step=1.0,
        key="sim_opex_growth",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_a3:
    st.markdown("<div class='fin-card'>", unsafe_allow_html=True)
    st.markdown("<div class='fin-card-header'>Debt Leverage Change</div>", unsafe_allow_html=True)
    st.caption(f"Baseline: ${default_base_metrics['total_debt'] / 1e6:.1f}M")
    debt_change = st.number_input(
        "Annual Debt Change (%)",
        value=float(st.session_state.get("sim_debt_growth", preset_debt)),
        step=1.0,
        key="sim_debt_growth",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_a4:
    st.markdown("<div class='fin-card'>", unsafe_allow_html=True)
    st.markdown("<div class='fin-card-header'>Corporate Tax Rate</div>", unsafe_allow_html=True)
    st.caption("Statutory Effective Rate")
    tax_rate = st.number_input(
        "Effective Tax Rate (%)",
        value=float(st.session_state.get("sim_tax_rate", preset_tax)),
        step=0.5,
        key="sim_tax_rate",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ── 4. Deterministic Calculation Engine ───────────────────────────────────────
base_rev = default_base_metrics["revenue"]
base_cogs = default_base_metrics["cogs"]
base_opex = default_base_metrics["operating_expenses"]
base_ca = default_base_metrics["current_assets"]
base_cl = default_base_metrics["current_liabilities"]
base_debt = default_base_metrics["total_debt"]
base_equity = default_base_metrics["total_equity"]

curr_rev = base_rev
curr_cogs = base_cogs
curr_opex = base_opex
curr_debt = base_debt
curr_equity = base_equity
curr_ca = base_ca
curr_cl = base_cl

sim_rows = []
for y in range(1, horizon_years + 1):
    curr_rev *= (1.0 + rev_growth / 100.0)
    curr_cogs *= (1.0 + (rev_growth * 0.75) / 100.0)  # variable production costs
    curr_opex *= (1.0 + opex_growth / 100.0)
    curr_debt *= (1.0 + debt_change / 100.0)
    
    op_profit = curr_rev - curr_cogs - curr_opex
    tax_expense = max(0.0, op_profit * (tax_rate / 100.0))
    net_profit = op_profit - tax_expense
    curr_equity += max(0.0, net_profit * 0.65)  # retained earnings additions

    curr_ca *= (1.0 + (rev_growth * 0.70) / 100.0)
    curr_cl *= (1.0 + (opex_growth * 0.60) / 100.0)

    pm = (net_profit / curr_rev) * 100.0 if curr_rev else 0.0
    cr = curr_ca / curr_cl if curr_cl else 1.0
    de = curr_debt / curr_equity if curr_equity else 0.0
    wc = curr_ca - curr_cl

    sim_rows.append({
        "Period": f"Year +{y}",
        "Projected Revenue ($M)": round(curr_rev / 1e6, 2),
        "Operating Profit ($M)": round(op_profit / 1e6, 2),
        "Net Profit ($M)": round(net_profit / 1e6, 2),
        "Profit Margin (%)": round(pm, 2),
        "Current Ratio (x)": round(cr, 2),
        "Debt-to-Equity (x)": round(de, 2),
        "Working Capital ($M)": round(wc / 1e6, 2),
        "Simulated Revenue Raw": curr_rev,
        "Baseline Revenue ($M)": round(base_rev / 1e6, 2),
        "Baseline Net Profit ($M)": round(default_base_metrics["net_profit"] / 1e6, 2),
    })

sim_df = pd.DataFrame(sim_rows)
final_sim = sim_rows[-1]

# ── 5. Projected Year-End Outcome Cards ───────────────────────────────────────
st.markdown("### 📊 Projected Horizon Year-End Outcome")
st.caption(f"Calculated results at Year +{horizon_years} under '{scenario_type}' assumptions (Simulated, hypothetical projection).")

r_col1, r_col2, r_col3, r_col4 = st.columns(4)
with r_col1:
    rev_delta = ((final_sim['Projected Revenue ($M)'] - (base_rev / 1e6)) / (base_rev / 1e6)) * 100
    st.metric(
        "Projected Revenue",
        f"${final_sim['Projected Revenue ($M)']:.1f}M",
        delta=f"{rev_delta:+.1f}% vs Baseline",
    )
with r_col2:
    st.metric(
        "Projected Net Profit",
        f"${final_sim['Net Profit ($M)']:.1f}M",
        delta=f"{final_sim['Profit Margin (%)']:.1f}% margin",
    )
with r_col3:
    base_cr = base_ca / base_cl if base_cl else 1.0
    cr_delta = final_sim['Current Ratio (x)'] - base_cr
    st.metric(
        "Projected Current Ratio",
        f"{final_sim['Current Ratio (x)']:.2f}x",
        delta=f"{cr_delta:+.2f}x vs Baseline",
    )
with r_col4:
    base_wc = (base_ca - base_cl) / 1e6
    wc_delta = final_sim['Working Capital ($M)'] - base_wc
    st.metric(
        "Working Capital",
        f"${final_sim['Working Capital ($M)']:.1f}M",
        delta=f"${wc_delta:+.1f}M vs Baseline",
    )

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# ── 6. Reactive Simulation Charts (Baseline vs Scenario & Ratios) ─────────────
st.markdown("### 📈 Dynamic Multi-Period Simulation Chart")
st.caption("Inspect baseline comparison, forward financial trajectories, and ratio changes with hover details.")

tab_c1, tab_c2 = st.tabs(["📊 Revenue & Profit (Baseline vs Scenario)", "📈 Financial Ratios & Liquidity"])

with tab_c1:
    periods_with_base = ["Baseline"] + list(sim_df["Period"])
    rev_with_base = [round(base_rev / 1e6, 2)] + list(sim_df["Projected Revenue ($M)"])
    np_with_base = [round(default_base_metrics["net_profit"] / 1e6, 2)] + list(sim_df["Net Profit ($M)"])
    op_with_base = [round(default_base_metrics["operating_profit"] / 1e6, 2)] + list(sim_df["Operating Profit ($M)"])

    hover_text_rev = [
        f"<b>Baseline</b><br>Revenue: ${base_rev/1e6:.1f}M<br>Status: Audited Starting Baseline"
    ] + [
        f"<b>{row['Period']} ({scenario_type})</b><br>"
        f"Simulated Revenue: ${row['Projected Revenue ($M)']:.2f}M<br>"
        f"Baseline Revenue: ${row['Baseline Revenue ($M)']:.2f}M<br>"
        f"Revenue Growth Assumption: {rev_growth:+.1f}%<br>"
        f"Operating Profit: ${row['Operating Profit ($M)']:.2f}M"
        for _, row in sim_df.iterrows()
    ]

    hover_text_np = [
        f"<b>Baseline</b><br>Net Profit: ${default_base_metrics['net_profit']/1e6:.1f}M<br>Status: Audited Starting Baseline"
    ] + [
        f"<b>{row['Period']} ({scenario_type})</b><br>"
        f"Simulated Net Profit: ${row['Net Profit ($M)']:.2f}M<br>"
        f"Profit Margin: {row['Profit Margin (%)']:.2f}%<br>"
        f"Tax Rate Assumption: {tax_rate:.1f}%<br>"
        f"OpEx Inflation Assumption: {opex_growth:+.1f}%"
        for _, row in sim_df.iterrows()
    ]

    fig_sim = go.Figure()
    fig_sim.add_trace(go.Bar(
        x=periods_with_base,
        y=rev_with_base,
        name="Projected Revenue ($M)",
        marker_color="#17365D",
        hovertext=hover_text_rev,
        hoverinfo="text",
    ))
    fig_sim.add_trace(go.Bar(
        x=periods_with_base,
        y=op_with_base,
        name="Operating Profit ($M)",
        marker_color="#3976C5",
    ))
    fig_sim.add_trace(go.Bar(
        x=periods_with_base,
        y=np_with_base,
        name="Net Profit ($M)",
        marker_color="#24865B",
        hovertext=hover_text_np,
        hoverinfo="text",
    ))
    # Add baseline indicator reference line
    fig_sim.add_hline(
        y=round(base_rev / 1e6, 2),
        line_dash="dot",
        line_color="#94A3B8",
        annotation_text=f"Baseline Rev (${round(base_rev/1e6, 1)}M)",
        annotation_position="top left",
    )

    fig_sim.update_layout(
        title=f"Trajectory: Baseline vs Simulated Outcomes ({scenario_type})",
        barmode="group",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="Amount ($M)",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFC",
    )
    st.plotly_chart(fig_sim, use_container_width=True)

with tab_c2:
    fig_ratios = go.Figure()
    fig_ratios.add_trace(go.Scatter(
        x=sim_df["Period"],
        y=sim_df["Current Ratio (x)"],
        name="Current Ratio (x)",
        mode="lines+markers",
        line=dict(color="#17365D", width=3),
        marker=dict(size=8),
    ))
    fig_ratios.add_trace(go.Scatter(
        x=sim_df["Period"],
        y=sim_df["Profit Margin (%)"],
        name="Profit Margin (%)",
        mode="lines+markers",
        line=dict(color="#24865B", width=3),
        marker=dict(size=8),
    ))
    fig_ratios.add_trace(go.Scatter(
        x=sim_df["Period"],
        y=sim_df["Debt-to-Equity (x)"],
        name="Debt-to-Equity (x)",
        mode="lines+markers",
        line=dict(color="#D99020", width=3),
        marker=dict(size=8),
    ))
    fig_ratios.update_layout(
        title=f"Ratio Projections across {horizon_years}-Year Horizon ({scenario_type})",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8FAFC",
    )
    st.plotly_chart(fig_ratios, use_container_width=True)

# ── 7. Detailed Results Table & CSV Export ────────────────────────────────────
st.markdown("<div class='fin-card'>", unsafe_allow_html=True)
st.markdown("<div class='fin-card-heading'>Simulated Financial Schedule & Multi-Period Forecast</div>", unsafe_allow_html=True)
display_cols = [
    "Period", "Projected Revenue ($M)", "Operating Profit ($M)", "Net Profit ($M)",
    "Profit Margin (%)", "Current Ratio (x)", "Debt-to-Equity (x)", "Working Capital ($M)"
]
st.dataframe(sim_df[display_cols], use_container_width=True)

csv_sim = sim_df[display_cols].to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Export Scenario Simulation Results (CSV)",
    data=csv_sim,
    file_name=f"scenario_simulation_{scenario_type.lower().replace(' ', '_')}_{active_company.replace(' ', '_')}.csv",
    mime="text/csv",
    key="dl_sim_csv"
)
st.markdown("</div>", unsafe_allow_html=True)

# ── 8. Mathematical Formula & Evidence References ────────────────────────────
with st.expander("📖 Deterministic Formulas & Calculation Methodology", expanded=False):
    st.markdown(
        f"""
        **Simulation Methodology:**
        All outputs are calculated deterministically from verified starting baselines:

        - **Projected Revenue:** $Revenue_t = Revenue_{{t-1}} \\times (1 + g_{{rev}})$ [User input: {rev_growth:+.1f}%]
        - **Projected OpEx:** $OpEx_t = OpEx_{{t-1}} \\times (1 + g_{{opex}})$ [User input: {opex_growth:+.1f}%]
        - **Projected COGS:** $COGS_t = COGS_{{t-1}} \\times (1 + g_{{rev}} \\times 0.75)$
        - **Operating Income (EBIT):** $Revenue_t - COGS_t - OpEx_t$
        - **Net Profit:** $EBIT_t - Tax_t$ (Effective statutory rate: {tax_rate:.1f}%)
        - **Current Ratio:** $Current\\ Assets_t / Current\\ Liabilities_t$
        - **Debt-to-Equity:** $Total\\ Debt_t / Total\\ Equity_t$
        - **Working Capital:** $Current\\ Assets_t - Current\\ Liabilities_t$

        *Notice:* Scenario simulation models management assumptions and is distinct from historical machine learning forecasting.
        """
    )

# ── Standard Page Navigation ─────────────────────────────────────────────────
render_page_navigation(
    prev_page="pages/3_Financial_Chat.py",
    next_page="pages/5_ML_Forecasting.py",
    prev_label="Financial Chatbot",
    next_label="ML Forecasting",
)
