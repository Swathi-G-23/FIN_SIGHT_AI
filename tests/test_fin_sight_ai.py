"""
FIN SIGHT AI - Test Suite
Automated tests using synthetic financial data.
All synthetic data is clearly labelled and never presented as real company data.
"""
import io
import math
import sys
import os
import pytest

# Add project root to path so src imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# SYNTHETIC TEST DATA
# Clearly labelled: this data represents a fictional company
# ============================================================

SYNTHETIC_INCOME_STATEMENT = """
--- PAGE 1 ---
SYNTHETIC FINANCIAL REPORT - FICTIONAL COMPANY XYZ LTD
FOR TESTING PURPOSES ONLY - NOT REAL COMPANY DATA

STATEMENT OF PROFIT AND LOSS
For the Year Ended 31 March 2024

                               FY2024          FY2023
Revenue                       500,000         450,000
Cost of Goods Sold            300,000         270,000
Gross Profit                  200,000         180,000
Operating Expenses             80,000          70,000
Operating Profit              120,000         110,000
Finance Costs                  10,000           8,000
Profit Before Tax             110,000         102,000
Tax Expense                    22,000          20,400
Net Profit                     88,000          81,600

BALANCE SHEET as at 31 March 2024

Current Assets                250,000         220,000
Non-Current Assets            400,000         380,000
Total Assets                  650,000         600,000

Current Liabilities           150,000         130,000
Long-Term Debt                100,000          90,000
Total Liabilities             250,000         220,000
Total Equity                  400,000         380,000
"""

SYNTHETIC_PDF_TEXT = SYNTHETIC_INCOME_STATEMENT


# ============================================================
# Unit tests: Text cleaning
# ============================================================
class TestTextCleaner:
    def test_basic_cleaning(self):
        from src.ingestion.text_cleaner import clean_text
        raw = "Hello   World\r\n\n\n\n\nTest"
        result = clean_text(raw)
        assert "Hello World" in result
        assert "\r" not in result

    def test_empty_string(self):
        from src.ingestion.text_cleaner import clean_text
        assert clean_text("") == ""
        assert clean_text("   ") == ""

    def test_normalize_number(self):
        from src.ingestion.text_cleaner import normalize_number
        assert normalize_number("1,23,456.78") == pytest.approx(123456.78)
        assert normalize_number("(5000)") == pytest.approx(-5000.0)
        assert normalize_number("-9999") == pytest.approx(-9999.0)
        assert normalize_number("not_a_number") is None
        assert normalize_number("") is None


# ============================================================
# Unit tests: Financial ratio calculations
# ============================================================
class TestRatioCalculator:
    def setup_method(self):
        from src.finance.ratio_calculator import FinancialRatioCalculator
        self.calc = FinancialRatioCalculator()

    def test_net_profit_margin_normal(self):
        r = self.calc.net_profit_margin(88000, 500000, "FY2024")
        assert r.is_valid
        assert r.result == pytest.approx(17.6, abs=0.01)
        assert "%" in r.unit

    def test_net_profit_margin_zero_revenue(self):
        r = self.calc.net_profit_margin(88000, 0, "FY2024")
        assert not r.is_valid
        assert r.result is None
        assert "zero" in r.error_message.lower()

    def test_net_profit_margin_none_revenue(self):
        r = self.calc.net_profit_margin(88000, None, "FY2024")
        assert not r.is_valid
        assert r.result is None

    def test_operating_profit_margin(self):
        r = self.calc.operating_profit_margin(120000, 500000)
        assert r.is_valid
        assert r.result == pytest.approx(24.0, abs=0.01)

    def test_current_ratio_above_1(self):
        r = self.calc.current_ratio(250000, 150000)
        assert r.is_valid
        assert r.result == pytest.approx(250000 / 150000, rel=1e-4)
        assert "adequate" in r.interpretation.lower() or "strong" in r.interpretation.lower()

    def test_current_ratio_below_1(self):
        r = self.calc.current_ratio(100, 200)
        assert r.is_valid
        assert r.result < 1
        assert "risk" in r.interpretation.lower()

    def test_debt_to_equity(self):
        r = self.calc.debt_to_equity(100000, 400000)
        assert r.is_valid
        assert r.result == pytest.approx(0.25, rel=1e-4)

    def test_debt_to_equity_negative_equity(self):
        r = self.calc.debt_to_equity(100000, -50000)
        # Should still calculate but flag in interpretation
        assert "negative equity" in r.interpretation.lower() or r.result is not None

    def test_revenue_growth_positive(self):
        r = self.calc.revenue_growth(500000, 450000, "FY2024", "FY2023")
        assert r.is_valid
        expected = (500000 - 450000) / 450000 * 100
        assert r.result == pytest.approx(expected, rel=1e-4)

    def test_revenue_growth_negative(self):
        r = self.calc.revenue_growth(400000, 450000, "FY2024", "FY2023")
        assert r.is_valid
        assert r.result < 0

    def test_revenue_growth_zero_prior(self):
        r = self.calc.revenue_growth(500000, 0, "FY2024", "FY2023")
        assert not r.is_valid

    def test_net_profit_growth(self):
        r = self.calc.net_profit_growth(88000, 81600, "FY2024", "FY2023")
        assert r.is_valid
        expected = (88000 - 81600) / abs(81600) * 100
        assert r.result == pytest.approx(expected, rel=1e-4)

    def test_both_none(self):
        r = self.calc.net_profit_margin(None, None)
        assert not r.is_valid
        assert r.result is None


# ============================================================
# Unit tests: Text chunker
# ============================================================
class TestTextChunker:
    def setup_method(self):
        from src.ingestion.chunker import TextChunker
        from src.ingestion.pdf_extractor import PageContent
        self.chunker = TextChunker(chunk_size=300, chunk_overlap=50)
        self.pages = [
            PageContent(
                page_number=1,
                text="Revenue 500000\nNet Profit 88000\n" * 10,
                word_count=40,
                char_count=400,
            ),
            PageContent(
                page_number=2,
                text="Total Assets 650000\nTotal Equity 400000\n" * 10,
                word_count=40,
                char_count=400,
            ),
        ]

    def test_chunk_count(self):
        chunks = self.chunker.chunk_document("test_doc", self.pages)
        assert len(chunks) > 0

    def test_chunk_ids_unique(self):
        chunks = self.chunker.chunk_document("test_doc", self.pages)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_page_numbers_preserved(self):
        chunks = self.chunker.chunk_document("test_doc", self.pages)
        all_pages = set()
        for c in chunks:
            all_pages.update(c.page_numbers)
        assert 1 in all_pages
        assert 2 in all_pages

    def test_chunk_size_respected(self):
        chunks = self.chunker.chunk_document("test_doc", self.pages)
        for c in chunks:
            # No chunk should massively exceed max size
            assert len(c.text) <= self.chunker.chunk_size * 3


# ============================================================
# Unit tests: Metric extraction
# ============================================================
class TestMetricExtraction:
    def _make_pages(self, text):
        from src.ingestion.pdf_extractor import PageContent
        return [PageContent(page_number=1, text=text, word_count=50, char_count=len(text))]

    def test_revenue_extraction(self):
        from src.finance.metric_extraction import extract_financial_metrics
        pages = self._make_pages("Revenue 500,000\nNet Profit 88,000\n")
        metrics = extract_financial_metrics(pages)
        assert len(metrics["revenue"]) > 0 or len(metrics["net_profit"]) > 0  # at least one found

    def test_no_metrics_in_garbage(self):
        from src.finance.metric_extraction import extract_financial_metrics
        pages = self._make_pages("Lorem ipsum dolor sit amet.")
        metrics = extract_financial_metrics(pages)
        total = sum(len(v) for v in metrics.values())
        # May find incidental matches, but not many
        assert total < 5

    def test_metrics_summary_structure(self):
        from src.finance.metric_extraction import extract_financial_metrics, metrics_summary
        pages = self._make_pages("Revenue 500000\nNet Profit 88000\n")
        raw = extract_financial_metrics(pages)
        summary = metrics_summary(raw)
        # Summary should be a dict
        assert isinstance(summary, dict)


# ============================================================
# Unit tests: Risk analysis
# ============================================================
class TestRiskAnalysis:
    def test_no_data_returns_info(self):
        from src.finance.trend_analysis import identify_risks_from_trends
        findings = identify_risks_from_trends({}, {})
        assert len(findings) > 0
        assert any(f["level"] == "Info" for f in findings)

    def test_negative_margin_is_high_risk(self):
        from src.finance.trend_analysis import identify_risks_from_trends
        from src.finance.ratio_calculator import FinancialRatioCalculator
        calc = FinancialRatioCalculator()
        ratios = {
            "Net Profit Margin": calc.net_profit_margin(-5000, 100000),
        }
        findings = identify_risks_from_trends({}, ratios)
        high_risk = [f for f in findings if f["level"] == "High"]
        assert len(high_risk) > 0

    def test_current_ratio_below_1_is_high_risk(self):
        from src.finance.trend_analysis import identify_risks_from_trends
        from src.finance.ratio_calculator import FinancialRatioCalculator
        calc = FinancialRatioCalculator()
        ratios = {
            "Current Ratio": calc.current_ratio(50, 200),
        }
        findings = identify_risks_from_trends({}, ratios)
        high_risk = [f for f in findings if f["level"] == "High" and "Liquidity" in f.get("category", "")]
        assert len(high_risk) > 0


# ============================================================
# Unit tests: Intent routing
# ============================================================
class TestIntentRouter:
    def test_numerical_intent(self):
        from src.graph.router import classify_intent
        from src.graph.state import QueryIntent
        intent = classify_intent("What is the profit margin?")
        assert intent in (QueryIntent.NUMERICAL, QueryIntent.GENERAL)

    def test_risk_intent(self):
        from src.graph.router import classify_intent
        from src.graph.state import QueryIntent
        intent = classify_intent("What are the major financial risks?")
        assert intent == QueryIntent.RISK

    def test_summary_intent(self):
        from src.graph.router import classify_intent
        from src.graph.state import QueryIntent
        intent = classify_intent("Summarize the company financial performance")
        assert intent in (QueryIntent.SUMMARY, QueryIntent.GENERAL)

    def test_empty_query_defaults(self):
        from src.graph.router import classify_intent
        from src.graph.state import QueryIntent
        intent = classify_intent("")
        assert intent == QueryIntent.GENERAL


# ============================================================
# Unit tests: Validation agent (no LLM)
# ============================================================
class TestValidationAgent:
    def test_valid_calculation_passes(self):
        from src.agents.validation_agent import validation_agent
        from src.finance.ratio_calculator import FinancialRatioCalculator
        from src.graph.state import initial_state

        calc = FinancialRatioCalculator()
        state = initial_state("test", "doc1")
        state["calculated_ratios"] = {
            "Net Profit Margin": calc.net_profit_margin(88000, 500000),
        }
        state["financial_metrics"] = {"revenue": {"value": 500000}}
        state["context_text"] = "Some context"
        state["errors"] = []

        result = validation_agent(state)
        notes = result.get("validation_notes", [])
        # Should have at least one verification note
        assert any("verified" in n.lower() or "net profit margin" in n.lower() for n in notes)

    def test_missing_metrics_noted(self):
        from src.agents.validation_agent import validation_agent
        from src.graph.state import initial_state

        state = initial_state("test", "doc1")
        state["calculated_ratios"] = {}
        state["financial_metrics"] = {}
        state["context_text"] = "test"
        state["errors"] = []

        result = validation_agent(state)
        notes = result.get("validation_notes", [])
        assert any("revenue" in n.lower() or "metric" in n.lower() for n in notes)


# ============================================================
# Performance test: chunking and embedding
# ============================================================
class TestPerformance:
    def _make_document(self, n_pages: int, chars_per_page: int):
        from src.ingestion.pdf_extractor import PageContent
        pages = []
        for i in range(n_pages):
            text = f"Revenue {i * 1000}\nNet Profit {i * 500}\n" * (chars_per_page // 30)
            pages.append(PageContent(
                page_number=i + 1,
                text=text,
                word_count=len(text.split()),
                char_count=len(text),
            ))
        return pages

    def test_chunking_100_pages(self):
        import time
        from src.ingestion.chunker import TextChunker

        pages = self._make_document(100, 2000)
        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        start = time.time()
        chunks = chunker.chunk_document("perf_test", pages)
        elapsed = time.time() - start

        assert len(chunks) > 0
        print(f"\n[PERF] 100-page doc → {len(chunks)} chunks in {elapsed:.2f}s")
        assert elapsed < 30.0, f"Chunking too slow: {elapsed:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
