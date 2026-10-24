"""
FIN SIGHT AI - Test Suite for Agent Telemetry & Persistent SQLite Evaluation
Verifies recording, aggregate metric calculations, filtering, and benchmark results.
"""
import tempfile
from pathlib import Path
import pytest

from src.monitoring.agent_telemetry import (
    AgentTelemetryStore,
    AgentExecutionRecord,
)


class TestAgentTelemetry:
    """Test suite for agent telemetry and quality benchmarks."""

    @pytest.fixture
    def test_store(self):
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_telemetry.db"
        store = AgentTelemetryStore(db_path=db_path)
        yield store

    def test_record_and_aggregate_metrics(self, test_store: AgentTelemetryStore):
        # Record 2 successful runs and 1 failed run for ratio_agent
        records = [
            AgentExecutionRecord(
                run_id="run_1",
                agent_name="ratio_agent",
                start_time="2026-10-23T10:00:00",
                end_time="2026-10-23T10:00:01",
                duration_seconds=0.25,
                status="completed",
                query="Calculate current ratio",
                validation_passed=True,
                claims_count=1,
                supported_claims_count=1,
                evidence_coverage_pct=100.0,
            ),
            AgentExecutionRecord(
                run_id="run_2",
                agent_name="ratio_agent",
                start_time="2026-10-23T10:01:00",
                end_time="2026-10-23T10:01:01",
                duration_seconds=0.35,
                status="completed",
                query="Calculate net margin",
                validation_passed=True,
                claims_count=1,
                supported_claims_count=1,
                evidence_coverage_pct=100.0,
            ),
            AgentExecutionRecord(
                run_id="run_3",
                agent_name="ratio_agent",
                start_time="2026-10-23T10:02:00",
                end_time="2026-10-23T10:02:01",
                duration_seconds=0.45,
                status="failed",
                query="Invalid metric query",
                validation_passed=False,
                error_message="Missing metric",
            ),
        ]

        for r in records:
            test_store.record_agent_execution(r)

        metrics = test_store.get_agent_metrics("ratio_agent")
        assert len(metrics) == 1
        m = metrics[0]

        assert m.total_executions == 3
        assert m.successful_executions == 2
        assert m.failed_executions == 1
        assert pytest.approx(m.success_rate_pct, 0.1) == 66.7
        assert pytest.approx(m.avg_duration_seconds, 0.01) == 0.35
        assert pytest.approx(m.median_duration_seconds, 0.01) == 0.35
        assert pytest.approx(m.validation_pass_rate_pct, 0.1) == 66.7

    def test_evaluation_benchmark_lifecycle(self, test_store: AgentTelemetryStore):
        test_store.record_evaluation_result(
            case_id="CASE_01_REVENUE_GROWTH",
            passed=True,
            numerical_accuracy=1.0,
            formula_correct=True,
            evidence_attributed=True,
            unsupported_claims_found=0,
            latency_seconds=0.45,
            notes="Evaluated successfully",
        )

        history = test_store.get_evaluation_history()
        assert len(history) == 1
        assert history[0]["case_id"] == "CASE_01_REVENUE_GROWTH"
        assert history[0]["passed"] == 1
        assert history[0]["unsupported_claims_found"] == 0
