"""
FIN SIGHT AI - Advanced Feature Test Suite
Tests multimodal ingestion (Excel, CSV, Manual, OCR), multi-period comparisons,
storage adapters, performance monitoring, and advanced Plotly charts.
All datasets used are synthetic and clearly labelled for testing.
"""
import os
import sys
import tempfile
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.models import FinancialPeriodRecord, InputSourceType, SourceProvenance
from src.ingestion.excel_extractor import ExcelExtractor
from src.ingestion.csv_extractor import CSVExtractor
from src.ingestion.manual_entry import ManualDataEntryManager
from src.ingestion.image_ocr_extractor import ImageOCRExtractor
from src.ingestion.comparator import FinancialComparator
from src.storage.storage_adapter import LocalStorageAdapter
from src.monitoring.performance import PerformanceMonitor
from src.finance.charts import (
    create_revenue_trend_chart,
    create_revenue_vs_profit_chart,
    create_financial_waterfall_chart,
    create_risk_heatmap,
    create_kpi_gauge,
)


class TestExcelExtractor:
    def test_excel_extraction(self, tmp_path):
        # Create synthetic Excel file
        file_path = tmp_path / "synthetic_financial_model.xlsx"
        df = pd.DataFrame({
            "Line Item": ["Revenue", "Cost of Goods Sold", "Gross Profit", "Operating Income", "Net Income"],
            "FY2023": [1200.0, 700.0, 500.0, 200.0, 150.0],
            "FY2022": [1000.0, 600.0, 400.0, 150.0, 100.0],
        })
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Income_Statement", index=False)

        extractor = ExcelExtractor()
        sheets = extractor.inspect_sheets(file_path)
        assert "Income_Statement" in sheets

        result = extractor.extract(file_path, sheet_name="Income_Statement", company_name="Synthetic Corp")
        assert len(result.financial_records) == 2
        
        # Verify FY2023 record
        rec_23 = next((r for r in result.financial_records if r.reporting_period == "FY2023"), None)
        assert rec_23 is not None
        assert rec_23.revenue == 1200.0
        assert rec_23.net_income == 150.0
        assert "revenue" in rec_23.provenance
        assert rec_23.provenance["revenue"].source_type == InputSourceType.EXCEL


class TestCSVExtractor:
    def test_csv_extraction_and_validation(self, tmp_path):
        file_path = tmp_path / "synthetic_dataset.csv"
        df = pd.DataFrame({
            "company": ["Alpha Inc", "Alpha Inc"],
            "year": ["2022", "2023"],
            "revenue": [500.0, 650.0],
            "operating_income": [80.0, 110.0],
            "net_income": [60.0, 90.0],
            "total_assets": [400.0, 520.0],
            "total_liabilities": [200.0, 250.0],
            "total_debt": [100.0, 120.0],
            "total_equity": [200.0, 270.0],
        })
        df.to_csv(file_path, index=False)

        extractor = CSVExtractor()
        result = extractor.extract(file_path, default_company="Alpha Inc")

        assert result.validation.is_valid is True
        assert len(result.financial_records) == 2
        r23 = next(r for r in result.financial_records if r.reporting_period == "2023")
        assert r23.revenue == 650.0
        assert r23.net_income == 90.0
        assert r23.provenance["revenue"].source_type == InputSourceType.CSV


class TestManualDataEntry:
    def test_valid_entry(self):
        manager = ManualDataEntryManager()
        res = manager.create_record(
            company_name="Beta Corp",
            reporting_period="FY2023",
            revenue=1000.0,
            cost_of_goods_sold=600.0,
            gross_profit=400.0,
            operating_income=150.0,
            net_income=120.0,
            total_assets=800.0,
            current_assets=350.0,
            total_liabilities=300.0,
            current_liabilities=180.0,
            total_debt=150.0,
            total_equity=500.0,
        )
        assert res.is_valid is True
        assert res.record is not None
        assert res.record.get_ratio("current_ratio") == round(350.0 / 180.0, 2)
        assert res.record.provenance["revenue"].source_type == InputSourceType.MANUAL

    def test_invalid_negative_assets(self):
        manager = ManualDataEntryManager()
        res = manager.create_record(
            company_name="Beta Corp",
            reporting_period="FY2023",
            total_assets=-500.0,
        )
        assert res.is_valid is False
        assert any("cannot be negative" in e for e in res.errors)


class TestImageOCRExtractor:
    def test_ocr_handler_availability(self):
        extractor = ImageOCRExtractor()
        # Verify handler returns boolean without raising
        is_avail = extractor.is_ocr_available()
        assert isinstance(is_avail, bool)


class TestFinancialComparator:
    def test_multi_period_comparison(self):
        rec_22 = FinancialPeriodRecord(
            company_name="Gamma Tech", reporting_period="FY2022",
            revenue=1000.0, net_income=100.0, current_assets=300.0, current_liabilities=200.0,
            total_debt=100.0, total_equity=400.0
        )
        rec_23 = FinancialPeriodRecord(
            company_name="Gamma Tech", reporting_period="FY2023",
            revenue=1200.0, net_income=150.0, current_assets=400.0, current_liabilities=200.0,
            total_debt=120.0, total_equity=500.0
        )

        comparator = FinancialComparator()
        res = comparator.compare_periods([rec_22, rec_23], target_company="Gamma Tech")

        assert res.has_comparable_data is True
        assert len(res.periods) == 2
        rev_row = next(r for r in res.metric_rows if r.metric_name == "Revenue")
        assert rev_row.absolute_change == 200.0
        assert rev_row.percentage_change == 20.0 # +20% growth

        # Check net profit margin ratio delta
        npm_row = next(r for r in res.ratio_rows if "Net Profit Margin" in r.metric_name)
        assert npm_row.values_by_period["FY2022"] == 10.0
        assert npm_row.values_by_period["FY2023"] == 12.5
        assert npm_row.absolute_change == 2.5


class TestStorageAdapter:
    def test_local_storage_lifecycle(self, tmp_path):
        adapter = LocalStorageAdapter(base_dir=tmp_path)
        sample_bytes = b"FINANCIAL_DATA_TEST_BYTES"
        dest_path = str(tmp_path / "uploads" / "doc.pdf")
        saved_uri = adapter.save_file(sample_bytes, dest_path)
        assert os.path.exists(saved_uri)

        read_bytes = adapter.get_file(saved_uri)
        assert read_bytes == sample_bytes

        deleted = adapter.delete_file(saved_uri)
        assert deleted is True
        assert not os.path.exists(saved_uri)


class TestPerformanceMonitor:
    def test_system_resources_and_benchmark(self):
        monitor = PerformanceMonitor()
        sys_res = monitor.get_system_resources()
        assert "process_memory_mb" in sys_res
        assert sys_res["process_memory_mb"] > 0
        assert "cpu_count_logical" in sys_res

        # Run small synthetic benchmark
        bench = monitor.run_benchmark(size_category="Small")
        assert bench.benchmark_size == "Small"
        assert bench.page_count == 5
        assert bench.char_count > 0
        assert bench.chunk_count > 0
        assert bench.ingestion_time_sec > 0
        assert bench.retrieval_latency_ms > 0


class TestPlotlyCharts:
    def test_charts_data_integrity(self):
        periods = ["FY2022", "FY2023"]
        revs = [1000.0, 1250.0]
        profits = [100.0, 140.0]

        fig_rev, df_rev = create_revenue_trend_chart(periods, revs, unit="$M")
        assert len(df_rev) == 2
        assert fig_rev is not None

        fig_comp, df_comp = create_revenue_vs_profit_chart(periods, revs, profits, unit="$M")
        assert len(df_comp) == 2

        fig_wf, df_wf = create_financial_waterfall_chart(1250.0, 750.0, 320.0, 25.0, 140.0, unit="$M")
        assert len(df_wf) == 7

        fig_heat, df_heat = create_risk_heatmap(
            ["Liquidity", "Leverage"], ["FY2022", "FY2023"], [[0.2, 0.15], [0.3, 0.35]]
        )
        assert df_heat.shape == (2, 2)

        fig_gauge = create_kpi_gauge(1.80, "Current Ratio", min_val=0, max_val=4.0)
        assert fig_gauge is not None
