"""
FIN SIGHT AI - Intent Router
Classifies user queries to determine the optimal agent routing path.
Handles numerical questions, ratios, risks, comparisons, simulations,
and action recommendations.
"""
import re
from typing import Dict

from src.graph.state import GraphState, QueryIntent
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# ------------------------------------------------------------------ #
# Keyword sets for rule-based intent classification
# ------------------------------------------------------------------ #

_NUMERICAL_KEYWORDS = {
    "revenue", "profit", "net income", "cogs", "expenses", "ebit", "operating profit",
    "operating income", "debt", "equity", "assets", "liabilities", "cash",
    "ratio", "margin", "percentage", "%", "calculate", "computation",
    "debt to equity", "current ratio", "quick ratio", "profit margin", "gross margin",
    "return on", "roe", "roa", "eps", "pe ratio", "how much",
    "total revenue", "net profit", "earnings per share", "working capital",
}

_RISK_KEYWORDS = {
    "risk", "risks", "warning", "concern", "red flag", "problem",
    "bankruptcy", "distress", "decline", "negative", "loss", "default",
    "vulnerable", "solvency", "leverage risk", "liquidity risk", "exposure",
}

_RECOMMENDATION_KEYWORDS = {
    "recommend", "recommendation", "recommendations", "improve", "optimize", "reduce risk",
    "action", "actions", "strategy", "suggest", "how to improve", "how can", "what can",
    "deteriorated", "areas need", "investigation", "remedy", "mitigate",
}

_SIMULATION_KEYWORDS = {
    "what if", "simulate", "simulation", "scenario", "what happens if", "increases by",
    "decreases by", "grows by", "drops by", "rise by", "fall by", "assumed", "if revenue",
    "if expenses", "if debt",
}

_COMPARISON_KEYWORDS = {
    "compare", "comparison", "versus", "vs", "previous year", "prior year",
    "year over year", "yoy", "peer", "peers", "quarter over quarter", "qoq",
    "change between", "growth rate",
}

_SUMMARY_KEYWORDS = {
    "summarize", "summary", "overview", "brief", "describe",
    "overall", "general", "performance", "executive summary",
    "balance sheet", "income statement", "statement of operations",
    "cash flow statement", "financial statements",
}


def _keyword_match_score(query_lower: str, keywords: set) -> int:
    """Count how many keywords match in the query."""
    return sum(1 for kw in keywords if kw in query_lower)


def classify_intent(query: str) -> QueryIntent:
    """
    Classify a query into one of the QueryIntent categories.
    Uses contextual keyword matching and regex patterns with fallback to GENERAL.
    """
    q = query.lower().strip()

    # Direct pattern checks for distinctive high-value intents
    if any(p in q for p in ["what happens if", "what if", "simulate", "scenario"]) or re.search(r"\b(increase|decrease|grow|drop)s?\s+by\s+\d+%", q):
        return QueryIntent.SIMULATION

    if any(p in q for p in ["how can", "how to improve", "recommend", "recommendation", "what actions", "what could reduce", "which areas need"]):
        return QueryIntent.RECOMMENDATION

    if any(p in q for p in ["compare", "versus", " vs ", "prior year", "previous year", "year over year", "yoy", "growth rate"]):
        return QueryIntent.COMPARISON

    if any(p in q for p in ["summary", "summarize", "overview", "executive summary", "balance sheet", "consolidated balance sheet", "income statement", "statement of operations", "statement of earnings", "about the report", "about this report", "financial statements"]):
        return QueryIntent.SUMMARY

    scores = {
        QueryIntent.SIMULATION: _keyword_match_score(q, _SIMULATION_KEYWORDS),
        QueryIntent.RECOMMENDATION: _keyword_match_score(q, _RECOMMENDATION_KEYWORDS),
        QueryIntent.COMPARISON: _keyword_match_score(q, _COMPARISON_KEYWORDS),
        QueryIntent.NUMERICAL: _keyword_match_score(q, _NUMERICAL_KEYWORDS),
        QueryIntent.RISK: _keyword_match_score(q, _RISK_KEYWORDS),
        QueryIntent.SUMMARY: _keyword_match_score(q, _SUMMARY_KEYWORDS),
    }

    top_intent = max(scores, key=lambda x: scores[x])
    top_score = scores[top_intent]

    if any(p in q for p in ["comprehensive", "full analysis", "in-depth", "complete overview", "end to end"]):
        return QueryIntent.COMPLEX

    # If two strong distinct intents match with balanced high scores, classify as COMPLEX
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) >= 2 and sorted_scores[1] >= 2 and top_score >= 2 and abs(sorted_scores[0] - sorted_scores[1]) <= 1:
        return QueryIntent.COMPLEX

    if top_score == 0:
        return QueryIntent.GENERAL

    return top_intent


def route_intent(state: GraphState) -> str:
    """
    LangGraph routing function.
    Returns the name of the next node to execute.
    """
    intent = state.get("intent", QueryIntent.UNKNOWN)

    routing = {
        QueryIntent.NUMERICAL: "ratio_agent",
        QueryIntent.COMPARISON: "analysis_agent",
        QueryIntent.SIMULATION: "ratio_agent",
        QueryIntent.RECOMMENDATION: "analysis_agent",
        QueryIntent.RISK: "risk_agent",
        QueryIntent.SUMMARY: "analysis_agent",
        QueryIntent.GENERAL: "analysis_agent",
        QueryIntent.COMPLEX: "ratio_agent",
        QueryIntent.UNKNOWN: "analysis_agent",
    }
    next_node = routing.get(intent, "analysis_agent")
    logger.info("Routing intent '%s' -> %s", intent, next_node)
    return next_node
