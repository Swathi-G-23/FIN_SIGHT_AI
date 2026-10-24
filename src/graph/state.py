"""
FIN SIGHT AI - LangGraph Shared State
Defines the GraphState TypedDict that flows through all agents.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class QueryIntent(str, Enum):
    NUMERICAL = "numerical"            # ratio / number question
    GENERAL = "general"               # general financial analysis
    RISK = "risk"                     # risk-related question
    COMPLEX = "complex"               # needs multiple agents
    SUMMARY = "summary"               # summarisation request
    RECOMMENDATION = "recommendation" # action recommendations
    SIMULATION = "simulation"         # what-if simulation
    COMPARISON = "comparison"         # period or peer comparison
    UNKNOWN = "unknown"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class GraphState(TypedDict, total=False):
    # ---- Input ----
    query: str
    document_id: str
    session_id: str

    # ---- Intent ----
    intent: QueryIntent

    # ---- Retrieved evidence ----
    retrieved_chunks: List[Dict[str, Any]]  # from HybridRetriever
    context_text: str                       # formatted context for LLM

    # ---- Extracted financial data ----
    financial_metrics: Dict[str, Any]       # from metric_extraction
    extracted_metrics_raw: Dict[str, List[Any]]

    # ---- Calculated ratios ----
    calculated_ratios: Dict[str, Any]       # RatioResult objects

    # ---- Trend / analysis ----
    trend_analysis: Dict[str, Any]
    financial_summary: str

    # ---- Risk findings ----
    risk_findings: List[Dict[str, Any]]

    # ---- Validation ----
    validation_notes: List[str]
    validation_passed: bool

    # ---- Agent statuses ----
    agent_statuses: Dict[str, AgentStatus]
    agent_outputs: Dict[str, Any]
    agent_skip_reasons: Dict[str, str]

    # ---- Final answer ----
    final_answer: str
    supporting_evidence: List[Dict[str, Any]]

    # ---- Error handling ----
    errors: List[str]
    warnings: List[str]

    # ---- Timing ----
    start_time: float
    agent_timings: Dict[str, float]

    # ---- Multimodal & Provenance Metadata ----
    company_name: str
    reporting_period: str
    multi_period_records: List[Dict[str, Any]]
    provenance_citations: List[str]


def initial_state(
    query: str,
    document_id: str,
    session_id: str = "",
) -> GraphState:
    """Create a fresh initial graph state."""
    return GraphState(
        query=query,
        document_id=document_id,
        session_id=session_id,
        intent=QueryIntent.UNKNOWN,
        retrieved_chunks=[],
        context_text="",
        financial_metrics={},
        extracted_metrics_raw={},
        calculated_ratios={},
        trend_analysis={},
        financial_summary="",
        risk_findings=[],
        validation_notes=[],
        validation_passed=False,
        agent_statuses={},
        agent_outputs={},
        agent_skip_reasons={},
        final_answer="",
        supporting_evidence=[],
        errors=[],
        warnings=[],
        start_time=time.time(),
        agent_timings={},
        company_name="",
        reporting_period="",
        multi_period_records=[],
        provenance_citations=[],
    )
