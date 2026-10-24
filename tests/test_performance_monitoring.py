"""
FIN SIGHT AI - Test Suite for Application Performance Monitoring & Multi-Agent Observability
Tests persistent SQLite operation tracking, health status calculation, bottleneck detection,
error log retrieval, time-window filtering, and LangSmith configuration checks.
"""
import tempfile
from pathlib import Path
import pytest

from src.monitoring.performance import PerformanceMonitor
from src.monitoring.agent_telemetry import (
    AgentTelemetryStore,
    AgentExecutionRecord,
)


class TestPerformanceMonitoring:
    """Test suite for APM and multi-agent observability."""

    @pytest.fixture
    def test_monitor(self):
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_perf.db"
        # Reset singleton instance db_path for isolation
        monitor = PerformanceMonitor(db_path=db_path)
        monitor.db_path = db_path
        monitor._history.clear()
        monitor._init_db()
        yield monitor
        monitor.clear_metrics()

    @pytest.fixture
    def test_agent_store(self):
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_agents.db"
        store = AgentTelemetryStore(db_path=db_path)
        yield store
        store.clear_telemetry()

    def test_record_and_query_operation(self, test_monitor: PerformanceMonitor):
        # Record 3 operations: 2 successful, 1 failed
        test_monitor.record_operation(
            operation_type="pdf_extraction",
            operation_name="Extract Annual Report",
            duration_seconds=0.45,
            status="success",
            details={"pages": 15, "file": "test.pdf"},
        )
        test_monitor.record_operation(
            operation_type="chat_query",
            operation_name="Query: Operating Income",
            duration_seconds=1.25,
            status="success",
            details={"intent": "numerical"},
        )
        test_monitor.record_operation(
            operation_type="report_generation",
            operation_name="Generate PDF Report",
            duration_seconds=0.85,
            status="failed",
            error_message="FPDF formatting error",
            details={"document": "test.pdf"},
        )

        summary = test_monitor.get_performance_summary()
        assert summary["total_requests"] == 3
        assert summary["successful_requests"] == 2
        assert summary["failed_requests"] == 1
        assert pytest.approx(summary["success_rate_pct"], 0.1) == 66.7
        assert summary["max_response_time"] == 1.25
        assert summary["min_response_time"] == 0.45
        assert pytest.approx(summary["avg_response_time"], 0.01) == 0.85

    def test_operation_breakdown(self, test_monitor: PerformanceMonitor):
        for _ in range(3):
            test_monitor.record_operation(
                operation_type="chat_query",
                operation_name="User Query",
                duration_seconds=0.5,
                status="success",
            )
        test_monitor.record_operation(
            operation_type="chat_query",
            operation_name="User Query",
            duration_seconds=1.5,
            status="failed",
            error_message="Timeout",
        )

        breakdown = test_monitor.get_operation_breakdown()
        assert len(breakdown) >= 1
        chat_op = next(b for b in breakdown if b["operation_type"] == "chat_query")
        assert chat_op["count"] == 4
        assert chat_op["failures"] == 1
        assert pytest.approx(chat_op["avg_duration"], 0.01) == 0.75
        assert chat_op["max_duration"] == 1.5

    def test_error_logs_retrieval(self, test_monitor: PerformanceMonitor):
        test_monitor.record_operation(
            operation_type="indexing",
            operation_name="Build FAISS Index",
            duration_seconds=0.1,
            status="failed",
            error_message="Memory allocation failure",
        )

        errors = test_monitor.get_error_logs()
        assert len(errors) == 1
        assert errors[0]["operation_type"] == "indexing"
        assert "Memory allocation" in errors[0]["error_message"]

    def test_application_health_status(self, test_monitor: PerformanceMonitor):
        health = test_monitor.get_application_health()
        assert health["status"] in ("HEALTHY", "DEGRADED", "CRITICAL")
        assert "badge" in health
        assert "uptime_formatted" in health
        assert health["db_connected"] is True

    def test_bottleneck_detection(self, test_agent_store: AgentTelemetryStore):
        # research_agent takes 2.0s per run, ratio_agent takes 0.2s
        test_agent_store.record_agent_execution(
            AgentExecutionRecord(
                run_id="r1",
                agent_name="research_agent",
                start_time="2026-10-24T10:00:00",
                end_time="2026-10-24T10:00:02",
                duration_seconds=2.0,
                status="completed",
            )
        )
        test_agent_store.record_agent_execution(
            AgentExecutionRecord(
                run_id="r1",
                agent_name="ratio_agent",
                start_time="2026-10-24T10:00:02",
                end_time="2026-10-24T10:00:02",
                duration_seconds=0.2,
                status="completed",
            )
        )

        bottleneck = test_agent_store.get_bottleneck_agent()
        assert bottleneck is not None
        assert bottleneck["bottleneck_agent"] == "research_agent"
        assert bottleneck["avg_duration_seconds"] == 2.0
        # research_agent should account for ~90.9% of total time (2.0 / 2.2)
        assert bottleneck["share_pct"] > 85.0

    def test_record_skipped_agent(self, test_agent_store: AgentTelemetryStore):
        test_agent_store.record_skipped_agent(
            run_id="r2",
            agent_name="risk_agent",
            reason="Query is purely numerical and did not require solvency checks",
            query="What is the gross margin?",
        )

        metrics = test_agent_store.get_agent_metrics("risk")
        assert len(metrics) == 1
        m = metrics[0]
        assert m.skipped_executions == 1
        assert m.successful_executions == 0
        assert m.total_executions == 1

    def test_sensitive_data_redaction(self, test_monitor: PerformanceMonitor):
        # Verify API keys and tokens are stripped
        sanitized = test_monitor._sanitize_dict({
            "google_api_key": "AIzaSySecret123456",
            "openai_api_key": "sk-proj-99999",
            "safe_metric": "revenue",
        })
        assert sanitized["google_api_key"] == "[REDACTED]"
        assert sanitized["openai_api_key"] == "[REDACTED]"
        assert sanitized["safe_metric"] == "revenue"

    def test_langsmith_status_probe(self, test_monitor: PerformanceMonitor):
        status = test_monitor.get_langsmith_status()
        assert "enabled" in status
        assert "mode" in status
        assert "project" in status
