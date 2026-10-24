"""
FIN SIGHT AI - Financial Scenario & What-If Simulator
Pure Python deterministic scenario engine for Base, Optimistic, and Pessimistic
multi-period forward simulation with instant recalculation of all financial ratios.
Explicitly distinguishes deterministic scenarios from machine learning forecasts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go

from src.finance.financial_formulas import (
    calculate_current_ratio,
    calculate_debt_ratio,
    calculate_debt_to_equity,
    calculate_gross_profit_margin,
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_quick_ratio,
    calculate_revenue_growth,
    calculate_working_capital,
)
from src.ui.theme import CHART_LAYOUT_DEFAULTS, PALETTE
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ScenarioAssumptions:
    """User-adjustable assumptions for a single scenario."""
    scenario_name: str  # "Base Case", "Optimistic Case", "Pessimistic Case"
    revenue_growth_pct: float = 5.0          # Annual % growth in revenue
    opex_growth_pct: float = 4.0             # Annual % growth in operating expenses
    cogs_pct_of_revenue: float = 50.0        # Direct costs as % of revenue
    tax_rate_pct: float = 21.0               # Corporate tax rate %
    interest_rate_pct: float = 5.0           # Annual cost of debt %
    proposed_debt_change: float = 0.0        # Absolute change in total debt
    proposed_equity_change: float = 0.0      # Absolute change in equity capital
    current_assets_growth_pct: float = 4.0   # % growth in current assets
    current_liab_growth_pct: float = 4.0     # % growth in current liabilities
    current_liabilities_growth_pct: float = 4.0
    inventory_pct_of_ca: float = 25.0        # Inventory as % of current assets
    capex_annual: float = 0.0                # Annual capital expenditure


@dataclass
class SimulatedPeriodResult:
    """Calculated financial metrics and ratios for a simulated period."""
    period_label: str
    period_year: int
    revenue: float
    cogs: float
    gross_profit: float
    operating_expenses: float
    operating_profit: float
    interest_expense: float
    tax_expense: float
    net_profit: float
    current_assets: float
    inventory: float
    current_liabilities: float
    working_capital: float
    total_debt: float
    total_equity: float
    total_assets: float
    total_liabilities: float
    # Calculated Ratios
    gross_profit_margin_pct: Optional[float]
    operating_margin_pct: Optional[float]
    net_profit_margin_pct: Optional[float]
    current_ratio: Optional[float]
    quick_ratio: Optional[float]
    debt_to_equity: Optional[float]
    debt_ratio: Optional[float]


@dataclass
class ScenarioSimulationResult:
    """Complete multi-period simulation result for one scenario."""
    scenario_name: str
    assumptions: ScenarioAssumptions
    base_period: str
    periods: List[SimulatedPeriodResult]
    summary_deltas: Dict[str, Any] = field(default_factory=dict)


class FinancialScenarioSimulator:
    """
    Deterministic multi-period financial scenario simulator.
    """

    def __init__(self):
        pass

    def simulate_scenario(
        self,
        base_metrics: Dict[str, float],
        assumptions: ScenarioAssumptions,
        horizon_years: int = 3,
        base_period_name: str = "FY2023",
    ) -> ScenarioSimulationResult:
        """
        Run multi-period deterministic simulation starting from baseline historical metrics.
        """
        # Baseline starting values
        rev = float(base_metrics.get("revenue", 100_000_000))
        op_prof = float(base_metrics.get("operating_profit", 15_000_000))
        net_prof = float(base_metrics.get("net_profit", 10_000_000))
        cogs = float(base_metrics.get("cogs", rev * (assumptions.cogs_pct_of_revenue / 100.0)))
        opex = float(base_metrics.get("operating_expenses", max(1.0, rev - cogs - op_prof)))

        ca = float(base_metrics.get("current_assets", 50_000_000))
        cl = float(base_metrics.get("current_liabilities", 30_000_000))
        inv = float(base_metrics.get("inventory", ca * (assumptions.inventory_pct_of_ca / 100.0)))
        debt = float(base_metrics.get("total_debt", 25_000_000))
        equity = float(base_metrics.get("total_equity", 60_000_000))
        assets = float(base_metrics.get("total_assets", ca + 70_000_000))
        non_current_assets = max(0.0, assets - ca)
        liab = float(base_metrics.get("total_liabilities", cl + debt))

        # Parse base year
        digits = "".join(c for c in base_period_name if c.isdigit())
        start_year = int(digits) if digits and len(digits) == 4 else 2023

        periods: List[SimulatedPeriodResult] = []

        curr_rev = rev
        curr_opex = opex
        curr_ca = ca
        curr_cl = cl
        curr_debt = debt + assumptions.proposed_debt_change
        curr_equity = equity + assumptions.proposed_equity_change

        g_rev = assumptions.revenue_growth_pct / 100.0
        g_opex = assumptions.opex_growth_pct / 100.0
        g_ca = getattr(assumptions, "current_assets_growth_pct", 4.0) / 100.0
        g_cl = (getattr(assumptions, "current_liabilities_growth_pct", None) if getattr(assumptions, "current_liabilities_growth_pct", None) is not None else getattr(assumptions, "current_liab_growth_pct", 4.0)) / 100.0
        cogs_rate = assumptions.cogs_pct_of_revenue / 100.0
        tax_rate = assumptions.tax_rate_pct / 100.0
        interest_rate = assumptions.interest_rate_pct / 100.0

        for year_step in range(1, horizon_years + 1):
            year_num = start_year + year_step
            period_lbl = f"FY{year_num} (Simulated)"

            # Step 1: Revenue projection
            curr_rev = curr_rev * (1.0 + g_rev)

            # Step 2: Direct Costs & Gross Profit
            step_cogs = curr_rev * cogs_rate
            step_gp = curr_rev - step_cogs

            # Step 3: Operating Expenses & Operating Profit
            curr_opex = curr_opex * (1.0 + g_opex)
            step_ebit = step_gp - curr_opex

            # Step 4: Interest & Tax
            step_interest = max(0.0, curr_debt * interest_rate)
            ebt = step_ebit - step_interest
            step_tax = max(0.0, ebt * tax_rate) if ebt > 0 else 0.0
            step_net_profit = ebt - step_tax

            # Step 5: Working Capital & Balance Sheet items
            curr_ca = curr_ca * (1.0 + g_ca)
            curr_cl = curr_cl * (1.0 + g_cl)
            step_wc = curr_ca - curr_cl
            step_inv = curr_ca * (assumptions.inventory_pct_of_ca / 100.0)

            # Equity increases by net profit retained
            curr_equity = curr_equity + step_net_profit
            step_total_assets = curr_ca + non_current_assets
            step_total_liab = curr_cl + curr_debt

            # Step 6: Recalculate Ratios using centralized formula engine
            eval_gpm = calculate_gross_profit_margin(curr_rev, step_cogs, step_gp)
            eval_opm = calculate_operating_profit_margin(step_ebit, curr_rev)
            eval_npm = calculate_net_profit_margin(step_net_profit, curr_rev)
            eval_cr = calculate_current_ratio(curr_ca, curr_cl)
            eval_qr = calculate_quick_ratio(curr_ca, step_inv, curr_cl)
            eval_de = calculate_debt_to_equity(curr_debt, curr_equity)
            eval_dr = calculate_debt_ratio(step_total_liab, step_total_assets)

            periods.append(
                SimulatedPeriodResult(
                    period_label=period_lbl,
                    period_year=year_num,
                    revenue=curr_rev,
                    cogs=step_cogs,
                    gross_profit=step_gp,
                    operating_expenses=curr_opex,
                    operating_profit=step_ebit,
                    interest_expense=step_interest,
                    tax_expense=step_tax,
                    net_profit=step_net_profit,
                    current_assets=curr_ca,
                    inventory=step_inv,
                    current_liabilities=curr_cl,
                    working_capital=step_wc,
                    total_debt=curr_debt,
                    total_equity=curr_equity,
                    total_assets=step_total_assets,
                    total_liabilities=step_total_liab,
                    gross_profit_margin_pct=eval_gpm.result,
                    operating_margin_pct=eval_opm.result,
                    net_profit_margin_pct=eval_npm.result,
                    current_ratio=eval_cr.result,
                    quick_ratio=eval_qr.result,
                    debt_to_equity=eval_de.result,
                    debt_ratio=eval_dr.result,
                )
            )

        # Calculate deltas from year 1 to end of horizon
        if periods:
            first_p = periods[0]
            last_p = periods[-1]
            rev_delta_pct = ((last_p.revenue - rev) / abs(rev)) * 100 if rev else 0.0
            profit_delta_pct = ((last_p.net_profit - net_prof) / abs(net_prof)) * 100 if net_prof else 0.0

            summary_deltas = {
                "initial_revenue": rev,
                "final_revenue": last_p.revenue,
                "revenue_total_growth_pct": rev_delta_pct,
                "initial_net_profit": net_prof,
                "final_net_profit": last_p.net_profit,
                "net_profit_total_growth_pct": profit_delta_pct,
                "final_current_ratio": last_p.current_ratio,
                "final_debt_to_equity": last_p.debt_to_equity,
            }
        else:
            summary_deltas = {}

        return ScenarioSimulationResult(
            scenario_name=assumptions.scenario_name,
            assumptions=assumptions,
            base_period=base_period_name,
            periods=periods,
            summary_deltas=summary_deltas,
        )

    def run_three_scenarios(
        self,
        base_metrics: Dict[str, float],
        base_period_name: str = "FY2023",
        horizon_years: int = 3,
        custom_base: Optional[ScenarioAssumptions] = None,
        custom_opt: Optional[ScenarioAssumptions] = None,
        custom_pess: Optional[ScenarioAssumptions] = None,
    ) -> Dict[str, ScenarioSimulationResult]:
        """
        Run side-by-side Base, Optimistic, and Pessimistic scenarios.
        """
        # Default or custom assumptions
        base_asm = custom_base or ScenarioAssumptions(
            scenario_name="Base Case",
            revenue_growth_pct=6.0,
            opex_growth_pct=5.0,
            cogs_pct_of_revenue=48.0,
            tax_rate_pct=21.0,
            interest_rate_pct=5.0,
            proposed_debt_change=0.0,
            proposed_equity_change=0.0,
            current_assets_growth_pct=5.0,
            current_liab_growth_pct=4.5,
        )

        opt_asm = custom_opt or ScenarioAssumptions(
            scenario_name="Optimistic Case",
            revenue_growth_pct=14.0,
            opex_growth_pct=7.0,
            cogs_pct_of_revenue=44.0,
            tax_rate_pct=21.0,
            interest_rate_pct=4.5,
            proposed_debt_change=-5_000_000,  # Pay down debt
            proposed_equity_change=10_000_000,  # Equity investment
            current_assets_growth_pct=10.0,
            current_liab_growth_pct=5.0,
        )

        pess_asm = custom_pess or ScenarioAssumptions(
            scenario_name="Pessimistic Case",
            revenue_growth_pct=-4.0,
            opex_growth_pct=4.0,
            cogs_pct_of_revenue=54.0,
            tax_rate_pct=21.0,
            interest_rate_pct=7.0,
            proposed_debt_change=10_000_000,  # Draw down credit facility
            proposed_equity_change=0.0,
            current_assets_growth_pct=-2.0,
            current_liab_growth_pct=6.0,
        )

        results = {
            "Base Case": self.simulate_scenario(base_metrics, base_asm, horizon_years, base_period_name),
            "Optimistic Case": self.simulate_scenario(base_metrics, opt_asm, horizon_years, base_period_name),
            "Pessimistic Case": self.simulate_scenario(base_metrics, pess_asm, horizon_years, base_period_name),
        }
        return results


def plot_scenario_comparison(
    scenario_results: Dict[str, ScenarioSimulationResult],
    metric_attr: str = "revenue",
    metric_title: str = "Simulated Revenue",
    unit: str = "$",
) -> go.Figure:
    """
    Plot interactive comparative lines for Base, Optimistic, and Pessimistic scenarios.
    """
    fig = go.Figure()

    colors = {
        "Base Case": PALETTE["navy_primary"],
        "Optimistic Case": PALETTE["green_accent"],
        "Pessimistic Case": PALETTE["coral_accent"],
    }

    dash_styles = {
        "Base Case": "solid",
        "Optimistic Case": "dash",
        "Pessimistic Case": "dot",
    }

    for name, res in scenario_results.items():
        x_vals = [p.period_label for p in res.periods]
        y_vals = [getattr(p, metric_attr, 0.0) for p in res.periods]

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines+markers",
                name=name,
                line=dict(
                    color=colors.get(name, PALETTE["navy_primary"]),
                    width=3 if name == "Base Case" else 2.5,
                    dash=dash_styles.get(name, "solid"),
                ),
                marker=dict(size=8),
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:,.2f}} {unit}<extra></extra>",
            )
        )

    fig.update_layout(
        **CHART_LAYOUT_DEFAULTS,
        title=dict(text=f"What-If Scenario Simulation: {metric_title}", font=dict(size=14, color=PALETTE["navy_primary"])),
        height=380,
        xaxis=dict(title="Simulated Period", showgrid=True, gridcolor="#EDF2F7"),
        yaxis=dict(title=f"{metric_title} ({unit})", showgrid=True, gridcolor="#EDF2F7"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
