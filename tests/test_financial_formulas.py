"""
FIN SIGHT AI - Test Suite for Centralized Financial Formulas
Verifies all 12 financial formulas, edge cases, negative/zero values, and step-by-step arithmetic.
"""
import pytest

from src.finance.financial_formulas import (
    calculate_revenue_growth,
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_gross_profit_margin,
    calculate_current_ratio,
    calculate_quick_ratio,
    calculate_debt_to_equity,
    calculate_debt_ratio,
    calculate_return_on_assets,
    calculate_return_on_equity,
    calculate_working_capital,
    calculate_operating_cash_flow_ratio,
    evaluate_all_formulas,
)


class TestFinancialFormulas:
    """Test suite for pure Python financial calculations."""

    def test_revenue_growth_normal(self):
        res = calculate_revenue_growth(124.8, 108.5)
        assert res.is_valid is True
        assert res.result is not None
        assert pytest.approx(res.result, 0.01) == 15.02
        assert res.unit == "%"
        assert "15.02%" in res.step_by_step

    def test_revenue_growth_zero_prior(self):
        res = calculate_revenue_growth(100.0, 0.0)
        assert res.is_valid is False
        assert res.result is None
        assert "zero" in res.error_message.lower()

    def test_revenue_growth_missing_inputs(self):
        res = calculate_revenue_growth(None, 100.0)
        assert res.is_valid is False
        assert res.result is None

    def test_net_profit_margin(self):
        res = calculate_net_profit_margin(18.2, 124.8)
        assert res.is_valid is True
        assert pytest.approx(res.result, 0.01) == 14.58
        assert res.unit == "%"

    def test_net_profit_margin_negative(self):
        res = calculate_net_profit_margin(-5.0, 100.0)
        assert res.is_valid is True
        assert res.result == -5.0
        assert "loss" in res.interpretation.lower()

    def test_operating_profit_margin(self):
        res = calculate_operating_profit_margin(23.1, 124.8)
        assert res.is_valid is True
        assert pytest.approx(res.result, 0.01) == 18.51

    def test_gross_profit_margin(self):
        res = calculate_gross_profit_margin(100.0, 60.0)
        assert res.is_valid is True
        assert res.result == 40.0

    def test_current_ratio(self):
        res = calculate_current_ratio(55.4, 28.6)
        assert res.is_valid is True
        assert pytest.approx(res.result, 0.01) == 1.94
        assert res.unit == "x"

    def test_current_ratio_zero_denominator(self):
        res = calculate_current_ratio(50.0, 0.0)
        assert res.is_valid is False
        assert res.result is None
        assert "zero" in res.error_message.lower()

    def test_quick_ratio(self):
        res = calculate_quick_ratio(50.0, 15.0, 25.0, prepaid_expenses=5.0)
        assert res.is_valid is True
        # (50 - 15 - 5) / 25 = 30 / 25 = 1.20x
        assert pytest.approx(res.result, 0.01) == 1.20

    def test_quick_ratio_missing_inventory(self):
        res = calculate_quick_ratio(50.0, None, 25.0)
        assert res.is_valid is False
        assert "inventory" in res.error_message.lower()

    def test_debt_to_equity(self):
        res = calculate_debt_to_equity(25.0, 84.0)
        assert res.is_valid is True
        assert pytest.approx(res.result, 0.01) == 0.30

    def test_debt_to_equity_negative_equity(self):
        res = calculate_debt_to_equity(50.0, -10.0)
        assert res.is_valid is True
        assert "negative" in res.interpretation.lower()

    def test_debt_ratio(self):
        res = calculate_debt_ratio(60.0, 120.0)
        assert res.is_valid is True
        assert res.result == 0.50

    def test_return_on_assets_with_average(self):
        res = calculate_return_on_assets(15.0, closing_assets=110.0, opening_assets=90.0)
        assert res.is_valid is True
        # Average assets = 100.0, ROA = 15.0 / 100.0 * 100 = 15.0%
        assert res.result == 15.0
        assert "average" in res.assumptions.lower()

    def test_return_on_equity_with_closing_only(self):
        res = calculate_return_on_equity(20.0, closing_equity=100.0, opening_equity=None)
        assert res.is_valid is True
        assert res.result == 20.0
        assert "closing" in res.assumptions.lower()

    def test_working_capital(self):
        res = calculate_working_capital(55.4, 28.6)
        assert res.is_valid is True
        assert pytest.approx(res.result, 0.01) == 26.80
        assert res.unit == "currency"

    def test_operating_cash_flow_ratio(self):
        res = calculate_operating_cash_flow_ratio(26.4, 28.6)
        assert res.is_valid is True
        assert pytest.approx(res.result, 0.01) == 0.92

    def test_evaluate_all_formulas_batch(self):
        metrics = {
            "revenue": 100.0,
            "prior_revenue": 80.0,
            "net_profit": 15.0,
            "operating_profit": 20.0,
            "cogs": 50.0,
            "current_assets": 60.0,
            "current_liabilities": 30.0,
            "inventory": 10.0,
            "total_debt": 20.0,
            "total_equity": 80.0,
            "total_assets": 120.0,
            "total_liabilities": 40.0,
            "operating_cash_flow": 25.0,
        }
        all_evals = evaluate_all_formulas(metrics, period="FY2023")
        assert len(all_evals) == 12
        assert all_evals["Revenue Growth"].is_valid is True
        assert all_evals["Current Ratio"].result == 2.0
        assert all_evals["Working Capital"].result == 30.0
