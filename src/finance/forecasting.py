"""
FIN SIGHT AI - Machine Learning Financial Forecasting
Provides chronological time-series forecasting, backtesting, model comparison,
evaluation metrics (MAE, RMSE, MAPE, WAPE, Bias), and confidence intervals.
NEVER fabricates data or uses random splits on time-series.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

try:
    from statsmodels.tsa.api import Holt, SimpleExpSmoothing
    from statsmodels.tsa.arima.model import ARIMA
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

from src.ui.theme import CHART_LAYOUT_DEFAULTS, PALETTE
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

FORECASTABLE_METRICS = [
    "revenue",
    "operating_expenses",
    "operating_profit",
    "net_profit",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "operating_cash_flow",
    "net_profit_margin",
]


@dataclass
class BacktestMetrics:
    """Chronological evaluation metrics for a single model."""
    model_name: str
    mae: float
    rmse: float
    mape: Optional[float]  # None if division by zero occurred
    wape: float
    forecast_bias: float
    validation_periods: List[str]
    actual_values: List[float]
    predicted_values: List[float]
    beat_baseline: bool = False
    notes: str = ""


@dataclass
class ForecastResult:
    """Complete forecasting result container."""
    metric_name: str
    metric_display_name: str
    selected_model: str
    forecast_horizon: int
    historical_periods: List[str]
    historical_values: List[float]
    forecast_periods: List[str]
    forecast_values: List[float]
    confidence_interval_80_lower: List[float]
    confidence_interval_80_upper: List[float]
    confidence_interval_95_lower: List[float]
    confidence_interval_95_upper: List[float]
    model_evaluations: List[BacktestMetrics]
    is_data_sufficient: bool
    insufficiency_reason: str = ""
    limitations: List[str] = field(default_factory=list)
    unit: str = "currency"  # or "%"


class FinancialForecaster:
    """
    Chronological time series financial forecasting pipeline.
    """

    def __init__(self):
        self.min_samples_for_baseline = 2
        self.min_samples_for_linear = 3
        self.min_samples_for_advanced = 4

    @staticmethod
    def _calculate_metrics(
        actuals: np.ndarray, preds: np.ndarray, model_name: str
    ) -> BacktestMetrics:
        """Calculate MAE, RMSE, MAPE, WAPE, and Bias."""
        errors = preds - actuals
        abs_errors = np.abs(errors)

        mae = float(np.mean(abs_errors))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        bias = float(np.mean(errors))

        # WAPE: sum(|e|) / sum(|y|) * 100
        sum_actuals = float(np.sum(np.abs(actuals)))
        wape = float((np.sum(abs_errors) / sum_actuals) * 100) if sum_actuals > 0 else 0.0

        # MAPE: handle 0 in actuals
        if np.any(actuals == 0):
            mape = None
            notes = "MAPE undefined due to zero value in historical actuals."
        else:
            pct_errors = np.abs(errors / actuals)
            mape = float(np.mean(pct_errors) * 100)
            notes = "Standard percentage error."

        return BacktestMetrics(
            model_name=model_name,
            mae=mae,
            rmse=rmse,
            mape=mape,
            wape=wape,
            forecast_bias=bias,
            validation_periods=[],
            actual_values=actuals.tolist(),
            predicted_values=preds.tolist(),
            notes=notes,
        )

    # ---------------------------------------------------------------------- #
    # Individual Algorithms
    # ---------------------------------------------------------------------- #

    def _fit_predict_naive(self, train: np.ndarray, horizon: int) -> np.ndarray:
        """Naive baseline: repeat last known observation."""
        last_val = train[-1]
        return np.full(horizon, last_val)

    def _fit_predict_moving_average(self, train: np.ndarray, horizon: int, window: int = 2) -> np.ndarray:
        """Moving average baseline: average of last k observations."""
        k = min(window, len(train))
        ma_val = float(np.mean(train[-k:]))
        return np.full(horizon, ma_val)

    def _fit_predict_linear(self, train: np.ndarray, horizon: int) -> np.ndarray:
        """Linear regression trend projection: y = alpha + beta * t."""
        n = len(train)
        X = np.arange(n).reshape(-1, 1)
        y = train
        model = LinearRegression().fit(X, y)
        X_future = np.arange(n, n + horizon).reshape(-1, 1)
        preds = model.predict(X_future)
        return preds

    def _fit_predict_exponential_smoothing(self, train: np.ndarray, horizon: int) -> np.ndarray:
        """Exponential Smoothing (Holt's linear trend if n >= 3, or Simple ETS)."""
        if HAS_STATSMODELS and len(train) >= 3:
            try:
                # Use Holt's linear trend
                model = Holt(train, initialization_method="estimated").fit(optimized=True)
                preds = model.forecast(horizon)
                return np.array(preds)
            except Exception:
                pass

        if HAS_STATSMODELS and len(train) >= 2:
            try:
                model = SimpleExpSmoothing(train, initialization_method="estimated").fit(optimized=True)
                return np.array(model.forecast(horizon))
            except Exception:
                pass

        # Robust analytical fallback: exponential smoothing with alpha=0.5
        alpha = 0.5
        s = train[0]
        for t in range(1, len(train)):
            s = alpha * train[t] + (1 - alpha) * s
        return np.full(horizon, s)

    def _fit_predict_arima(self, train: np.ndarray, horizon: int) -> Optional[np.ndarray]:
        """ARIMA(1,1,0) or AR(1) time series model."""
        if not HAS_STATSMODELS or len(train) < 4:
            return None
        try:
            model = ARIMA(train, order=(1, 1, 0)).fit()
            preds = model.forecast(steps=horizon)
            return np.array(preds)
        except Exception:
            try:
                model = ARIMA(train, order=(1, 0, 0)).fit()
                return np.array(model.forecast(steps=horizon))
            except Exception:
                return None

    def _fit_predict_random_forest(self, train: np.ndarray, horizon: int) -> Optional[np.ndarray]:
        """Random Forest regressor with lag-1 and lag-2 features."""
        if len(train) < 5:
            return None
        try:
            # Build autoregressive lags
            X_lags, y_target = [], []
            for i in range(2, len(train)):
                X_lags.append([train[i - 1], train[i - 2]])
                y_target.append(train[i])

            rf = RandomForestRegressor(n_estimators=50, random_state=42)
            rf.fit(X_lags, y_target)

            # Iterative multi-step forecasting
            history = list(train)
            preds = []
            for _ in range(horizon):
                feat = np.array([[history[-1], history[-2]]])
                pred_step = float(rf.predict(feat)[0])
                preds.append(pred_step)
                history.append(pred_step)

            return np.array(preds)
        except Exception:
            return None

    # ---------------------------------------------------------------------- #
    # Chronological Backtesting & Model Selection
    # ---------------------------------------------------------------------- #

    def backtest_and_select(
        self,
        values: np.ndarray,
        periods: List[str],
        requested_model: str = "Auto (Best Backtest)",
        horizon: int = 1,
    ) -> Tuple[str, List[BacktestMetrics], Optional[float]]:
        """
        Chronologically splits history into train and validation (holding out the last 1-2 periods).
        Evaluates candidate models and selects the top performer.
        Returns: (best_model_name, evaluation_metrics_list, residual_std)
        """
        n = len(values)
        if n < self.min_samples_for_baseline:
            return "Insufficient Data", [], None

        # Hold out last 1 period for validation (or 2 if n >= 6)
        val_size = 2 if n >= 6 else 1
        train = values[:-val_size]
        val = values[-val_size:]
        val_periods = periods[-val_size:]

        evaluations: List[BacktestMetrics] = []

        # 1. Naive Baseline
        pred_naive = self._fit_predict_naive(train, val_size)
        metrics_naive = self._calculate_metrics(val, pred_naive, "Naive Baseline (Last Value)")
        metrics_naive.validation_periods = val_periods
        metrics_naive.beat_baseline = True  # Baseline reference
        evaluations.append(metrics_naive)

        # 2. Moving Average
        if len(train) >= 2:
            pred_ma = self._fit_predict_moving_average(train, val_size, window=2)
            m_ma = self._calculate_metrics(val, pred_ma, "Moving Average (k=2)")
            m_ma.validation_periods = val_periods
            m_ma.beat_baseline = m_ma.mae < metrics_naive.mae
            evaluations.append(m_ma)

        # 3. Linear Regression Trend
        if len(train) >= self.min_samples_for_linear:
            pred_lr = self._fit_predict_linear(train, val_size)
            m_lr = self._calculate_metrics(val, pred_lr, "Linear Trend Regression")
            m_lr.validation_periods = val_periods
            m_lr.beat_baseline = m_lr.mae < metrics_naive.mae
            evaluations.append(m_lr)

        # 4. Exponential Smoothing
        if len(train) >= 2:
            pred_ets = self._fit_predict_exponential_smoothing(train, val_size)
            m_ets = self._calculate_metrics(val, pred_ets, "Exponential Smoothing (ETS/Holt)")
            m_ets.validation_periods = val_periods
            m_ets.beat_baseline = m_ets.mae < metrics_naive.mae
            evaluations.append(m_ets)

        # 5. ARIMA
        if len(train) >= 4 and HAS_STATSMODELS:
            pred_arima = self._fit_predict_arima(train, val_size)
            if pred_arima is not None:
                m_arima = self._calculate_metrics(val, pred_arima, "ARIMA (1,1,0)")
                m_arima.validation_periods = val_periods
                m_arima.beat_baseline = m_arima.mae < metrics_naive.mae
                evaluations.append(m_arima)

        # 6. Random Forest
        if len(train) >= 5:
            pred_rf = self._fit_predict_random_forest(train, val_size)
            if pred_rf is not None:
                m_rf = self._calculate_metrics(val, pred_rf, "Random Forest Regressor")
                m_rf.validation_periods = val_periods
                m_rf.beat_baseline = m_rf.mae < metrics_naive.mae
                evaluations.append(m_rf)

        # Model selection: Pick lowest MAE among evaluated models
        sorted_models = sorted(evaluations, key=lambda x: x.mae)
        best_model = sorted_models[0].model_name

        # If user explicitly requested a specific model (other than Auto), respect selection
        if requested_model != "Auto (Best Backtest)":
            matched = next((m for m in evaluations if requested_model.lower() in m.model_name.lower()), None)
            if matched:
                selected = matched.model_name
            else:
                selected = best_model
        else:
            selected = best_model

        # Calculate residual standard error for confidence intervals
        best_eval = next(m for m in evaluations if m.model_name == selected)
        residuals = np.array(best_eval.predicted_values) - np.array(best_eval.actual_values)
        residual_std = float(np.std(residuals)) if len(residuals) > 1 else float(best_eval.mae * 1.25)

        return selected, evaluations, residual_std

    # ---------------------------------------------------------------------- #
    # Master Forecast Pipeline
    # ---------------------------------------------------------------------- #

    def forecast_metric(
        self,
        historical_periods: List[str],
        historical_values: List[float],
        metric_name: str,
        metric_display_name: str,
        forecast_horizon: int = 2,
        model_name: str = "Auto (Best Backtest)",
        unit: str = "currency",
    ) -> ForecastResult:
        """
        Execute machine learning forecasting on historical financial observations.
        """
        # Validate data
        clean_pairs = [
            (p, v) for p, v in zip(historical_periods, historical_values)
            if v is not None and not math.isnan(v)
        ]

        if len(clean_pairs) < self.min_samples_for_baseline:
            return ForecastResult(
                metric_name=metric_name,
                metric_display_name=metric_display_name,
                selected_model="None",
                forecast_horizon=forecast_horizon,
                historical_periods=[p for p, _ in clean_pairs],
                historical_values=[v for _, v in clean_pairs],
                forecast_periods=[],
                forecast_values=[],
                confidence_interval_80_lower=[],
                confidence_interval_80_upper=[],
                confidence_interval_95_lower=[],
                confidence_interval_95_upper=[],
                model_evaluations=[],
                is_data_sufficient=False,
                insufficiency_reason=(
                    f"Insufficient historical data: Only {len(clean_pairs)} period(s) available. "
                    f"Machine learning time-series training requires at least {self.min_samples_for_baseline} observations "
                    f"for baseline and {self.min_samples_for_linear}+ observations for statistical regression."
                ),
                limitations=[
                    "Cannot train ML models without sufficient historical periods.",
                    "Annual financial reports typically require multi-year continuous statements.",
                    "Use deterministic Scenario Simulation to model what-if forward expectations instead.",
                ],
                unit=unit,
            )

        periods = [p for p, _ in clean_pairs]
        vals = np.array([v for _, v in clean_pairs], dtype=float)

        # Model evaluation & selection via chronological backtest
        selected_model, evaluations, residual_std = self.backtest_and_select(
            vals, periods, requested_model=model_name, horizon=forecast_horizon
        )

        # Generate future periods labels
        last_period = periods[-1]
        future_periods = []
        try:
            # Try parsing FY2023 or 2023
            digits = "".join(c for c in last_period if c.isdigit())
            if digits and len(digits) == 4:
                year = int(digits)
                prefix = last_period.replace(digits, "")
                for h in range(1, forecast_horizon + 1):
                    future_periods.append(f"{prefix}{year + h} (Forecast)")
            else:
                for h in range(1, forecast_horizon + 1):
                    future_periods.append(f"Period +{h} (Forecast)")
        except Exception:
            for h in range(1, forecast_horizon + 1):
                future_periods.append(f"T+{h} (Forecast)")

        # Fit model on ALL available data to generate final forward forecasts
        if "naive" in selected_model.lower():
            final_preds = self._fit_predict_naive(vals, forecast_horizon)
        elif "moving average" in selected_model.lower():
            final_preds = self._fit_predict_moving_average(vals, forecast_horizon, window=2)
        elif "linear" in selected_model.lower():
            final_preds = self._fit_predict_linear(vals, forecast_horizon)
        elif "exponential" in selected_model.lower():
            final_preds = self._fit_predict_exponential_smoothing(vals, forecast_horizon)
        elif "arima" in selected_model.lower():
            preds = self._fit_predict_arima(vals, forecast_horizon)
            final_preds = preds if preds is not None else self._fit_predict_linear(vals, forecast_horizon)
        elif "random forest" in selected_model.lower():
            preds = self._fit_predict_random_forest(vals, forecast_horizon)
            final_preds = preds if preds is not None else self._fit_predict_linear(vals, forecast_horizon)
        else:
            final_preds = self._fit_predict_naive(vals, forecast_horizon)

        # Calculate prediction intervals: z_80 = 1.282, z_95 = 1.960
        std = residual_std if (residual_std is not None and residual_std > 0) else float(np.std(vals) * 0.1)
        ci_80_lower, ci_80_upper = [], []
        ci_95_lower, ci_95_upper = [], []

        for step_idx, pred_val in enumerate(final_preds):
            horizon_multiplier = math.sqrt(1 + (step_idx + 1) / len(vals))
            margin_80 = 1.282 * std * horizon_multiplier
            margin_95 = 1.960 * std * horizon_multiplier

            ci_80_lower.append(float(pred_val - margin_80))
            ci_80_upper.append(float(pred_val + margin_80))
            ci_95_lower.append(float(pred_val - margin_95))
            ci_95_upper.append(float(pred_val + margin_95))

        limitations = [
            "Financial forecasts are estimates based on historical patterns, not guaranteed future outcomes.",
            "Macroeconomic shifts, regulatory changes, or unmodeled shocks are not reflected in pure time-series extrapolation.",
            "Small sample sizes (<10 observations) widen confidence interval bounds substantially.",
        ]

        # Check if baseline beat the selected model
        baseline_eval = next((e for e in evaluations if "naive" in e.model_name.lower()), None)
        selected_eval = next((e for e in evaluations if e.model_name == selected_model), None)
        if baseline_eval and selected_eval and baseline_eval.mae < selected_eval.mae and "naive" not in selected_model.lower():
            limitations.append(
                f"Note: Naive Baseline achieved lower historical backtest error ({baseline_eval.mae:.2f}) than {selected_model} ({selected_eval.mae:.2f})."
            )

        return ForecastResult(
            metric_name=metric_name,
            metric_display_name=metric_display_name,
            selected_model=selected_model,
            forecast_horizon=forecast_horizon,
            historical_periods=periods,
            historical_values=vals.tolist(),
            forecast_periods=future_periods,
            forecast_values=final_preds.tolist(),
            confidence_interval_80_lower=ci_80_lower,
            confidence_interval_80_upper=ci_80_upper,
            confidence_interval_95_lower=ci_95_lower,
            confidence_interval_95_upper=ci_95_upper,
            model_evaluations=evaluations,
            is_data_sufficient=True,
            limitations=limitations,
            unit=unit,
        )


def plot_financial_forecast(result: ForecastResult) -> go.Figure:
    """
    Generate an enterprise light-theme Plotly chart displaying historical actuals,
    predicted future points, and confidence interval cones.
    """
    fig = go.Figure()

    if not result.is_data_sufficient or not result.historical_periods:
        fig.add_annotation(
            text="Insufficient historical observations for ML forecasting.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color=PALETTE["text_muted"])
        )
        fig.update_layout(**CHART_LAYOUT_DEFAULTS, height=350)
        return fig

    # 1. Historical Actuals (Solid Blue Line + Circle Markers)
    fig.add_trace(
        go.Scatter(
            x=result.historical_periods,
            y=result.historical_values,
            mode="lines+markers",
            name="Historical Actuals (Observed)",
            line=dict(color=PALETTE["navy_primary"], width=3),
            marker=dict(size=9, color=PALETTE["navy_primary"]),
            hovertemplate="<b>%{x}</b><br>Actual: %{y:,.2f}<extra></extra>",
        )
    )

    if result.forecast_periods and result.forecast_values:
        # Connect last actual point to first forecast point for seamless curve
        connect_x = [result.historical_periods[-1]] + result.forecast_periods
        connect_y = [result.historical_values[-1]] + result.forecast_values
        connect_ci95_low = [result.historical_values[-1]] + result.confidence_interval_95_lower
        connect_ci95_up = [result.historical_values[-1]] + result.confidence_interval_95_upper
        connect_ci80_low = [result.historical_values[-1]] + result.confidence_interval_80_lower
        connect_ci80_up = [result.historical_values[-1]] + result.confidence_interval_80_upper

        # 95% Confidence Interval Band (Light Blue Transparent Fill)
        fig.add_trace(
            go.Scatter(
                x=connect_x + connect_x[::-1],
                y=connect_ci95_up + connect_ci95_low[::-1],
                fill="toself",
                fillcolor="rgba(33, 150, 243, 0.12)",
                line=dict(color="rgba(255,255,255,0)"),
                name="95% Confidence Interval",
                hoverinfo="skip",
                showlegend=True,
            )
        )

        # 80% Confidence Interval Band (Slightly Darker Transparent Fill)
        fig.add_trace(
            go.Scatter(
                x=connect_x + connect_x[::-1],
                y=connect_ci80_up + connect_ci80_low[::-1],
                fill="toself",
                fillcolor="rgba(33, 150, 243, 0.20)",
                line=dict(color="rgba(255,255,255,0)"),
                name="80% Confidence Interval",
                hoverinfo="skip",
                showlegend=True,
            )
        )

        # Forecast Points (Dashed Amber/Teal Line + Diamond Markers)
        fig.add_trace(
            go.Scatter(
                x=connect_x,
                y=connect_y,
                mode="lines+markers",
                name=f"Forecast: {result.selected_model}",
                line=dict(color=PALETTE["gold_accent"], width=3, dash="dash"),
                marker=dict(size=10, symbol="diamond", color=PALETTE["gold_accent"]),
                hovertemplate="<b>%{x}</b><br>Forecast: %{y:,.2f}<extra></extra>",
            )
        )

    title_text = f"{result.metric_display_name} — Historical Trend & ML Forecast ({result.selected_model})"
    fig.update_layout(
        **CHART_LAYOUT_DEFAULTS,
        title=dict(text=title_text, font=dict(size=14, color=PALETTE["navy_primary"])),
        height=400,
        xaxis=dict(title="Reporting Period", showgrid=True, gridcolor="#EDF2F7"),
        yaxis=dict(title=f"{result.metric_display_name} ({result.unit})", showgrid=True, gridcolor="#EDF2F7"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig
