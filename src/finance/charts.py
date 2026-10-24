"""
FIN SIGHT AI - Advanced Financial Charts Library
Interactive, enterprise-grade Plotly visualizations styled with professional light theme.
Provides 12 financial charts with period filtering and CSV data export capabilities.
"""
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Enterprise Light Theme Color Palette
NAVY_PRIMARY = "#17365D"
BLUE_SECONDARY = "#3976C5"
TEAL_ACCENT = "#168C87"
GREEN_SUCCESS = "#24865B"
AMBER_WARNING = "#D99020"
RED_ERROR = "#C74440"
SLATE_TEXT = "#253247"
SLATE_MUTED = "#697586"
BG_WHITE = "#FFFFFF"
BG_LIGHT = "#F8FAFC"
BORDER_COLOR = "#E1E7EF"


def apply_light_layout(
    fig: go.Figure,
    title: str = "",
    height: int = 400,
    show_legend: bool = True
) -> go.Figure:
    """Applies clean enterprise light theme styling to any Plotly figure."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(size=14, color=NAVY_PRIMARY, family="Inter, Arial, sans-serif"),
            x=0.01,
            xanchor="left",
        ),
        paper_bgcolor=BG_WHITE,
        plot_bgcolor=BG_LIGHT,
        font=dict(family="Inter, Arial, sans-serif", color=SLATE_TEXT, size=11),
        margin=dict(l=40, r=40, t=50, b=40),
        height=height,
        showlegend=show_legend,
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor=BORDER_COLOR,
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hoverlabel=dict(
            bgcolor=NAVY_PRIMARY,
            font_size=12,
            font_family="Inter, sans-serif",
            font_color="#FFFFFF"
        ),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#EDF2F7",
        linecolor=BORDER_COLOR,
        tickfont=dict(color=SLATE_MUTED),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#EDF2F7",
        linecolor=BORDER_COLOR,
        tickfont=dict(color=SLATE_MUTED),
    )
    return fig


# ── Chart 1: Revenue Trend (Line) ───────────────────────────────────────────
def create_revenue_trend_chart(
    periods: List[str],
    revenues: List[float],
    unit: str = "$M"
) -> Tuple[go.Figure, pd.DataFrame]:
    df = pd.DataFrame({"Reporting Period": periods, f"Revenue ({unit})": revenues})
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=periods,
            y=revenues,
            mode="lines+markers",
            name="Revenue",
            line=dict(color=BLUE_SECONDARY, width=3),
            marker=dict(size=8, color=NAVY_PRIMARY, symbol="circle"),
            hovertemplate="<b>Period:</b> %{x}<br><b>Revenue:</b> %{y:,.1f} " + unit + "<extra></extra>",
        )
    )
    apply_light_layout(fig, title=f"Revenue Trajectory ({unit})", height=380)
    return fig, df


# ── Chart 2: Revenue vs Net Profit (Grouped Bar) ─────────────────────────────
def create_revenue_vs_profit_chart(
    periods: List[str],
    revenues: List[float],
    net_profits: List[float],
    unit: str = "$M"
) -> Tuple[go.Figure, pd.DataFrame]:
    df = pd.DataFrame({
        "Period": periods,
        f"Revenue ({unit})": revenues,
        f"Net Profit ({unit})": net_profits,
    })
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=periods,
            y=revenues,
            name="Total Revenue",
            marker_color=BLUE_SECONDARY,
            hovertemplate="<b>%{x}</b><br>Revenue: %{y:,.1f} " + unit + "<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=periods,
            y=net_profits,
            name="Net Profit",
            marker_color=TEAL_ACCENT,
            hovertemplate="<b>%{x}</b><br>Net Profit: %{y:,.1f} " + unit + "<extra></extra>",
        )
    )
    fig.update_layout(barmode="group")
    apply_light_layout(fig, title=f"Revenue vs. Net Profit Comparison ({unit})", height=380)
    return fig, df


# ── Chart 3: Profit Margin Trend (Line) ──────────────────────────────────────
def create_profit_margin_trend_chart(
    periods: List[str],
    net_margins: List[float],
    operating_margins: Optional[List[float]] = None
) -> Tuple[go.Figure, pd.DataFrame]:
    data = {"Period": periods, "Net Margin (%)": net_margins}
    if operating_margins:
        data["Operating Margin (%)"] = operating_margins
    df = pd.DataFrame(data)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=periods,
            y=net_margins,
            mode="lines+markers",
            name="Net Profit Margin (%)",
            line=dict(color=GREEN_SUCCESS, width=2.5),
            marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>Net Margin: %{y:.1f}%<extra></extra>",
        )
    )
    if operating_margins:
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=operating_margins,
                mode="lines+markers",
                name="Operating Margin (%)",
                line=dict(color=BLUE_SECONDARY, width=2, dash="dash"),
                marker=dict(size=6),
                hovertemplate="<b>%{x}</b><br>Operating Margin: %{y:.1f}%<extra></extra>",
            )
        )
    apply_light_layout(fig, title="Operating & Net Profit Margin (%)", height=380)
    return fig, df


# ── Chart 4: Assets vs Liabilities vs Equity (Grouped Bar) ───────────────────
def create_balance_sheet_comp_chart(
    periods: List[str],
    assets: List[float],
    liabilities: List[float],
    equity: List[float],
    unit: str = "$M"
) -> Tuple[go.Figure, pd.DataFrame]:
    df = pd.DataFrame({
        "Period": periods,
        f"Assets ({unit})": assets,
        f"Liabilities ({unit})": liabilities,
        f"Equity ({unit})": equity,
    })
    fig = go.Figure()
    fig.add_trace(go.Bar(x=periods, y=assets, name="Total Assets", marker_color=NAVY_PRIMARY))
    fig.add_trace(go.Bar(x=periods, y=liabilities, name="Total Liabilities", marker_color=AMBER_WARNING))
    fig.add_trace(go.Bar(x=periods, y=equity, name="Stockholders' Equity", marker_color=TEAL_ACCENT))
    fig.update_layout(barmode="group")
    apply_light_layout(fig, title=f"Assets, Liabilities & Equity Structure ({unit})", height=380)
    return fig, df


# ── Chart 5: Financial Composition (Donut) ──────────────────────────────────
def create_financial_composition_donut(
    labels: List[str],
    values: List[float],
    title: str = "Balance Sheet Composition"
) -> Tuple[go.Figure, pd.DataFrame]:
    df = pd.DataFrame({"Item": labels, "Value": values})
    colors = [NAVY_PRIMARY, BLUE_SECONDARY, TEAL_ACCENT, GREEN_SUCCESS, AMBER_WARNING, "#8B5CF6"]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors[:len(labels)]),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Value: %{value:,.1f}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )
    apply_light_layout(fig, title=title, height=360)
    return fig, df


# ── Chart 6: Cash Flow Breakdown (Bar) ──────────────────────────────────────
def create_cash_flow_chart(
    periods: List[str],
    operating_cf: List[float],
    investing_cf: Optional[List[float]] = None,
    financing_cf: Optional[List[float]] = None,
    unit: str = "$M"
) -> Tuple[go.Figure, pd.DataFrame]:
    data = {"Period": periods, f"Operating CF ({unit})": operating_cf}
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=periods,
            y=operating_cf,
            name="Operating Cash Flow",
            marker_color=[GREEN_SUCCESS if x >= 0 else RED_ERROR for x in operating_cf],
            hovertemplate="<b>%{x}</b><br>Operating CF: %{y:,.1f} " + unit + "<extra></extra>",
        )
    )
    if investing_cf:
        data[f"Investing CF ({unit})"] = investing_cf
        fig.add_trace(
            go.Bar(
                x=periods,
                y=investing_cf,
                name="Investing Cash Flow",
                marker_color=BLUE_SECONDARY,
                hovertemplate="<b>%{x}</b><br>Investing CF: %{y:,.1f} " + unit + "<extra></extra>",
            )
        )
    if financing_cf:
        data[f"Financing CF ({unit})"] = financing_cf
        fig.add_trace(
            go.Bar(
                x=periods,
                y=financing_cf,
                name="Financing Cash Flow",
                marker_color=AMBER_WARNING,
                hovertemplate="<b>%{x}</b><br>Financing CF: %{y:,.1f} " + unit + "<extra></extra>",
            )
        )
    df = pd.DataFrame(data)
    fig.update_layout(barmode="group")
    apply_light_layout(fig, title=f"Cash Flow Breakdown ({unit})", height=380)
    return fig, df


# ── Chart 7: Financial Ratio Comparison (Grouped Bar) ────────────────────────
def create_ratio_comparison_chart(
    periods: List[str],
    current_ratios: List[float],
    debt_to_equity: List[float]
) -> Tuple[go.Figure, pd.DataFrame]:
    df = pd.DataFrame({
        "Period": periods,
        "Current Ratio (x)": current_ratios,
        "Debt-to-Equity (x)": debt_to_equity,
    })
    fig = go.Figure()
    fig.add_trace(go.Bar(x=periods, y=current_ratios, name="Current Ratio (Liquidity)", marker_color=BLUE_SECONDARY))
    fig.add_trace(go.Bar(x=periods, y=debt_to_equity, name="Debt to Equity (Leverage)", marker_color=AMBER_WARNING))
    fig.add_hline(y=1.0, line_dash="dot", line_color=RED_ERROR, annotation_text="Liquidity Baseline (1.0x)")
    fig.update_layout(barmode="group")
    apply_light_layout(fig, title="Financial Health Ratios (x)", height=380)
    return fig, df


# ── Chart 8: Risk Heatmap ───────────────────────────────────────────────────
def create_risk_heatmap(
    categories: List[str],
    periods: List[str],
    risk_scores: List[List[float]], # 0.0 (low) to 1.0 (high)
) -> Tuple[go.Figure, pd.DataFrame]:
    df = pd.DataFrame(risk_scores, index=categories, columns=periods)
    fig = go.Figure(
        data=go.Heatmap(
            z=risk_scores,
            x=periods,
            y=categories,
            colorscale=[[0, "#E6F4EA"], [0.5, "#FEF7E0"], [1.0, "#FCE8E6"]],
            showscale=True,
            colorbar=dict(title="Risk Level", tickvals=[0.2, 0.5, 0.8], ticktext=["Low", "Medium", "High"]),
            hovertemplate="<b>Category:</b> %{y}<br><b>Period:</b> %{x}<br><b>Score:</b> %{z:.2f}<extra></extra>",
        )
    )
    apply_light_layout(fig, title="Multi-Dimensional Financial Risk Heatmap", height=340, show_legend=False)
    return fig, df


# ── Chart 9: Financial Waterfall Chart ──────────────────────────────────────
def create_financial_waterfall_chart(
    revenue: float,
    cogs: float,
    opex: float,
    taxes: float,
    net_income: float,
    unit: str = "$M"
) -> Tuple[go.Figure, pd.DataFrame]:
    labels = ["Revenue", "COGS", "Gross Profit", "Operating Expenses", "EBIT", "Taxes", "Net Income"]
    gross_profit = revenue - cogs
    ebit = gross_profit - opex
    
    measures = ["absolute", "relative", "total", "relative", "total", "relative", "total"]
    values = [revenue, -cogs, gross_profit, -opex, ebit, -taxes, net_income]

    df = pd.DataFrame({"Step": labels, f"Value ({unit})": values})
    fig = go.Figure(
        go.Waterfall(
            name="Income Waterfall",
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            connector=dict(line=dict(color=BORDER_COLOR)),
            decreasing=dict(marker=dict(color=RED_ERROR)),
            increasing=dict(marker=dict(color=GREEN_SUCCESS)),
            totals=dict(marker=dict(color=NAVY_PRIMARY)),
            hovertemplate="<b>%{x}</b><br>Amount: %{y:,.1f} " + unit + "<extra></extra>",
        )
    )
    apply_light_layout(fig, title=f"Income Statement Waterfall Bridge ({unit})", height=390, show_legend=False)
    return fig, df


# ── Chart 10: Financial KPI Gauges ──────────────────────────────────────────
def create_kpi_gauge(
    value: float,
    title: str,
    min_val: float = 0.0,
    max_val: float = 5.0,
    target_val: Optional[float] = None,
    suffix: str = "x"
) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta" if target_val is not None else "gauge+number",
            value=value,
            delta={"reference": target_val} if target_val is not None else None,
            number={"suffix": f" {suffix}", "font": {"size": 26, "color": NAVY_PRIMARY}},
            title={"text": f"<b>{title}</b>", "font": {"size": 13, "color": SLATE_TEXT}},
            gauge={
                "axis": {"range": [min_val, max_val], "tickwidth": 1, "tickcolor": BORDER_COLOR},
                "bar": {"color": BLUE_SECONDARY},
                "bgcolor": BG_WHITE,
                "borderwidth": 1,
                "bordercolor": BORDER_COLOR,
                "steps": [
                    {"range": [min_val, min_val + (max_val - min_val) * 0.4], "color": "#FEE2E2"},
                    {"range": [min_val + (max_val - min_val) * 0.4, min_val + (max_val - min_val) * 0.7], "color": "#FEF3C7"},
                    {"range": [min_val + (max_val - min_val) * 0.7, max_val], "color": "#DCFCE7"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor=BG_WHITE,
        height=220,
        margin=dict(l=20, r=20, t=35, b=20),
    )
    return fig


# ── Chart 11: Period-over-Period Growth (Bar) ────────────────────────────────
def create_growth_bar_chart(
    periods: List[str],
    rev_growth: List[float],
    profit_growth: Optional[List[float]] = None
) -> Tuple[go.Figure, pd.DataFrame]:
    data = {"Period": periods, "Revenue Growth (%)": rev_growth}
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=periods,
            y=rev_growth,
            name="Revenue Growth (%)",
            marker_color=[GREEN_SUCCESS if x >= 0 else RED_ERROR for x in rev_growth],
            hovertemplate="<b>%{x}</b><br>Revenue YoY: %{y:.1f}%<extra></extra>",
        )
    )
    if profit_growth:
        data["Net Profit Growth (%)"] = profit_growth
        fig.add_trace(
            go.Bar(
                x=periods,
                y=profit_growth,
                name="Net Profit Growth (%)",
                marker_color=BLUE_SECONDARY,
                hovertemplate="<b>%{x}</b><br>Profit YoY: %{y:.1f}%<extra></extra>",
            )
        )
    df = pd.DataFrame(data)
    fig.add_hline(y=0.0, line_color=SLATE_MUTED, line_width=1)
    fig.update_layout(barmode="group")
    apply_light_layout(fig, title="Year-over-Year Growth Rates (%)", height=380)
    return fig, df


# ── Chart 12: Actual vs Previous Period (Delta View) ─────────────────────────
def create_period_delta_table(
    metric_names: List[str],
    current_vals: List[float],
    prior_vals: List[float],
    unit: str = "$M"
) -> pd.DataFrame:
    records = []
    for name, curr, prior in zip(metric_names, current_vals, prior_vals):
        abs_delta = round(curr - prior, 2)
        pct_delta = round((abs_delta / abs(prior)) * 100, 2) if prior != 0 else 0.0
        records.append({
            "Metric": name,
            f"Current Period ({unit})": f"{curr:,.1f}",
            f"Prior Period ({unit})": f"{prior:,.1f}",
            "Change (Abs)": f"{'+' if abs_delta > 0 else ''}{abs_delta:,.1f}",
            "Change (%)": f"{'+' if pct_delta > 0 else ''}{pct_delta:.1f}%",
        })
    return pd.DataFrame(records)
