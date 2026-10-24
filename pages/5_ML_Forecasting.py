"""
FIN SIGHT AI - Machine Learning Financial Forecasting Page
Estimates future financial metrics using chronological time-series algorithms,
backtesting model selection, evaluation metrics (MAE, RMSE, MAPE, WAPE),
prediction intervals, and honest handling of data limitations.
"""
import streamlit as st
import pandas as pd
import numpy as np

from src.ui.theme import inject_theme, section_header, kpi_card
from src.finance.forecasting import (
    FinancialForecaster,
    FORECASTABLE_METRICS,
    plot_financial_forecast,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="ML Financial Forecasting | FIN SIGHT AI",
    page_icon="📈",
    layout="wide",
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
    title="Machine Learning Financial Forecasting",
    subtitle="Estimate future financial trajectories using chronological backtesting, statistical trend modeling, and empirical confidence intervals."
)

forecaster = FinancialForecaster()

# Check for session state document or multi-period data
doc_session = st.session_state.get("document_session")
multi_records = st.session_state.get("multi_period_records", [])

# Collect available historical company data
company_name = st.session_state.get("active_company", "Apex Technologies Ltd.")
reporting_period = st.session_state.get("active_period", "FY2023")

# Available sample / loaded series builder
# If documents are uploaded, extract historical sequence. Otherwise provide sample verified baseline
default_historical = {
    "revenue": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [78_400_000.0, 89_200_000.0, 108_500_000.0, 124_800_000.0],
        "unit": "$",
    },
    "operating_expenses": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [34_200_000.0, 38_100_000.0, 44_600_000.0, 51_200_000.0],
        "unit": "$",
    },
    "operating_profit": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [12_100_000.0, 15_600_000.0, 19_200_000.0, 23_100_000.0],
        "unit": "$",
    },
    "net_profit": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [9_200_000.0, 11_800_000.0, 14_900_000.0, 18_200_000.0],
        "unit": "$",
    },
    "total_assets": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [85_000_000.0, 98_000_000.0, 120_000_000.0, 145_000_000.0],
        "unit": "$",
    },
    "total_liabilities": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [35_000_000.0, 42_000_000.0, 52_000_000.0, 61_000_000.0],
        "unit": "$",
    },
    "total_equity": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [50_000_000.0, 56_000_000.0, 68_000_000.0, 84_000_000.0],
        "unit": "$",
    },
    "operating_cash_flow": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [14_000_000.0, 16_500_000.0, 21_000_000.0, 26_400_000.0],
        "unit": "$",
    },
    "net_profit_margin": {
        "periods": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "values": [11.73, 13.23, 13.73, 14.58],
        "unit": "%",
    },
}

# If live document session has extracted metrics, overlay or supplement
if doc_session and hasattr(doc_session, "extracted_metrics"):
    m_summary = doc_session.extracted_metrics.get("metrics_summary", {})
    if "revenue" in m_summary:
        rev_v = m_summary["revenue"].get("value")
        if rev_v:
            default_historical["revenue"]["values"][-1] = rev_v
    if "net_profit" in m_summary:
        np_v = m_summary["net_profit"].get("value")
        if np_v:
            default_historical["net_profit"]["values"][-1] = np_v

st.markdown("---")

# ── Control Bar ─────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.2, 1.5])

with c1:
    metric_labels = {
        "revenue": "Revenue",
        "operating_expenses": "Operating Expenses",
        "operating_profit": "Operating Profit",
        "net_profit": "Net Profit",
        "total_assets": "Total Assets",
        "total_liabilities": "Total Liabilities",
        "total_equity": "Total Equity",
        "operating_cash_flow": "Operating Cash Flow",
        "net_profit_margin": "Net Profit Margin (%)",
    }
    selected_metric_key = st.selectbox(
        "Financial Metric",
        options=list(metric_labels.keys()),
        format_func=lambda k: metric_labels[k],
    )

with c2:
    selected_algo = st.selectbox(
        "Algorithm Strategy",
        options=[
            "Auto (Best Backtest)",
            "Naive Baseline (Last Value)",
            "Moving Average (k=2)",
            "Linear Trend Regression",
            "Exponential Smoothing (ETS/Holt)",
            "ARIMA (1,1,0)",
            "Random Forest Regressor",
        ],
    )

with c3:
    forecast_horizon = st.slider("Horizon (Years)", min_value=1, max_value=5, value=3)

with c4:
    use_custom_data = st.checkbox("Input Custom Historical Data", value=False)

# Historical Data Table & Setup
hist_data = default_historical[selected_metric_key]
unit_str = hist_data["unit"]

if use_custom_data:
    st.markdown("##### 📝 Custom Historical Observations")
    c_p, c_v = st.columns(2)
    with c_p:
        custom_p_str = st.text_input(
            "Historical Periods (comma-separated)",
            value=", ".join(hist_data["periods"]),
        )
    with c_v:
        custom_v_str = st.text_input(
            "Historical Values (comma-separated numbers)",
            value=", ".join([str(v) for v in hist_data["values"]]),
        )
    try:
        active_periods = [p.strip() for p in custom_p_str.split(",") if p.strip()]
        active_values = [float(v.strip()) for v in custom_v_str.split(",") if v.strip()]
    except Exception as e:
        st.error(f"Invalid numbers in custom input: {e}")
        active_periods = hist_data["periods"]
        active_values = hist_data["values"]
else:
    active_periods = hist_data["periods"]
    active_values = hist_data["values"]

# Run Forecast
result = forecaster.forecast_metric(
    historical_periods=active_periods,
    historical_values=active_values,
    metric_name=selected_metric_key,
    metric_display_name=metric_labels[selected_metric_key],
    forecast_horizon=forecast_horizon,
    model_name=selected_algo,
    unit=unit_str,
)

# Display Forecast Results
if not result.is_data_sufficient:
    st.warning(f"⚠️ {result.insufficiency_reason}")
    st.info(
        "**Recommendation:** For single-period filings, navigate to the **Scenario Simulator** page "
        "to explore deterministic What-If growth outcomes based on user assumptions."
    )
else:
    # ── Interactive Plotly Chart ────────────────────────────────────────────
    fig = plot_financial_forecast(result)
    st.plotly_chart(fig, use_container_width=True)

    # ── Top-level KPI Cards ─────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        last_actual = result.historical_values[-1]
        st.metric(
            f"Last Observed ({result.historical_periods[-1]})",
            f"{last_actual:,.2f} {unit_str}",
        )
    with k2:
        final_forecast = result.forecast_values[-1]
        delta_val = final_forecast - last_actual
        delta_pct = (delta_val / abs(last_actual)) * 100 if last_actual != 0 else 0.0
        st.metric(
            f"Forecast ({result.forecast_periods[-1]})",
            f"{final_forecast:,.2f} {unit_str}",
            f"{delta_pct:+.1f}% vs actual",
        )
    with k3:
        st.metric("Selected Model", result.selected_model)
    with k4:
        st.metric(
            "95% CI Range",
            f"±{(result.confidence_interval_95_upper[-1] - final_forecast):,.1f} {unit_str}",
        )

    # ── Forecast Details Table ──────────────────────────────────────────────
    st.markdown("### 📋 Forecast Projections & Confidence Intervals")
    table_rows = []
    for p, val, c80_l, c80_u, c95_l, c95_u in zip(
        result.forecast_periods,
        result.forecast_values,
        result.confidence_interval_80_lower,
        result.confidence_interval_80_upper,
        result.confidence_interval_95_lower,
        result.confidence_interval_95_upper,
    ):
        table_rows.append({
            "Period": p,
            f"Point Forecast ({unit_str})": f"{val:,.2f}",
            "80% Lower Bound": f"{c80_l:,.2f}",
            "80% Upper Bound": f"{c80_u:,.2f}",
            "95% Lower Bound": f"{c95_l:,.2f}",
            "95% Upper Bound": f"{c95_u:,.2f}",
        })
    df_forecast = pd.DataFrame(table_rows)
    st.dataframe(df_forecast, use_container_width=True)

    # ── Model Backtest Scorecard ────────────────────────────────────────────
    st.markdown("### 🔬 Chronological Backtesting & Model Evaluation Scorecard")
    st.caption(
        "Candidate models were evaluated chronologically by holding out the most recent historical period(s). "
        "Lower error metrics indicate superior out-of-sample backtest tracking."
    )

    if result.model_evaluations:
        eval_rows = []
        for me in result.model_evaluations:
            eval_rows.append({
                "Model": me.model_name,
                "MAE": f"{me.mae:,.2f}",
                "RMSE": f"{me.rmse:,.2f}",
                "MAPE (%)": f"{me.mape:.2f}%" if me.mape is not None else "N/A (0 in data)",
                "WAPE (%)": f"{me.wape:.2f}%",
                "Bias": f"{me.forecast_bias:+,.2f}",
                "Outperformed Baseline?": "✅ Yes" if me.beat_baseline else "❌ No",
            })
        df_eval = pd.DataFrame(eval_rows)
        st.dataframe(df_eval, use_container_width=True)

    # ── Methodology & Transparent Disclaimers ───────────────────────────────
    with st.expander("ℹ️ Methodology, Backtesting Protocols & Model Limitations", expanded=False):
        st.markdown(
            """
            - **Data Leakage Prevention:** All time-series models use strictly chronological train-validation splits. No future data or random cross-validation folds are permitted.
            - **Evaluation Metrics Defined:**
              - **MAE (Mean Absolute Error):** $\\frac{1}{n} \\sum |y - \\hat{y}|$
              - **RMSE (Root Mean Squared Error):** $\\sqrt{\\frac{1}{n} \\sum (y - \\hat{y})^2}$
              - **MAPE (Mean Absolute Percentage Error):** $\\frac{100\\%}{n} \\sum |\\frac{y - \\hat{y}}{y}|$ (only defined when actual values are non-zero).
              - **WAPE (Weighted Absolute Percentage Error):** $\\frac{\\sum |y - \\hat{y}|}{\\sum |y|} \\times 100\\%$
              - **Forecast Bias:** Average signed error; positive indicates systematic over-forecasting, negative indicates under-forecasting.
            - **Important Limitations:**
              - Historical extrapolation cannot anticipate structural shocks, unforeseen regulatory changes, or macroeconomic crises.
              - Annual statements typically have small sample sizes ($N < 10$). Confidence interval envelopes appropriately widen for multi-year horizons.
              - Financial forecasts are analytical approximations and do not constitute investment advice or guarantees.
            """
        )

# ── Standard Page Navigation ─────────────────────────────────────────────────
render_page_navigation(
    prev_page="pages/4_Scenario_Simulator.py",
    next_page="pages/6_Agent_Workflow.py",
    prev_label="Scenario Simulator",
    next_label="Agent Workflow",
)
