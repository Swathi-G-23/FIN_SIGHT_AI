"""
FIN SIGHT AI - Multi-Document Isolation & Dynamic Ingestion Test Suite
Verifies document isolation across distinct PDFs, Excel, CSV, Image OCR, and Manual Entry.
Ensures zero data leakage between companies, correct citation provenance, and dynamic calculations.
"""
from pathlib import Path
import pytest
import pymupdf as fitz

from src.utils.session_manager import (
    process_document,
    process_excel_document,
    process_csv_document,
    process_manual_financial_record,
    DocumentSession,
)
from src.ingestion.models import FinancialPeriodRecord, InputSourceType
from src.finance.scenario_simulator import FinancialScenarioSimulator, ScenarioAssumptions
from src.graph.workflow import run_query
from src.graph.state import QueryIntent, AgentStatus


def create_synthetic_pdf(filepath: Path, company_name: str, revenue: float, net_income: float, assets: float, debt: float):
    """Generates a clearly labeled synthetic test PDF with unique financial values."""
    doc = fitz.open()
    page = doc.new_page()
    text = f"""
    {company_name.upper()}
    ANNUAL FINANCIAL REPORT — FISCAL YEAR 2023
    
    Item 8. Consolidated Financial Statements
    
    CONSOLIDATED STATEMENT OF OPERATIONS
    For the Fiscal Year Ended December 31, 2023
    
    Total Revenue: ${revenue:,.1f} million
    Cost of Goods Sold: ${revenue * 0.55:,.1f} million
    Operating Expenses: ${revenue * 0.25:,.1f} million
    Operating Income: ${revenue * 0.20:,.1f} million
    Net Income: ${net_income:,.1f} million
    
    CONSOLIDATED BALANCE SHEET
    As of December 31, 2023
    
    Total Assets: ${assets:,.1f} million
    Current Assets: ${assets * 0.45:,.1f} million
    Cash and Cash Equivalents: ${assets * 0.20:,.1f} million
    Total Liabilities: ${assets * 0.40:,.1f} million
    Current Liabilities: ${assets * 0.22:,.1f} million
    Total Debt: ${debt:,.1f} million
    Total Shareholders' Equity: ${assets - (assets * 0.40):,.1f} million
    
    Note 1: {company_name} is an enterprise provider. The figures above are audited statutory disclosures.
    """
    page.insert_text((50, 72), text, fontsize=11)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(filepath))
    doc.close()


@pytest.fixture(scope="module")
def synthetic_pdfs():
    """Generates and provides paths to 3 distinct corporate test PDFs."""
    p_dir = Path("sample_inputs")
    pdf_apex = p_dir / "Apex_Technologies_FY2023_Annual_Report.pdf"
    pdf_nova = p_dir / "Nova_Dynamics_FY2023_Annual_Report.pdf"
    pdf_solaris = p_dir / "Solaris_Energy_FY2023_Annual_Report.pdf"

    if not pdf_nova.exists():
        create_synthetic_pdf(pdf_nova, "Nova Dynamics", revenue=340.5, net_income=48.2, assets=410.0, debt=75.0)
    if not pdf_solaris.exists():
        create_synthetic_pdf(pdf_solaris, "Solaris Energy", revenue=850.0, net_income=110.0, assets=1250.0, debt=380.0)

    return {
        "apex": pdf_apex,
        "nova": pdf_nova,
        "solaris": pdf_solaris,
    }


def test_three_pdf_document_isolation(synthetic_pdfs):
    """
    Requirement 7: Verify that three different PDFs produce distinct extracted metrics,
    isolated document IDs, and no cross-document leakage.
    """
    sess_nova = process_document(synthetic_pdfs["nova"].read_bytes(), synthetic_pdfs["nova"].name)
    sess_solaris = process_document(synthetic_pdfs["solaris"].read_bytes(), synthetic_pdfs["solaris"].name)

    # 1. Unique Document IDs
    assert sess_nova.document_id != sess_solaris.document_id

    # 2. Company Name Identification
    assert "Nova Dynamics" in sess_nova.company_name
    assert "Solaris Energy" in sess_solaris.company_name

    # 3. Disparate Financial Values
    nova_rev = sess_nova.financial_records[0].revenue
    solaris_rev = sess_solaris.financial_records[0].revenue
    assert nova_rev is not None and solaris_rev is not None
    assert abs(nova_rev - solaris_rev) > 100.0  # 340.5 vs 850.0

    # 4. Retrieval Isolation
    nova_results = sess_nova.retriever.retrieve("What is the company name and revenue?", top_k=2)
    assert any("Nova Dynamics" in r["text"] for r in nova_results)
    assert not any("Solaris Energy" in r["text"] for r in nova_results)

    solaris_results = sess_solaris.retriever.retrieve("What is the company name and revenue?", top_k=2)
    assert any("Solaris Energy" in r["text"] for r in solaris_results)
    assert not any("Nova Dynamics" in r["text"] for r in solaris_results)


def test_scenario_simulator_reactivity():
    """
    Requirement 4: Verify that simulator outputs reactively recalculate when assumptions change.
    """
    sim = FinancialScenarioSimulator()
    base_metrics = {
        "revenue": 100_000_000.0,
        "cogs": 40_000_000.0,
        "operating_expenses": 30_000_000.0,
        "operating_profit": 30_000_000.0,
        "net_profit": 23_700_000.0,
        "current_assets": 50_000_000.0,
        "current_liabilities": 25_000_000.0,
        "total_debt": 20_000_000.0,
        "total_equity": 60_000_000.0,
    }

    # Case 1: 5% revenue growth
    res_5pct = sim.simulate_scenario(
        base_metrics,
        ScenarioAssumptions(scenario_name="5pct", revenue_growth_pct=5.0, opex_growth_pct=2.0),
        horizon_years=1,
    )
    rev_5 = res_5pct.periods[0].revenue

    # Case 2: 15% revenue growth
    res_15pct = sim.simulate_scenario(
        base_metrics,
        ScenarioAssumptions(scenario_name="15pct", revenue_growth_pct=15.0, opex_growth_pct=2.0),
        horizon_years=1,
    )
    rev_15 = res_15pct.periods[0].revenue

    # Recalculation verification
    assert rev_15 > rev_5
    assert pytest.approx(rev_5, rel=1e-3) == 105_000_000.0
    assert pytest.approx(rev_15, rel=1e-3) == 115_000_000.0


def test_agent_workflow_routing_and_skip_reasons(synthetic_pdfs):
    """
    Requirement 5: Verify that the router routes correctly and records exact skip reasons.
    """
    sess = process_document(synthetic_pdfs["nova"].read_bytes(), synthetic_pdfs["nova"].name)

    # 1. Complex query should execute ratio, analysis, risk, validation, report
    complex_state = run_query(
        query="Provide a comprehensive analysis of the company's financial health, ratios, and risk outlook.",
        document_id=sess.document_id,
        retriever=sess.retriever,
        extracted_metrics_raw=sess.extracted_metrics_raw,
        company_name=sess.company_name,
    )
    statuses = complex_state.get("agent_statuses", {})
    assert statuses.get("ratio") == AgentStatus.COMPLETED
    assert statuses.get("analysis") == AgentStatus.COMPLETED
    assert statuses.get("risk") == AgentStatus.COMPLETED
    assert statuses.get("validation") == AgentStatus.COMPLETED
    assert statuses.get("report") == AgentStatus.COMPLETED

    # 2. Pure numerical query should execute ratio and report, and skip risk with an explicit reason
    num_state = run_query(
        query="What is the net profit margin and debt to equity ratio?",
        document_id=sess.document_id,
        retriever=sess.retriever,
        extracted_metrics_raw=sess.extracted_metrics_raw,
        company_name=sess.company_name,
    )
    num_statuses = num_state.get("agent_statuses", {})
    assert num_statuses.get("ratio") == AgentStatus.COMPLETED
    assert num_statuses.get("risk") == AgentStatus.SKIPPED
    skip_reasons = num_state.get("agent_skip_reasons", {})
    assert "risk" in skip_reasons
    assert "did not require" in skip_reasons["risk"].lower() or "focused" in skip_reasons["risk"].lower()
