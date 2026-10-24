"""
FIN SIGHT AI - Test Suite for Machine Learning Financial Forecasting
Tests chronological backtesting, algorithm selection, evaluation metrics,
insufficient data handling, and prediction intervals.
"""
import pytest
import numpy as np

from src.finance.forecasting import FinancialForecaster, plot_financial_forecast


class TestFinancialForecasting:
    """Test suite for ML time-series forecasting."""

    @pytest.fixture
    def forecaster(self):
        return FinancialForecaster()

    def test_insufficient_data_behavior(self, forecaster):
        # 1 observation is insufficient for ML training
        res = forecaster.forecast_metric(
            historical_periods=["FY2023"],
            historical_values=[100.0],
            metric_name="revenue",
            metric_display_name="Revenue",
            forecast_horizon=2,
        )
        assert res.is_data_sufficient is False
        assert "insufficient" in res.insufficiency_reason.lower()
        assert len(res.forecast_values) == 0

    def test_chronological_forecast_execution(self, forecaster):
        periods = ["FY2020", "FY2021", "FY2022", "FY2023"]
        values = [80.0, 90.0, 105.0, 120.0]

        res = forecaster.forecast_metric(
            historical_periods=periods,
            historical_values=values,
            metric_name="revenue",
            metric_display_name="Revenue",
            forecast_horizon=2,
            model_name="Auto (Best Backtest)",
        )

        assert res.is_data_sufficient is True
        assert len(res.forecast_periods) == 2
        assert len(res.forecast_values) == 2
        assert len(res.confidence_interval_95_lower) == 2
        assert len(res.confidence_interval_95_upper) == 2
        assert res.confidence_interval_95_upper[0] > res.confidence_interval_95_lower[0]
        assert len(res.model_evaluations) > 0

    def test_metric_calculations_mae_rmse_wape(self, forecaster):
        actuals = np.array([100.0, 110.0, 120.0])
        preds = np.array([102.0, 108.0, 125.0])
        metrics = forecaster._calculate_metrics(actuals, preds, "Test Model")

        # errors: [+2, -2, +5], abs: [2, 2, 5], sum: 9
        # MAE = 9 / 3 = 3.0
        assert metrics.mae == 3.0
        # errors^2: [4, 4, 25] = 33 / 3 = 11, sqrt(11) = 3.3166
        assert pytest.approx(metrics.rmse, 0.01) == 3.3166
        # WAPE: 9 / 330 * 100 = 2.727%
        assert pytest.approx(metrics.wape, 0.01) == 2.727
        # Bias: (+2 -2 +5) / 3 = 1.666
        assert pytest.approx(metrics.forecast_bias, 0.01) == 1.667

    def test_naive_baseline_model(self, forecaster):
        train = np.array([50.0, 60.0, 75.0])
        preds = forecaster._fit_predict_naive(train, horizon=3)
        assert len(preds) == 3
        assert np.all(preds == 75.0)

    def test_moving_average_model(self, forecaster):
        train = np.array([50.0, 60.0, 70.0])
        # window=2 -> mean of [60, 70] = 65
        preds = forecaster._fit_predict_moving_average(train, horizon=2, window=2)
        assert len(preds) == 2
        assert np.all(preds == 65.0)

    def test_linear_trend_model(self, forecaster):
        # Strict linear trend: y = 10 + 10 * t
        train = np.array([10.0, 20.0, 30.0, 40.0])
        preds = forecaster._fit_predict_linear(train, horizon=2)
        assert len(preds) == 2
        assert pytest.approx(preds[0], 0.01) == 50.0
        assert pytest.approx(preds[1], 0.01) == 60.0

    def test_plot_generation(self, forecaster):
        res = forecaster.forecast_metric(
            historical_periods=["FY2021", "FY2022", "FY2023"],
            historical_values=[100.0, 115.0, 130.0],
            metric_name="revenue",
            metric_display_name="Revenue",
            forecast_horizon=2,
        )
        fig = plot_financial_forecast(res)
        assert fig is not None
        assert len(fig.data) >= 2  # actuals + forecast + intervals
