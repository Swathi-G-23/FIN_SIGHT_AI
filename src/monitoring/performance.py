"""
FIN SIGHT AI - Performance & Scalability Monitoring
Provides live system metrics (CPU, RAM via psutil), ingestion/retrieval latency tracking,
persistent application operation profiling via SQLite, and automated benchmark runners.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import psutil

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = Path("data/agent_telemetry.db")


@dataclass
class OperationMetric:
    operation_name: str
    duration_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)
    operation_type: str = "general"
    status: str = "success"
    error_message: str = ""


@dataclass
class DocumentBenchmarkResult:
    benchmark_size: str              # Small (~5 pages), Medium (~25 pages), Large (~100 pages)
    page_count: int
    char_count: int
    chunk_count: int
    ingestion_time_sec: float
    retrieval_latency_ms: float
    memory_used_mb: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PerformanceMonitor:
    """
    Singleton monitor for hardware resources, application latencies,
    and persistent operation telemetry.
    """

    _instance = None

    def __new__(cls, db_path: Optional[Path] = None):
        if cls._instance is None or not hasattr(cls._instance, "get_application_health"):
            cls._instance = super(PerformanceMonitor, cls).__new__(cls)
            cls._instance._history = []
            cls._instance._benchmarks = []
            cls._instance.db_path = db_path or DB_PATH
            cls._instance.db_path.parent.mkdir(parents=True, exist_ok=True)
            cls._instance._start_time = time.time()
            cls._instance._init_db()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize application operations database table."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS application_operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation_type TEXT NOT NULL,
                        operation_name TEXT NOT NULL,
                        duration_seconds REAL NOT NULL,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        cpu_percent REAL,
                        memory_mb REAL,
                        details_json TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_app_ops_timestamp ON application_operations(timestamp)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_app_ops_type ON application_operations(operation_type)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_app_ops_status ON application_operations(status)"
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not initialize application_operations table: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # Recording Operations & Latencies
    # ─────────────────────────────────────────────────────────────────────────────

    def record_operation(
        self,
        operation_type: str,
        operation_name: str,
        duration_seconds: float,
        status: str = "success",
        error_message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> OperationMetric:
        """
        Record an application operation to both memory and persistent SQLite database.
        Includes non-blocking CPU and RSS memory telemetry.
        """
        duration = max(0.0001, round(float(duration_seconds), 4))
        status_clean = "failed" if status in ("failed", "error", False) else "success"

        # Sanitize details (strip API keys, passwords, tokens)
        clean_details = self._sanitize_dict(details or {})
        details_json = json.dumps(clean_details)

        # Get lightweight non-blocking process telemetry
        sys_res = self.get_system_resources()
        cpu_val = sys_res.get("process_cpu_percent", 0.0)
        mem_val = sys_res.get("process_memory_mb", 0.0)

        metric = OperationMetric(
            operation_name=operation_name,
            duration_seconds=duration,
            timestamp=datetime.now().isoformat(),
            details=clean_details,
            operation_type=operation_type,
            status=status_clean,
            error_message=str(error_message or ""),
        )
        self._history.append(metric)

        # Persist to SQLite
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO application_operations (
                        operation_type, operation_name, duration_seconds,
                        status, error_message, cpu_percent, memory_mb, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        operation_type,
                        operation_name,
                        duration,
                        status_clean,
                        error_message,
                        cpu_val,
                        mem_val,
                        details_json,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not persist application operation telemetry: {e}")

        logger.info(
            f"APM: [{operation_type}] {operation_name} took {duration:.3f}s | status={status_clean}"
        )
        return metric

    def record_metric(
        self,
        operation: str,
        duration: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Backward-compatible metric recorder that maps to record_operation."""
        op_lower = operation.lower()
        if "pdf" in op_lower or "extract" in op_lower:
            op_type = "pdf_extraction"
        elif "chunk" in op_lower:
            op_type = "chunking"
        elif "faiss" in op_lower or "vector" in op_lower:
            op_type = "faiss_indexing"
        elif "bm25" in op_lower:
            op_type = "bm25_indexing"
        elif "embed" in op_lower:
            op_type = "embedding_generation"
        elif "report" in op_lower:
            op_type = "report_generation"
        elif "chat" in op_lower or "query" in op_lower:
            op_type = "chat_query"
        else:
            op_type = "general"

        return self.record_operation(
            operation_type=op_type,
            operation_name=operation,
            duration_seconds=duration,
            status="success",
            details=details,
        )

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive keys like API keys, tokens, or passwords."""
        sensitive_keys = {"api_key", "token", "password", "secret", "google_api_key", "openai_api_key"}
        sanitized = {}
        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = self._sanitize_dict(v)
            elif isinstance(v, str) and len(v) > 300:
                sanitized[k] = v[:300] + "…"
            else:
                sanitized[k] = v
        return sanitized

    # ─────────────────────────────────────────────────────────────────────────────
    # System Hardware & Health Profiling
    # ─────────────────────────────────────────────────────────────────────────────

    def get_system_resources(self) -> Dict[str, Any]:
        """Returns live process and host memory and CPU utilization."""
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)
            cpu_pct = process.cpu_percent(interval=0.0)  # non-blocking
            sys_mem = psutil.virtual_memory()

            return {
                "process_memory_mb": round(mem_mb, 1),
                "process_cpu_percent": round(cpu_pct, 1),
                "system_total_memory_gb": round(sys_mem.total / (1024**3), 1),
                "system_memory_used_gb": round(sys_mem.used / (1024**3), 1),
                "system_memory_used_percent": sys_mem.percent,
                "cpu_count_logical": psutil.cpu_count(logical=True) or 1,
                "cpu_count_physical": psutil.cpu_count(logical=False) or 1,
            }
        except Exception as e:
            logger.warning(f"Could not read process resources: {e}")
            return {
                "process_memory_mb": 0.0,
                "process_cpu_percent": 0.0,
                "system_total_memory_gb": 16.0,
                "system_memory_used_gb": 8.0,
                "system_memory_used_percent": 50.0,
                "cpu_count_logical": 4,
                "cpu_count_physical": 2,
            }

    def get_application_health(self) -> Dict[str, Any]:
        """
        Evaluate overall system health: OPERATIONAL, DEGRADED, or UNHEALTHY.
        Evaluates recent error rates and CPU/RAM thresholds.
        """
        res = self.get_system_resources()
        uptime = round(time.time() - self._start_time, 1)

        # Check recent 1-hour error rate
        summary_1h = self.get_performance_summary(hours=1)
        tot_1h = summary_1h.get("total_requests", 0)
        fail_1h = summary_1h.get("failed_requests", 0)
        fail_rate = (fail_1h / tot_1h * 100.0) if tot_1h > 0 else 0.0

        db_ok = self.db_path.exists()
        langsmith = self.get_langsmith_status()

        # Health determination
        if not db_ok or fail_rate > 35.0 or res["system_memory_used_percent"] > 95.0:
            status = "CRITICAL"
            badge = "🔴 Unhealthy"
            description = "High failure rate or resource exhaustion detected."
        elif fail_rate > 10.0 or res["process_memory_mb"] > 2048.0 or res["system_memory_used_percent"] > 85.0:
            status = "DEGRADED"
            badge = "🟡 Degraded"
            description = "Elevated failure rate or high resource consumption."
        else:
            status = "HEALTHY"
            badge = "🟢 Operational"
            description = "All application pipelines and multi-agent systems performing nominally."

        return {
            "status": status,
            "badge": badge,
            "description": description,
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_uptime(uptime),
            "cpu_percent": res["process_cpu_percent"],
            "memory_mb": res["process_memory_mb"],
            "system_ram_pct": res["system_memory_used_percent"],
            "error_rate_1h_pct": round(fail_rate, 1),
            "db_connected": db_ok,
            "langsmith_mode": langsmith["mode"],
        }

    def _format_uptime(self, seconds: float) -> str:
        mins, secs = divmod(int(seconds), 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs}h {mins}m {secs}s"
        return f"{mins}m {secs}s"

    # ─────────────────────────────────────────────────────────────────────────────
    # APM Metrics Aggregations & History
    # ─────────────────────────────────────────────────────────────────────────────

    def get_performance_summary(self, hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Aggregate response times, success/failure counts, and percentiles.
        Filter by hours if specified (e.g. 1, 24, 168).
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT duration_seconds, status FROM application_operations WHERE 1=1"
                params: List[Any] = []
                if hours is not None and hours > 0:
                    query += " AND timestamp >= datetime('now', ?)"
                    params.append(f"-{hours} hours")

                cursor.execute(query, params)
                rows = cursor.fetchall()

            if not rows:
                return {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "success_rate_pct": 100.0,
                    "avg_response_time": 0.0,
                    "max_response_time": 0.0,
                    "min_response_time": 0.0,
                    "p95_response_time": 0.0,
                }

            durations = [float(r["duration_seconds"]) for r in rows]
            total = len(rows)
            successes = sum(1 for r in rows if r["status"] == "success")
            failures = total - successes

            durations.sort()
            avg_lat = sum(durations) / total
            max_lat = max(durations)
            min_lat = min(durations)
            p95_idx = int(0.95 * total)
            p95_lat = durations[min(p95_idx, total - 1)]

            return {
                "total_requests": total,
                "successful_requests": successes,
                "failed_requests": failures,
                "success_rate_pct": round((successes / total * 100.0), 1),
                "avg_response_time": round(avg_lat, 3),
                "max_response_time": round(max_lat, 3),
                "min_response_time": round(min_lat, 3),
                "p95_response_time": round(p95_lat, 3),
            }
        except Exception as e:
            logger.warning(f"Could not calculate performance summary: {e}")
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate_pct": 100.0,
                "avg_response_time": 0.0,
                "max_response_time": 0.0,
                "min_response_time": 0.0,
                "p95_response_time": 0.0,
            }

    def get_operation_breakdown(self, hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """Group operations by type with volume, latency, and success rates."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                SELECT 
                    operation_type,
                    COUNT(*) as count,
                    AVG(duration_seconds) as avg_duration,
                    MAX(duration_seconds) as max_duration,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failure_count
                FROM application_operations
                WHERE 1=1
                """
                params: List[Any] = []
                if hours is not None and hours > 0:
                    query += " AND timestamp >= datetime('now', ?)"
                    params.append(f"-{hours} hours")

                query += " GROUP BY operation_type ORDER BY count DESC"
                cursor.execute(query, params)
                rows = cursor.fetchall()

            breakdown = []
            for r in rows:
                cnt = r["count"]
                fails = r["failure_count"] or 0
                succ_rate = round(((cnt - fails) / cnt * 100.0), 1) if cnt > 0 else 100.0
                breakdown.append({
                    "operation_type": r["operation_type"],
                    "count": cnt,
                    "avg_duration": round(float(r["avg_duration"] or 0.0), 3),
                    "max_duration": round(float(r["max_duration"] or 0.0), 3),
                    "failures": fails,
                    "success_rate_pct": succ_rate,
                })
            return breakdown
        except Exception as e:
            logger.warning(f"Could not get operation breakdown: {e}")
            return []

    def get_latency_history(self, hours: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch chronological operations for plotting latency trends."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT id, operation_type, operation_name, duration_seconds, status, timestamp FROM application_operations WHERE 1=1"
                params: List[Any] = []
                if hours is not None and hours > 0:
                    query += " AND timestamp >= datetime('now', ?)"
                    params.append(f"-{hours} hours")

                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)
                cursor.execute(query, params)
                rows = cursor.fetchall()

            return [dict(r) for r in reversed(rows)]
        except Exception as e:
            logger.warning(f"Could not get latency history: {e}")
            return []

    def get_error_logs(self, hours: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent failed operations and error messages."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                SELECT id, operation_type, operation_name, duration_seconds, error_message, timestamp
                FROM application_operations
                WHERE status = 'failed' OR (error_message IS NOT NULL AND error_message != '')
                """
                params: List[Any] = []
                if hours is not None and hours > 0:
                    query += " AND timestamp >= datetime('now', ?)"
                    params.append(f"-{hours} hours")

                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)
                cursor.execute(query, params)
                rows = cursor.fetchall()

            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Could not get error logs: {e}")
            return []

    def get_langsmith_status(self) -> Dict[str, Any]:
        """
        Check whether LangSmith cloud tracing is actively enabled in the environment.
        """
        tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() in ("true", "1", "yes")
        api_key = os.getenv("LANGCHAIN_API_KEY", "")
        project = os.getenv("LANGCHAIN_PROJECT", "fin-sight-ai")
        endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

        has_key = bool(api_key and len(api_key.strip()) > 5)
        active = tracing_v2 and has_key

        return {
            "enabled": active,
            "tracing_v2_set": tracing_v2,
            "api_key_configured": has_key,
            "project": project,
            "endpoint": endpoint,
            "mode": "LangSmith Cloud Active" if active else "Embedded Local APM (Active)",
        }

    def clear_metrics(self) -> None:
        """Clear memory and database metrics for testing or cleanup."""
        self._history.clear()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM application_operations")
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not clear operations table: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # Document Scaling Benchmark Runner
    # ─────────────────────────────────────────────────────────────────────────────

    def run_document_scaling_benchmark(self, page_counts: Optional[List[int]] = None, size_category: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs document scaling benchmark for specified page counts and returns timing details.
        """
        from src.ingestion.pdf_extractor import PageContent
        from src.ingestion.chunker import TextChunker
        from src.retrieval.keyword_search import KeywordSearcher

        pages = (page_counts[0] if page_counts else 25)
        size_label = size_category or ("Small" if pages <= 5 else "Medium" if pages <= 25 else "Large")

        synthetic_pages = []
        for p in range(1, pages + 1):
            page_text = (
                f"=== CORPORATE FINANCIAL REPORT | FISCAL YEAR ANALYSIS | PAGE {p} ===\n"
                f"Operating revenue for segment {p} totaled ${120 + p * 4}.5 million with operational cost of ${70 + p * 2}.0 million.\n"
                f"Gross margin achieved {(40 + (p % 10)):.1f}% with research development expenditures of ${18.5} million.\n"
                f"Balance sheet cash assets recorded at ${95 + p * 2}.0 million against debt covenants of ${45.0} million.\n"
                f"Corporate risk disclosures: Liquidity buffers, capital expenditure pipeline, and interest rate sensitivity.\n\n"
            ) * 4
            synthetic_pages.append((p, page_text))

        page_objects = [PageContent(page_number=p_num, text=p_txt) for p_num, p_txt in synthetic_pages]

        t0 = time.perf_counter()
        chunker = TextChunker(chunk_size=600, chunk_overlap=80)
        chunks = chunker.chunk_document("scaling_doc", page_objects)
        t_chunk = time.perf_counter() - t0

        t1 = time.perf_counter()
        chunk_dicts = [{"text": c.text, "chunk_id": c.chunk_id, "page_numbers": c.page_numbers} for c in chunks]
        keyword_searcher = KeywordSearcher()
        keyword_searcher.build(chunk_dicts)
        t_index = time.perf_counter() - t1

        t2 = time.perf_counter()
        _ = keyword_searcher.search("operating revenue gross margin cash assets debt", top_k=5)
        t_query_ms = (time.perf_counter() - t2) * 1000.0

        total_duration = t_chunk + t_index + (t_query_ms / 1000.0)
        res_info = self.get_system_resources()

        benchmark = DocumentBenchmarkResult(
            benchmark_size=size_label,
            page_count=pages,
            char_count=sum(len(t) for _, t in synthetic_pages),
            chunk_count=len(chunks),
            ingestion_time_sec=round(t_chunk + t_index, 4),
            retrieval_latency_ms=round(t_query_ms, 2),
            memory_used_mb=res_info.get("process_memory_mb", 0.0),
        )
        self._benchmarks.append(benchmark)

        # Record benchmark operation
        self.record_operation(
            operation_type="scaling_benchmark",
            operation_name=f"Document Scaling Benchmark ({size_label}: {pages} Pages)",
            duration_seconds=total_duration,
            status="success",
            details={"pages": pages, "chunks": len(chunks), "retrieval_ms": round(t_query_ms, 2), "size": size_label},
        )

        return {
            "total_duration": total_duration,
            "chunk_count": len(chunks),
            "ingestion_time": t_chunk + t_index,
            "retrieval_latency_ms": t_query_ms,
            "page_count": pages,
            "benchmark_size": size_label,
            "memory_mb": res_info.get("process_memory_mb", 0.0),
        }

    def run_benchmark(self, size_category: str = "Small") -> DocumentBenchmarkResult:
        """
        Runs synthetic scaling benchmark by size category.
        """
        page_counts = {"Small": 5, "Medium": 25, "Large": 100}
        target_pages = page_counts.get(size_category, 25)
        self.run_document_scaling_benchmark(page_counts=[target_pages], size_category=size_category)
        return self._benchmarks[-1]

    def get_benchmarks(self) -> List[DocumentBenchmarkResult]:
        return self._benchmarks
