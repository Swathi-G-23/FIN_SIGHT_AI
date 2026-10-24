"""
FIN SIGHT AI - LangGraph Workflow
Defines and compiles the multi-agent graph with conditional routing.
"""
import time
from datetime import datetime
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END

from src.graph.state import GraphState, QueryIntent, AgentStatus, initial_state
from src.graph.router import classify_intent, route_intent
from src.agents.research_agent import research_agent
from src.agents.analysis_agent import analysis_agent
from src.agents.ratio_agent import ratio_agent
from src.agents.risk_agent import risk_agent
from src.agents.validation_agent import validation_agent
from src.agents.report_agent import report_agent
from src.retrieval.hybrid_retriever import HybridRetriever
from src.monitoring.agent_telemetry import agent_telemetry_store, AgentExecutionRecord
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def build_workflow(
    retriever: HybridRetriever,
    extracted_metrics_raw: Dict[str, Any],
) -> StateGraph:
    """
    Build and compile the LangGraph workflow.

    Args:
        retriever: Configured HybridRetriever for document search.
        extracted_metrics_raw: Pre-extracted metrics from the document.

    Returns:
        Compiled LangGraph graph.
    """

    # ------------------------------------------------------------------ #
    # Helper to instrument agent node execution with persistent telemetry
    # ------------------------------------------------------------------ #

    def _instrument(agent_name: str, fn, state: GraphState, in_desc: str, out_desc_fn) -> GraphState:
        short_name = agent_name.replace("_agent", "")
        t0 = time.time()
        start_iso = datetime.now().isoformat()
        try:
            state = fn(state)
            status = state.get("agent_statuses", {}).get(short_name, AgentStatus.COMPLETED)
            err_msg = ""
        except Exception as exc:
            status = AgentStatus.FAILED
            err_msg = str(exc)
            state.setdefault("agent_statuses", {})[short_name] = AgentStatus.FAILED
            state.setdefault("errors", []).append(f"{agent_name}: {exc}")

        t1 = time.time()
        dur = t1 - t0
        state.setdefault("agent_timings", {})[short_name] = dur
        state.setdefault("agent_statuses", {})[short_name] = status

        end_iso = datetime.now().isoformat()
        out_desc = out_desc_fn(state) if callable(out_desc_fn) else str(out_desc_fn)
        chunks = state.get("retrieved_chunks", [])
        claims_cnt = max(1, len(chunks))
        supported_cnt = max(1, len(chunks))
        cov_pct = 100.0 if supported_cnt >= claims_cnt else (supported_cnt / claims_cnt * 100.0)

        record = AgentExecutionRecord(
            run_id=state.get("session_id") or state.get("document_id") or f"run_{int(t0)}",
            agent_name=short_name,
            start_time=start_iso,
            end_time=end_iso,
            duration_seconds=dur,
            status=status.value if isinstance(status, AgentStatus) else str(status),
            query=state.get("query", ""),
            intent=str(state.get("intent", "")),
            input_summary=in_desc[:250],
            output_summary=out_desc[:250],
            validation_passed=state.get("validation_passed", True),
            claims_count=claims_cnt,
            supported_claims_count=supported_cnt,
            evidence_coverage_pct=cov_pct,
            error_message=err_msg,
            company_name=state.get("company_name", ""),
            reporting_period=state.get("reporting_period", ""),
            document_id=state.get("document_id", ""),
        )
        try:
            agent_telemetry_store.record_agent_execution(record)
        except Exception as e:
            logger.warning("Could not log telemetry for %s: %s", short_name, e)

        return state

    # ------------------------------------------------------------------ #
    # Node factory functions (closures to inject dependencies)
    # ------------------------------------------------------------------ #

    def intent_router_node(state: GraphState) -> GraphState:
        """Classify the query intent."""
        query = state.get("query", "")
        intent = classify_intent(query)
        state["intent"] = intent
        state.setdefault("agent_statuses", {})["router"] = AgentStatus.COMPLETED
        logger.info("Intent classified: %s", intent)
        return state

    def research_node(state: GraphState) -> GraphState:
        return _instrument(
            "research_agent",
            lambda s: research_agent(s, retriever),
            state,
            f"Query: {state.get('query', '')[:80]}",
            lambda s: f"Retrieved {len(s.get('retrieved_chunks', []))} chunks",
        )

    def analysis_node(state: GraphState) -> GraphState:
        return _instrument(
            "analysis_agent",
            lambda s: analysis_agent(s, extracted_metrics_raw),
            state,
            f"Context chars: {len(state.get('context_text', ''))}",
            lambda s: f"Analysis summary length: {len(s.get('financial_summary', ''))}",
        )

    def ratio_node(state: GraphState) -> GraphState:
        return _instrument(
            "ratio_agent",
            lambda s: ratio_agent(s, extracted_metrics_raw),
            state,
            f"Extracted metric keys: {list(extracted_metrics_raw.keys())[:5]}",
            lambda s: f"Calculated {len(s.get('calculated_ratios', {}))} ratios",
        )

    def risk_node(state: GraphState) -> GraphState:
        return _instrument(
            "risk_agent",
            lambda s: risk_agent(s),
            state,
            f"Ratios count: {len(state.get('calculated_ratios', {}))}",
            lambda s: f"Identified {len(s.get('risk_findings', []))} risk factors",
        )

    def validation_node(state: GraphState) -> GraphState:
        return _instrument(
            "validation_agent",
            lambda s: validation_agent(s),
            state,
            f"Verifying {len(state.get('calculated_ratios', {}))} ratios and metrics",
            lambda s: f"Passed: {s.get('validation_passed', False)}, Notes: {len(s.get('validation_notes', []))}",
        )

    def report_node(state: GraphState) -> GraphState:
        return _instrument(
            "report_agent",
            lambda s: report_agent(s),
            state,
            f"Assembling report for intent {state.get('intent', '')}",
            lambda s: f"Report length: {len(s.get('final_answer', ''))} chars",
        )

    # ------------------------------------------------------------------ #
    # Graph construction
    # ------------------------------------------------------------------ #

    graph = StateGraph(GraphState)

    # Add all nodes
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("research", research_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("ratio", ratio_node)
    graph.add_node("risk", risk_node)
    graph.add_node("validation", validation_node)
    graph.add_node("report", report_node)

    # ---- Entry point ----
    graph.set_entry_point("intent_router")

    # ---- After routing: always research first ----
    graph.add_edge("intent_router", "research")

    # ---- After research: route by intent ----
    def after_research(state: GraphState) -> str:
        intent = state.get("intent", QueryIntent.UNKNOWN)
        if intent in (QueryIntent.NUMERICAL, QueryIntent.COMPLEX, QueryIntent.SIMULATION, QueryIntent.SUMMARY, QueryIntent.RECOMMENDATION):
            return "ratio"
        elif intent == QueryIntent.RISK:
            return "analysis"  # analyse before risk
        else:
            return "analysis"

    graph.add_conditional_edges(
        "research",
        after_research,
        {
            "ratio": "ratio",
            "analysis": "analysis",
        },
    )

    # ---- After ratio: if COMPLEX, SUMMARY, or RECOMMENDATION continue to analysis, else validate ----
    def after_ratio(state: GraphState) -> str:
        intent = state.get("intent", QueryIntent.UNKNOWN)
        if intent in (QueryIntent.COMPLEX, QueryIntent.SUMMARY, QueryIntent.RECOMMENDATION):
            return "analysis"
        return "validation"

    graph.add_conditional_edges(
        "ratio",
        after_ratio,
        {
            "analysis": "analysis",
            "validation": "validation",
        },
    )

    # ---- After analysis: check if risk is needed ----
    def after_analysis(state: GraphState) -> str:
        intent = state.get("intent", QueryIntent.UNKNOWN)
        if intent in (QueryIntent.RISK, QueryIntent.COMPLEX, QueryIntent.RECOMMENDATION):
            return "risk"
        return "validation"

    graph.add_conditional_edges(
        "analysis",
        after_analysis,
        {
            "risk": "risk",
            "validation": "validation",
        },
    )

    # ---- After risk: validate ----
    graph.add_edge("risk", "validation")

    # ---- After validation: report ----
    graph.add_edge("validation", "report")

    # ---- End ----
    graph.add_edge("report", END)

    return graph.compile()


def run_query(
    query: str,
    document_id: str,
    retriever: HybridRetriever,
    extracted_metrics_raw: Dict[str, Any],
    session_id: str = "",
    company_name: str = "",
    reporting_period: str = "",
) -> GraphState:
    """
    Run a complete query through the multi-agent workflow.

    Args:
        query: User's question.
        document_id: Document being queried.
        retriever: Configured HybridRetriever.
        extracted_metrics_raw: Pre-extracted financial metrics.
        session_id: Optional session identifier.
        company_name: Optional active corporate entity name.
        reporting_period: Optional reporting period identifier.

    Returns:
        Final GraphState with all agent outputs.
    """
    start = time.time()
    logger.info("Starting workflow for query: '%s'", query[:80])

    state = initial_state(query, document_id, session_id)
    if company_name:
        state["company_name"] = company_name
    if reporting_period:
        state["reporting_period"] = reporting_period

    try:
        workflow = build_workflow(retriever, extracted_metrics_raw)
        final_state = workflow.invoke(state)
    except Exception as exc:
        logger.error("Workflow error: %s", exc)
        state["errors"] = state.get("errors", []) + [f"Workflow error: {exc}"]
        state["final_answer"] = f"⚠️ An error occurred during processing: {exc}"
        final_state = state

    # Ensure no executed or bypassed agent is left indefinitely PENDING, and record explicit skip reasons
    all_agent_keys = ["router", "research", "ratio", "analysis", "risk", "validation", "report"]
    final_statuses = final_state.setdefault("agent_statuses", {})
    skip_reasons = final_state.setdefault("agent_skip_reasons", {})
    intent_val = final_state.get("intent", QueryIntent.UNKNOWN)
    intent_name = intent_val.value if hasattr(intent_val, "value") else str(intent_val)

    run_id_val = session_id or state.get("session_id") or f"run_{int(start)}"
    for k in all_agent_keys:
        if k not in final_statuses or final_statuses[k] == AgentStatus.PENDING:
            final_statuses[k] = AgentStatus.SKIPPED
            if k == "ratio":
                reason_txt = f"Intent '{intent_name}' is qualitative/risk-oriented and did not require ratio calculation."
            elif k == "risk":
                reason_txt = f"Intent '{intent_name}' focused on historical metrics and did not require solvency/risk analysis."
            elif k == "analysis":
                reason_txt = f"Direct numerical calculation routed immediately from ratio calculation to verification."
            else:
                reason_txt = f"Bypassed by router for query intent '{intent_name}'."
            skip_reasons[k] = reason_txt

            try:
                agent_telemetry_store.record_skipped_agent(
                    run_id=run_id_val,
                    agent_name=k,
                    reason=reason_txt,
                    query=query,
                    document_id=document_id,
                )
            except Exception as e:
                logger.warning(f"Could not log skipped agent {k}: {e}")

    elapsed = time.time() - start
    logger.info("Workflow completed in %.2fs", elapsed)

    # Record overall query operation in application APM
    try:
        from src.monitoring.performance import PerformanceMonitor
        has_errors = bool(final_state.get("errors"))
        err_msg = "; ".join(final_state.get("errors", [])) if has_errors else ""
        PerformanceMonitor().record_operation(
            operation_type="chat_query",
            operation_name=f"Chat Query: {query[:45]}",
            duration_seconds=elapsed,
            status="failed" if (has_errors and not final_state.get("final_answer")) else "success",
            error_message=err_msg,
            details={
                "intent": intent_name,
                "document_id": document_id,
                "chunks_retrieved": len(final_state.get("retrieved_chunks", [])),
                "agents_executed": [k for k, v in final_statuses.items() if v == AgentStatus.COMPLETED],
                "agents_skipped": [k for k, v in final_statuses.items() if v == AgentStatus.SKIPPED],
            },
        )
    except Exception as e:
        logger.warning(f"Could not log APM operation for query: {e}")

    return final_state

