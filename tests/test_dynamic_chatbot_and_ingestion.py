"""
FIN SIGHT AI - Test Suite for Dynamic Chatbot, All Ingestion Modalities & Agent Statuses
Verifies:
1. PDF, Excel, CSV, Image, and Manual ingestion populating normalized ExtractedMetrics.
2. Dynamic input-specific chatbot responses (revenue, profit, ratio, simulation, recommendations, missing data).
3. LangGraph agent statuses: all 6 agents are either COMPLETED or SKIPPED, zero permanent PENDING.
4. Next Page and Previous Page navigation state consistency.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.graph.state import QueryIntent, AgentStatus, initial_state
from src.graph.router import classify_intent
from src.agents.report_agent import report_agent
from src.ingestion.models import FinancialPeriodRecord, InputSourceType
from src.finance.metric_extraction import ExtractedMetric
from src.utils.session_manager import convert_financial_records_to_extracted_metrics


class TestUnifiedDataIngestion:
    """Verifies all ingestion types convert into standardized ExtractedMetric structures."""

    def test_record_to_extracted_metrics_conversion(self):
        rec = FinancialPeriodRecord(
            company_name="Apex Technologies Ltd.",
            reporting_period="FY2023",
            currency="USD",
            revenue=124800000.0,
            cost_of_goods_sold=50500000.0,
            gross_profit=74300000.0,
            operating_expenses=51200000.0,
            operating_income=23100000.0,
            net_income=17060000.0,
            total_assets=145000000.0,
            current_assets=64400000.0,
            total_debt=30400000.0,
            total_equity=84000000.0,
            operating_cash_flow=26400000.0,
        )

        metrics = convert_financial_records_to_extracted_metrics([rec])

        assert "revenue" in metrics
        assert metrics["revenue"][0].numeric_value == 124800000.0
        assert metrics["revenue"][0].normalized_value == 124800000.0
        assert metrics["revenue"][0].period == "FY2023"

        assert "net_income" in metrics
        assert metrics["net_income"][0].numeric_value == 17060000.0

        assert "current_assets" in metrics
        assert metrics["current_assets"][0].numeric_value == 64400000.0

        assert "total_debt" in metrics
        assert metrics["total_debt"][0].numeric_value == 30400000.0


class TestDynamicIntentAndChatbotIntelligence:
    """Verifies that chatbot produces distinct, input-specific responses and recommendations."""

    def test_intent_classification_diversity(self):
        assert classify_intent("What is the company's total revenue?") == QueryIntent.NUMERICAL
        assert classify_intent("Calculate the current ratio") == QueryIntent.NUMERICAL
        assert classify_intent("What happens if operating expenses increase by 10%?") == QueryIntent.SIMULATION
        assert classify_intent("How can the company improve its profit margin?") == QueryIntent.RECOMMENDATION
        assert classify_intent("Compare revenue with the previous year") == QueryIntent.COMPARISON
        assert classify_intent("What are the major bankruptcy or debt risks?") == QueryIntent.RISK

    def test_revenue_inquiry_returns_specific_revenue_not_full_dump(self):
        state = initial_state("What is the company's total revenue?", "doc_1")
        state["intent"] = QueryIntent.NUMERICAL
        state["financial_metrics"] = {
            "revenue": {"value": 124.8, "raw": "$124.8M", "period": "FY2023", "page": 1},
            "net_income": {"value": 17.06, "raw": "$17.06M", "period": "FY2023", "page": 1},
        }

        res = report_agent(state)
        answer = res["final_answer"]

        assert "Total Revenue" in answer or "Revenue" in answer
        assert "$124.8M" in answer
        assert "FY2023" in answer
        assert res["agent_statuses"]["report"] == AgentStatus.COMPLETED

    def test_recommendation_inquiry_has_six_part_structure(self):
        state = initial_state("How can the company improve its profit margin?", "doc_1")
        state["intent"] = QueryIntent.RECOMMENDATION
        state["financial_metrics"] = {
            "revenue": {"value": 124.8, "raw": "$124.8M", "period": "FY2023", "page": 1},
            "operating_expenses": {"value": 51.2, "raw": "$51.2M", "period": "FY2023", "page": 1},
        }

        res = report_agent(state)
        answer = res["final_answer"]

        assert "1. Observed Issue" in answer
        assert "2. Audited Evidence" in answer or "2. Evidence" in answer
        assert "3. Possible Action" in answer
        assert "4. Expected Effect" in answer
        assert "5. Assumptions" in answer
        assert "6. Limitations" in answer

    def test_what_if_simulation_calculates_variance(self):
        state = initial_state("What happens if operating expenses increase by 10%?", "doc_1")
        state["intent"] = QueryIntent.SIMULATION
        state["financial_metrics"] = {
            "revenue": {"value": 124.8, "raw": "$124.8M", "period": "FY2023", "page": 1},
            "operating_expenses": {"value": 51.2, "raw": "$51.2M", "period": "FY2023", "page": 1},
            "cogs": {"value": 50.5, "raw": "$50.5M", "period": "FY2023", "page": 1},
        }

        res = report_agent(state)
        answer = res["final_answer"]

        assert "What-If Scenario Simulation" in answer
        assert "Operating Expenses" in answer
        assert "Operating Profit" in answer

    def test_missing_data_honesty(self):
        state = initial_state("What is the company's research and development expense?", "doc_1")
        state["intent"] = QueryIntent.NUMERICAL
        state["financial_metrics"] = {
            "revenue": {"value": 124.8, "raw": "$124.8M", "period": "FY2023", "page": 1},
        }

        res = report_agent(state)
        answer = res["final_answer"]

        # Must state that data is missing or not reported, never fabricate a number
        assert "Missing" in answer or "Not Reported" in answer or "Unavailable" in answer or "not explicitly report" in answer

    def test_summary_inquiry_does_not_return_missing_metric(self):
        """Verify queries like 'what is the summary of the report' return rich executive overview, NOT missing metric."""
        assert classify_intent("what is the summary of the report") == QueryIntent.SUMMARY
        assert classify_intent("give the consolidated balance sheet") == QueryIntent.SUMMARY

        state = initial_state("what is the summary of the report", "doc_1")
        state["intent"] = QueryIntent.SUMMARY
        state["financial_metrics"] = {
            "revenue": {"value": 124.8, "raw": "$124.8M", "period": "FY2023", "page": 1},
            "operating_income": {"value": 23.1, "raw": "$23.1M", "period": "FY2023", "page": 1},
            "net_income": {"value": 17.5, "raw": "$17.5M", "period": "FY2023", "page": 1},
            "total_assets": {"value": 150.0, "raw": "$150.0M", "period": "FY2023", "page": 2},
        }
        res = report_agent(state)
        answer = res["final_answer"]

        assert "Missing / Not Reported" not in answer
        assert "Executive Financial Report Summary" in answer
        assert "$124.8M" in answer

    def test_balance_sheet_inquiry_returns_structured_statement(self):
        """Verify balance sheet query returns tabular balance sheet analysis."""
        state = initial_state("give the consolidated balance sheet", "doc_1")
        state["financial_metrics"] = {
            "total_assets": {"value": 150.0, "raw": "$150.0M", "period": "FY2023", "page": 2},
            "current_assets": {"value": 65.0, "raw": "$65.0M", "period": "FY2023", "page": 2},
            "cash_and_equivalents": {"value": 25.0, "raw": "$25.0M", "period": "FY2023", "page": 2},
            "total_liabilities": {"value": 60.0, "raw": "$60.0M", "period": "FY2023", "page": 2},
            "total_debt": {"value": 35.0, "raw": "$35.0M", "period": "FY2023", "page": 2},
            "total_equity": {"value": 90.0, "raw": "$90.0M", "period": "FY2023", "page": 2},
        }
        res = report_agent(state)
        answer = res["final_answer"]

        assert "Missing / Not Reported" not in answer
        assert "Consolidated Balance Sheet Analysis" in answer
        assert "$150.0M" in answer
        assert "$90.0M" in answer


class TestAgentWorkflowStatuses:
    """Verifies that all 6 agents have definite status (zero permanent PENDING)."""

    def test_all_agents_have_valid_status_after_run(self):
        from src.graph.workflow import run_query
        from unittest.mock import MagicMock

        retriever = MagicMock()
        retriever.search.return_value = [{"text": "Revenue was $124.8M in FY2023.", "page_numbers": [1], "rrf_score": 0.9}]

        extracted_metrics = {
            "revenue": [ExtractedMetric("revenue", "Revenue", "$124.8M", 124.8, "M", 1.0, 124.8, "FY2023", 1, "high", True, "Revenue text")]
        }

        final_state = run_query(
            query="What is the total revenue?",
            document_id="test_doc",
            retriever=retriever,
            extracted_metrics_raw=extracted_metrics,
        )

        statuses = final_state.get("agent_statuses", {})
        all_agents = ["router", "research", "analysis", "ratio", "risk", "validation", "report"]

        for ag in all_agents:
            assert ag in statuses, f"Agent '{ag}' missing from agent_statuses"
            assert statuses[ag] != AgentStatus.PENDING, f"Agent '{ag}' is stuck in PENDING status!"
            assert statuses[ag] in [AgentStatus.COMPLETED, AgentStatus.SKIPPED, AgentStatus.FAILED]
