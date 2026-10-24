"""
FIN SIGHT AI - Persistent Agent Telemetry & Evaluation Store
Stores agent execution traces, durations, success/failure counts, validation pass rates,
and evidence coverage metrics in persistent SQLite so metrics survive restarts.
Never fabricates benchmarks, random scores, or fake success rates.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = Path("data/agent_telemetry.db")


@dataclass
class AgentExecutionRecord:
    """Record of a single agent execution run."""
    run_id: str
    agent_name: str
    start_time: str
    end_time: str
    duration_seconds: float
    status: str  # "completed", "failed", "skipped"
    query: str = ""
    intent: str = ""
    input_summary: str = ""
    output_summary: str = ""
    validation_passed: bool = True
    claims_count: int = 0
    supported_claims_count: int = 0
    evidence_coverage_pct: float = 100.0
    error_message: str = ""
    company_name: str = ""
    reporting_period: str = ""
    document_id: str = ""


@dataclass
class AgentAggregateMetrics:
    """Calculated summary metrics for an agent."""
    agent_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    skipped_executions: int
    success_rate_pct: float
    avg_duration_seconds: float
    median_duration_seconds: float
    p95_duration_seconds: float
    validation_pass_rate_pct: float
    evidence_coverage_pct: float
    last_status: str
    last_run_timestamp: str


class AgentTelemetryStore:
    """
    Persistent SQLite telemetry store for all six FIN SIGHT AI agents.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize telemetry and evaluation tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    status TEXT NOT NULL,
                    query TEXT,
                    intent TEXT,
                    input_summary TEXT,
                    output_summary TEXT,
                    validation_passed INTEGER NOT NULL,
                    claims_count INTEGER DEFAULT 0,
                    supported_claims_count INTEGER DEFAULT 0,
                    evidence_coverage_pct REAL DEFAULT 100.0,
                    error_message TEXT,
                    company_name TEXT,
                    reporting_period TEXT,
                    document_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_benchmark_cases (
                    case_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    query TEXT NOT NULL,
                    expected_agent_path TEXT NOT NULL,
                    expected_metric_keys TEXT,
                    ground_truth_formula TEXT,
                    requires_citation INTEGER DEFAULT 1,
                    description TEXT
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eval_timestamp TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    numerical_accuracy REAL,
                    formula_correct INTEGER,
                    evidence_attributed INTEGER,
                    unsupported_claims_found INTEGER,
                    latency_seconds REAL,
                    notes TEXT
                )
                """
            )
            conn.commit()

        self._seed_default_benchmarks()

    def _seed_default_benchmarks(self) -> None:
        """Seed reproducible benchmark evaluation test cases if table is empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM evaluation_benchmark_cases")
            count = cursor.fetchone()[0]
            if count == 0:
                benchmarks = [
                    (
                        "CASE_01_REVENUE_GROWTH",
                        "Numerical / Ratio",
                        "What was the revenue growth of the company from FY2022 to FY2023?",
                        "intent_router->research->ratio->validation->report",
                        json.dumps(["revenue", "prior_revenue"]),
                        "((Current Revenue − Prior Revenue) / Prior Revenue) × 100",
                        1,
                        "Verifies percentage growth calculation and prior year baseline citation.",
                    ),
                    (
                        "CASE_02_CURRENT_RATIO",
                        "Liquidity",
                        "Calculate the current ratio for FY2023.",
                        "intent_router->research->ratio->validation->report",
                        json.dumps(["current_assets", "current_liabilities"]),
                        "Current Assets / Current Liabilities",
                        1,
                        "Tests current ratio and liquidity buffer interpretation.",
                    ),
                    (
                        "CASE_03_PROFIT_MARGIN",
                        "Profitability",
                        "What is the net profit margin and operating margin?",
                        "intent_router->research->ratio->validation->report",
                        json.dumps(["revenue", "net_profit", "operating_profit"]),
                        "Net Profit / Revenue × 100",
                        1,
                        "Verifies multiple profitability ratio evaluation.",
                    ),
                    (
                        "CASE_04_DEBT_LEVERAGE_RISK",
                        "Risk Analysis",
                        "Are there any liquidity or debt leverage risks identified in the balance sheet?",
                        "intent_router->research->analysis->risk->validation->report",
                        json.dumps(["total_debt", "total_equity", "current_assets", "current_liabilities"]),
                        "Total Debt / Total Equity",
                        1,
                        "Checks risk agent threshold evaluation against audited numbers.",
                    ),
                    (
                        "CASE_05_EXECUTIVE_SUMMARY",
                        "Summary",
                        "Provide a comprehensive financial summary of the company.",
                        "intent_router->research->analysis->validation->report",
                        json.dumps(["revenue", "net_profit"]),
                        "Multi-statement compilation",
                        1,
                        "Verifies end-to-end report generation with cited provenance.",
                    ),
                ]
                cursor.executemany(
                    """
                    INSERT INTO evaluation_benchmark_cases
                    (case_id, category, query, expected_agent_path, expected_metric_keys, ground_truth_formula, requires_citation, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    benchmarks,
                )
                conn.commit()

    def record_agent_execution(self, record: AgentExecutionRecord) -> None:
        """Insert a single agent execution record into the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO agent_executions (
                    run_id, agent_name, start_time, end_time, duration_seconds, status,
                    query, intent, input_summary, output_summary, validation_passed,
                    claims_count, supported_claims_count, evidence_coverage_pct,
                    error_message, company_name, reporting_period, document_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.agent_name,
                    record.start_time,
                    record.end_time,
                    record.duration_seconds,
                    record.status,
                    record.query,
                    record.intent,
                    record.input_summary,
                    record.output_summary,
                    1 if record.validation_passed else 0,
                    record.claims_count,
                    record.supported_claims_count,
                    record.evidence_coverage_pct,
                    record.error_message,
                    record.company_name,
                    record.reporting_period,
                    record.document_id,
                ),
            )
            conn.commit()

    def get_agent_metrics(self, agent_name: Optional[str] = None, hours: Optional[int] = None) -> List[AgentAggregateMetrics]:
        """
        Calculate actual measured aggregate performance metrics for all agents or a specific agent,
        with optional time range filtering.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM agent_executions WHERE 1=1"
            params: List[Any] = []
            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)
            if hours is not None and hours > 0:
                query += " AND created_at >= datetime('now', ?)"
                params.append(f"-{hours} hours")

            query += " ORDER BY id DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

        if not rows:
            return []

        df = pd.DataFrame([dict(r) for r in rows])

        metrics_list: List[AgentAggregateMetrics] = []
        grouped = df.groupby("agent_name")

        for name, group in grouped:
            total = len(group)
            successes = int((group["status"] == "completed").sum())
            failures = int((group["status"] == "failed").sum())
            skipped = int((group["status"] == "skipped").sum())
            succ_rate = (successes / total * 100.0) if total > 0 else 0.0

            durations = group["duration_seconds"].values
            avg_dur = float(np.mean(durations)) if len(durations) > 0 else 0.0
            med_dur = float(np.median(durations)) if len(durations) > 0 else 0.0
            p95_dur = float(np.percentile(durations, 95)) if len(durations) >= 5 else avg_dur

            val_passed = int((group["validation_passed"] == 1).sum())
            val_rate = (val_passed / total * 100.0) if total > 0 else 0.0

            cov_rate = float(group["evidence_coverage_pct"].mean()) if "evidence_coverage_pct" in group else 100.0
            last_record = group.iloc[0]

            metrics_list.append(
                AgentAggregateMetrics(
                    agent_name=str(name),
                    total_executions=total,
                    successful_executions=successes,
                    failed_executions=failures,
                    skipped_executions=skipped,
                    success_rate_pct=succ_rate,
                    avg_duration_seconds=avg_dur,
                    median_duration_seconds=med_dur,
                    p95_duration_seconds=p95_dur,
                    validation_pass_rate_pct=val_rate,
                    evidence_coverage_pct=cov_rate,
                    last_status=str(last_record["status"]),
                    last_run_timestamp=str(last_record["end_time"]),
                )
            )

        return sorted(metrics_list, key=lambda x: x.agent_name)

    def get_bottleneck_agent(self, hours: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Identify which agent is taking the most cumulative execution time.
        Returns the bottleneck agent, duration, and share percentage of overall multi-agent runtime.
        """
        metrics = self.get_agent_metrics(hours=hours)
        if not metrics:
            return None

        # Filter to completed/active executions with non-zero duration
        active_metrics = [m for m in metrics if m.avg_duration_seconds > 0 and m.total_executions > 0]
        if not active_metrics:
            return None

        total_pipeline_time = sum(m.avg_duration_seconds * m.successful_executions for m in active_metrics)
        if total_pipeline_time <= 0:
            return None

        # Find slowest by total cumulative time
        slowest = max(active_metrics, key=lambda m: m.avg_duration_seconds * m.successful_executions)
        agent_total = slowest.avg_duration_seconds * slowest.successful_executions
        share_pct = round((agent_total / total_pipeline_time * 100.0), 1)

        return {
            "bottleneck_agent": slowest.agent_name,
            "avg_duration_seconds": round(slowest.avg_duration_seconds, 3),
            "p95_duration_seconds": round(slowest.p95_duration_seconds, 3),
            "share_pct": share_pct,
            "total_executions": slowest.total_executions,
            "successful_executions": slowest.successful_executions,
            "failed_executions": slowest.failed_executions,
        }

    def record_skipped_agent(
        self,
        run_id: str,
        agent_name: str,
        reason: str,
        query: str = "",
        document_id: str = "",
    ) -> None:
        """Record an explicit skipped agent execution in telemetry."""
        now_iso = datetime.now().isoformat()
        record = AgentExecutionRecord(
            run_id=run_id,
            agent_name=agent_name.replace("_agent", ""),
            start_time=now_iso,
            end_time=now_iso,
            duration_seconds=0.0,
            status="skipped",
            query=query,
            input_summary=reason[:250],
            output_summary="Agent bypassed by workflow routing logic",
            validation_passed=True,
            claims_count=0,
            supported_claims_count=0,
            evidence_coverage_pct=100.0,
            error_message="",
            document_id=document_id,
        )
        self.record_agent_execution(record)

    def get_recent_executions(
        self,
        limit: int = 50,
        agent_name: Optional[str] = None,
        company_name: Optional[str] = None,
        hours: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch recent execution logs with optional filtering by agent, company, or time window."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM agent_executions WHERE 1=1"
            params: List[Any] = []

            if agent_name and agent_name != "All Agents":
                query += " AND agent_name = ?"
                params.append(agent_name)
            if company_name and company_name != "All Companies":
                query += " AND company_name = ?"
                params.append(company_name)
            if hours is not None and hours > 0:
                query += " AND created_at >= datetime('now', ?)"
                params.append(f"-{hours} hours")

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [dict(r) for r in rows]

    def record_evaluation_result(
        self,
        case_id: str,
        passed: bool,
        numerical_accuracy: float,
        formula_correct: bool,
        evidence_attributed: bool,
        unsupported_claims_found: int,
        latency_seconds: float,
        notes: str = "",
    ) -> None:
        """Record the outcome of an automated benchmark case."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evaluation_results (
                    eval_timestamp, case_id, passed, numerical_accuracy,
                    formula_correct, evidence_attributed, unsupported_claims_found,
                    latency_seconds, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    case_id,
                    1 if passed else 0,
                    numerical_accuracy,
                    1 if formula_correct else 0,
                    1 if evidence_attributed else 0,
                    unsupported_claims_found,
                    latency_seconds,
                    notes,
                ),
            )
            conn.commit()

    def get_evaluation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch past evaluation runs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.*, c.category, c.query, c.expected_agent_path
                FROM evaluation_results r
                LEFT JOIN evaluation_benchmark_cases c ON r.case_id = c.case_id
                ORDER BY r.id DESC LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def clear_telemetry(self) -> None:
        """Clear execution history (for test isolation)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_executions")
            cursor.execute("DELETE FROM evaluation_results")
            conn.commit()


# Global singleton instance
agent_telemetry_store = AgentTelemetryStore()
