"""
FIN SIGHT AI - Test Suite for Financial Scenario Simulator
Verifies deterministic multi-period simulations across Base, Optimistic, and Pessimistic cases.
"""
import pytest

from src.finance.scenario_simulator import (
    FinancialScenarioSimulator,
    ScenarioAssumptions,
    plot_scenario_comparison,
)


class TestScenarioSimulator:
    """Test suite for deterministic What-If scenario simulations."""

    @pytest.fixture
    def simulator(self):
        return FinancialScenarioSimulator()

    @pytest.fixture
    def base_data(self):
        return {
            "revenue": 100_000_000.0,
            "cogs": 50_000_000.0,
            "operating_expenses": 30_000_000.0,
            "operating_profit": 20_000_000.0,
            "net_profit": 15_000_000.0,
            "current_assets": 40_000_000.0,
            "current_liabilities": 20_000_000.0,
            "total_debt": 25_000_000.0,
            "total_equity": 60_000_000.0,
            "total_assets": 110_000_000.0,
            "total_liabilities": 50_000_000.0,
        }

    def test_single_scenario_simulation(self, simulator, base_data):
        asm = ScenarioAssumptions(
            scenario_name="Test Base",
            revenue_growth_pct=10.0,
            opex_growth_pct=5.0,
            cogs_pct_of_revenue=50.0,
        )
        res = simulator.simulate_scenario(base_data, asm, horizon_years=2, base_period_name="FY2023")

        assert res.scenario_name == "Test Base"
        assert len(res.periods) == 2
        p1 = res.periods[0]
        # Year 1 revenue: 100M * 1.10 = 110M
        assert pytest.approx(p1.revenue, 0.01) == 110_000_000.0
        # Year 1 COGS: 110M * 0.50 = 55M
        assert pytest.approx(p1.cogs, 0.01) == 55_000_000.0
        # Year 1 Gross Profit: 55M
        assert pytest.approx(p1.gross_profit, 0.01) == 55_000_000.0
        assert p1.gross_profit_margin_pct == 50.0

        p2 = res.periods[1]
        # Year 2 revenue: 110M * 1.10 = 121M
        assert pytest.approx(p2.revenue, 0.01) == 121_000_000.0

    def test_three_scenarios_comparison(self, simulator, base_data):
        results = simulator.run_three_scenarios(base_data, horizon_years=3)

        assert "Base Case" in results
        assert "Optimistic Case" in results
        assert "Pessimistic Case" in results

        base_res = results["Base Case"].periods[-1]
        opt_res = results["Optimistic Case"].periods[-1]
        pess_res = results["Pessimistic Case"].periods[-1]

        # Optimistic should deliver higher revenue than Base and Pessimistic
        assert opt_res.revenue > base_res.revenue > pess_res.revenue

        # Ratios must be recalculated deterministically
        assert opt_res.gross_profit_margin_pct is not None
        assert base_res.current_ratio is not None
        assert pess_res.debt_to_equity is not None

    def test_plot_scenario_generation(self, simulator, base_data):
        results = simulator.run_three_scenarios(base_data, horizon_years=2)
        fig = plot_scenario_comparison(results, metric_attr="revenue", metric_title="Revenue")
        assert fig is not None
        assert len(fig.data) == 3  # Base, Opt, Pess
