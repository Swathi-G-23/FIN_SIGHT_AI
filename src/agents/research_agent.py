"""
FIN SIGHT AI - Research Agent
Retrieves relevant document evidence for the user's query.
"""
import time
from typing import Any, Dict

from src.graph.state import GraphState, AgentStatus
from src.retrieval.hybrid_retriever import HybridRetriever
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def research_agent(state: GraphState, retriever: HybridRetriever) -> GraphState:
    """
    Agent 1: Research Agent
    Retrieves the most relevant document chunks for the query.

    Updates state with:
        - retrieved_chunks
        - context_text
        - agent_statuses["research"]
        - agent_timings["research"]
    """
    start = time.time()
    state.setdefault("agent_statuses", {})["research"] = AgentStatus.RUNNING
    state.setdefault("agent_timings", {})

    query = state.get("query", "")
    if not query:
        state["agent_statuses"]["research"] = AgentStatus.FAILED
        state.setdefault("errors", []).append("Research agent: empty query.")
        return state

    try:
        chunks = retriever.retrieve(query)
        context = HybridRetriever.format_context(chunks)

        state["retrieved_chunks"] = chunks
        state["context_text"] = context
        state["agent_statuses"]["research"] = AgentStatus.COMPLETED
        logger.info("Research agent: retrieved %d chunks", len(chunks))

    except Exception as exc:
        logger.error("Research agent error: %s", exc)
        state["agent_statuses"]["research"] = AgentStatus.FAILED
        state.setdefault("errors", []).append(f"Research agent: {exc}")
        state["retrieved_chunks"] = []
        state["context_text"] = ""

    state["agent_timings"]["research"] = time.time() - start
    return state
