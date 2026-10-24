"""
FIN SIGHT AI - Comprehensive Sample Input Generator
Generates realistic corporate sample inputs across all supported multimodal formats:
- PDF: Audited 10-K Style Annual Report
- Excel (.xlsx): Multi-sheet financial model (Income Statement, Balance Sheet, Cash Flow, Ratios)
- CSV: Time-series financial metrics and multi-company comparative dataset
- TXT: Detailed earnings release with audited GAAP tables and narrative commentary
- Image (.png): High-contrast financial table scan for OCR testing
- JSON: Structured financial record catalog
"""
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Target directories
BASE_DIR = Path(__file__).resolve().parent
SAMPLE_INPUTS_DIR = BASE_DIR / "sample_inputs"
SAMPLE_REPORTS_DIR = BASE_DIR / "sample_reports"
SAMPLE_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------------- #
# 1. Excel (.xlsx) Multi-Sheet Financial Model
# -------------------------------------------------------------------------- #
def generate_excel_model():
    file_path = SAMPLE_INPUTS_DIR / "Apex_Technologies_Financial_Model_FY2021_FY2023.xlsx"
    
    # Sheet 1: Income Statement
    df_is = pd.DataFrame({
        "Line Item ($ in Millions)": [
            "Revenue",
            "Cost of Goods Sold (COGS)",
            "Gross Profit",
            "Research & Development",
            "Selling, General & Administrative",
            "Total Operating Expenses",
            "Operating Income (EBIT)",
            "Interest Expense",
            "Income Before Taxes (EBT)",
            "Income Tax Expense (21%)",
            "Net Income",
        ],
        "FY2021": [89.2, 38.4, 50.8, 18.2, 17.0, 35.2, 15.6, 1.4, 14.2, 2.98, 11.22],
        "FY2022": [108.5, 45.6, 62.9, 22.5, 21.2, 43.7, 19.2, 1.6, 17.6, 3.70, 13.90],
        "FY2023": [124.8, 50.5, 74.3, 26.4, 24.8, 51.2, 23.1, 1.5, 21.6, 4.54, 17.06],
    })

    # Sheet 2: Balance Sheet
    df_bs = pd.DataFrame({
        "Balance Sheet Item ($ in Millions)": [
            "Cash & Cash Equivalents",
            "Accounts Receivable",
            "Inventory",
            "Prepaid Expenses",
            "Total Current Assets",
            "Property, Plant & Equipment (Net)",
            "Intangible Assets & Goodwill",
            "Total Non-Current Assets",
            "Total Assets",
            "Accounts Payable",
            "Accrued Liabilities",
            "Short-Term Borrowings",
            "Total Current Liabilities",
            "Long-Term Senior Debt",
            "Total Liabilities",
            "Common Stock",
            "Retained Earnings",
            "Total Stockholders' Equity",
            "Total Liabilities & Equity",
        ],
        "FY2021": [21.5, 14.8, 10.2, 2.5, 49.0, 32.0, 17.0, 49.0, 98.0, 14.2, 8.8, 3.0, 26.0, 16.0, 42.0, 25.0, 31.0, 56.0, 98.0],
        "FY2022": [25.0, 16.5, 12.4, 3.1, 57.0, 41.0, 22.0, 63.0, 120.0, 16.5, 11.1, 4.4, 32.0, 20.0, 52.0, 25.0, 43.0, 68.0, 120.0],
        "FY2023": [28.2, 18.4, 14.2, 3.6, 64.4, 52.0, 28.6, 80.6, 145.0, 18.2, 12.4, 5.0, 35.6, 25.4, 61.0, 25.0, 59.0, 84.0, 145.0],
    })

    # Sheet 3: Cash Flow Statement
    df_cf = pd.DataFrame({
        "Cash Flow Statement ($ in Millions)": [
            "Net Income",
            "Depreciation & Amortization",
            "Change in Working Capital",
            "Cash Flow from Operations (OCF)",
            "Capital Expenditures (CapEx)",
            "Cash Flow from Investing",
            "Net Repayment / Issuance of Debt",
            "Dividends Paid",
            "Cash Flow from Financing",
            "Net Change in Cash",
        ],
        "FY2021": [11.22, 5.4, -0.62, 16.0, -9.5, -9.5, -2.0, -1.0, -3.0, 3.5],
        "FY2022": [13.90, 6.8, 0.30, 21.0, -13.0, -13.0, 0.0, -4.5, -4.5, 3.5],
        "FY2023": [17.06, 8.2, 1.14, 26.4, -16.2, -16.2, 1.0, -8.0, -7.0, 3.2],
    })

    # Sheet 4: Financial Ratios
    df_ratios = pd.DataFrame({
        "Key Ratio": [
            "Gross Profit Margin (%)",
            "Operating Margin (%)",
            "Net Profit Margin (%)",
            "Current Ratio (x)",
            "Quick Ratio (x)",
            "Debt-to-Equity (x)",
            "Debt Ratio (%)",
            "Return on Assets (ROA %)",
            "Return on Equity (ROE %)",
            "Working Capital ($M)",
        ],
        "FY2021": [56.95, 17.49, 12.58, 1.88, 1.49, 0.34, 42.86, 11.45, 20.04, 23.0],
        "FY2022": [57.97, 17.70, 12.81, 1.78, 1.39, 0.36, 43.33, 11.58, 20.44, 25.0],
        "FY2023": [59.54, 18.51, 13.67, 1.81, 1.41, 0.36, 42.07, 11.77, 20.31, 28.8],
    })

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df_is.to_excel(writer, sheet_name="Income_Statement", index=False)
        df_bs.to_excel(writer, sheet_name="Balance_Sheet", index=False)
        df_cf.to_excel(writer, sheet_name="Cash_Flow", index=False)
        df_ratios.to_excel(writer, sheet_name="Financial_Ratios", index=False)
        
    print(f"Generated Excel: {file_path}")
    return file_path


# -------------------------------------------------------------------------- #
# 2. CSV Files (Time Series & Multi-Company Comparative)
# -------------------------------------------------------------------------- #
def generate_csv_datasets():
    # 2a. Time series metrics for Apex Technologies
    ts_path = SAMPLE_INPUTS_DIR / "Apex_Technologies_Financial_Metrics_FY2020_FY2023.csv"
    df_ts = pd.DataFrame({
        "company_name": ["Apex Technologies Ltd."] * 4,
        "reporting_period": ["FY2020", "FY2021", "FY2022", "FY2023"],
        "revenue": [78400000.0, 89200000.0, 108500000.0, 124800000.0],
        "cogs": [34500000.0, 38400000.0, 45600000.0, 50500000.0],
        "gross_profit": [43900000.0, 50800000.0, 62900000.0, 74300000.0],
        "operating_expenses": [31800000.0, 35200000.0, 43700000.0, 51200000.0],
        "operating_profit": [12100000.0, 15600000.0, 19200000.0, 23100000.0],
        "net_profit": [9200000.0, 11220000.0, 13900000.0, 17060000.0],
        "current_assets": [42000000.0, 49000000.0, 57000000.0, 64400000.0],
        "inventory": [8500000.0, 10200000.0, 12400000.0, 14200000.0],
        "current_liabilities": [22000000.0, 26000000.0, 32000000.0, 35600000.0],
        "total_debt": [15000000.0, 19000000.0, 24400000.0, 30400000.0],
        "total_equity": [50000000.0, 56000000.0, 68000000.0, 84000000.0],
        "total_assets": [85000000.0, 98000000.0, 120000000.0, 145000000.0],
        "total_liabilities": [35000000.0, 42000000.0, 52000000.0, 61000000.0],
        "operating_cash_flow": [14000000.0, 16000000.0, 21000000.0, 26400000.0],
    })
    df_ts.to_csv(ts_path, index=False)
    print(f"Generated CSV: {ts_path}")

    # 2b. Multi-Company Comparative Sector Dataset (FY2023)
    comp_path = SAMPLE_INPUTS_DIR / "Tech_Sector_Peer_Comparison_FY2023.csv"
    df_comp = pd.DataFrame({
        "company_name": ["Apex Technologies", "Horizon Cloud Systems", "Quantum Data Corp", "Nexus Software"],
        "reporting_period": ["FY2023", "FY2023", "FY2023", "FY2023"],
        "revenue": [124800000.0, 210500000.0, 78200000.0, 165000000.0],
        "cogs": [50500000.0, 88400000.0, 32100000.0, 62700000.0],
        "operating_profit": [23100000.0, 37800000.0, 11500000.0, 31200000.0],
        "net_profit": [17060000.0, 28100000.0, 8400000.0, 23500000.0],
        "current_assets": [64400000.0, 92000000.0, 41000000.0, 76000000.0],
        "current_liabilities": [35600000.0, 48000000.0, 24000000.0, 39000000.0],
        "total_debt": [30400000.0, 45000000.0, 18000000.0, 28000000.0],
        "total_equity": [84000000.0, 125000000.0, 45000000.0, 98000000.0],
        "total_assets": [145000000.0, 218000000.0, 87000000.0, 165000000.0],
        "operating_cash_flow": [26400000.0, 42000000.0, 13500000.0, 34000000.0],
    })
    df_comp.to_csv(comp_path, index=False)
    print(f"Generated CSV: {comp_path}")


# -------------------------------------------------------------------------- #
# 3. Formatted Financial TXT Earnings Release
# -------------------------------------------------------------------------- #
def generate_txt_report():
    file_path = SAMPLE_INPUTS_DIR / "Apex_Technologies_FY2023_Earnings_Release.txt"
    content = """================================================================================
APEX TECHNOLOGIES LTD. — FOURTH QUARTER AND FULL YEAR 2023 FINANCIAL RESULTS
================================================================================
FOR IMMEDIATE RELEASE

NEW YORK, NY — Apex Technologies Ltd. (NASDAQ: APEX) today announced audited 
financial results for the fiscal year ended December 31, 2023.

EXECUTIVE SUMMARY
-----------------
* Total revenue increased 15.0% year-over-year to $124.8 million, up from $108.5 million in FY2022.
* Gross profit expanded to $74.3 million (59.5% gross margin) compared to $62.9 million in FY2022.
* Operating profit (EBIT) grew 20.3% to $23.1 million, delivering an operating margin of 18.5%.
* Net income reached $17.06 million, representing diluted earnings per share of $1.36.
* Operating cash flow was strong at $26.4 million, representing 155% cash conversion of net income.

CONSOLIDATED STATEMENT OF OPERATIONS (AUDITED)
(Amounts in millions of USD, except per share data)
--------------------------------------------------------------------------------
Line Item                                  FY2023       FY2022       YoY Growth
--------------------------------------------------------------------------------
Revenue                                    $124.80      $108.50       +15.02%
Cost of Goods Sold                          $50.50       $45.60       +10.75%
--------------------------------------------------------------------------------
Gross Profit                                $74.30       $62.90       +18.12%
Gross Margin %                               59.54%       57.97%      +157 bps

Research & Development                      $26.40       $22.50       +17.33%
Selling, General & Administrative           $24.80       $21.20       +16.98%
Total Operating Expenses                    $51.20       $43.70       +17.16%
--------------------------------------------------------------------------------
Operating Income (EBIT)                     $23.10       $19.20       +20.31%
Operating Margin %                           18.51%       17.70%       +81 bps

Interest Expense                             $1.50        $1.60        -6.25%
Income Before Taxes (EBT)                   $21.60       $17.60       +22.73%
Income Tax Expense (21%)                     $4.54        $3.70       +22.70%
--------------------------------------------------------------------------------
Net Income                                  $17.06       $13.90       +22.73%
Net Profit Margin %                          13.67%       12.81%       +86 bps
================================================================================

CONSOLIDATED BALANCE SHEET SUMMARY
(As of December 31, 2023 and 2022, in millions of USD)
--------------------------------------------------------------------------------
Assets                                     FY2023       FY2022
--------------------------------------------------------------------------------
Cash and Cash Equivalents                   $28.20       $25.00
Accounts Receivable                         $18.40       $16.50
Inventories                                 $14.20       $12.40
Prepaid Expenses                             $3.60        $3.10
Total Current Assets                        $64.40       $57.00
Property, Plant & Equipment (Net)           $52.00       $41.00
Goodwill & Intangible Assets                $28.60       $22.00
--------------------------------------------------------------------------------
TOTAL ASSETS                               $145.00      $120.00
================================================================================

Liabilities & Stockholders' Equity          FY2023       FY2022
--------------------------------------------------------------------------------
Accounts Payable                            $18.20       $16.50
Accrued Compensation & Liabilities          $12.40       $11.10
Short-Term Credit Obligations                $5.00        $4.40
Total Current Liabilities                   $35.60       $32.00
Long-Term Debt                              $25.40       $20.00
Total Liabilities                           $61.00       $52.00
Stockholders' Equity                        $84.00       $68.00
--------------------------------------------------------------------------------
TOTAL LIABILITIES & EQUITY                 $145.00      $120.00
================================================================================

KEY AUDITED FINANCIAL RATIOS
--------------------------------------------------------------------------------
Ratio Formula                              Calculation                     Result
--------------------------------------------------------------------------------
Current Ratio (CA / CL)                    $64.40 / $35.60                  1.81x
Quick Ratio ((CA - Inv - Prep) / CL)       ($64.40 - 14.20 - 3.60) / 35.60  1.31x
Debt-to-Equity (Total Debt / Equity)       $30.40 / $84.00                  0.36x
Debt Ratio (Total Liab / Total Assets)     $61.00 / $145.00                42.07%
Working Capital (CA - CL)                  $64.40 - $35.60                 $28.80M
Operating Cash Flow Ratio (OCF / CL)       $26.40 / $35.60                  0.74x
================================================================================
MANAGEMENT COMMENTARY
"We concluded FY2023 with record operational performance and robust margin 
expansion across enterprise software and cloud consulting lines. Our disciplined 
balance sheet management maintains conservative financial leverage of 0.36x D/E 
and strong liquidity with $28.2 million in unencumbered cash."
================================================================================
"""
    file_path.write_text(content, encoding="utf-8")
    print(f"Generated TXT: {file_path}")
    return file_path


# -------------------------------------------------------------------------- #
# 4. Statement Scan Image (.png) for OCR Testing
# -------------------------------------------------------------------------- #
def generate_ocr_image():
    file_path = SAMPLE_INPUTS_DIR / "Apex_Technologies_Balance_Sheet_Scan.png"
    
    # Create white canvas
    width, height = 1000, 750
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw simple clean typography
    # Use default font
    draw.rectangle([20, 20, width - 20, height - 20], outline=(23, 54, 93), width=2)
    
    # Title
    draw.text((40, 40), "APEX TECHNOLOGIES LTD.", fill=(23, 54, 93))
    draw.text((40, 65), "CONSOLIDATED STATEMENT OF FINANCIAL POSITION (AUDITED)", fill=(100, 110, 130))
    draw.text((40, 85), "As of December 31, 2023 | Amounts in Millions of USD ($)", fill=(100, 110, 130))
    
    draw.line([(40, 115), (width - 40, 115)], fill=(200, 210, 225), width=2)
    
    # Table Header
    draw.text((50, 130), "LINE ITEM", fill=(23, 54, 93))
    draw.text((650, 130), "FY2023 ($M)", fill=(23, 54, 93))
    draw.text((800, 130), "FY2022 ($M)", fill=(23, 54, 93))
    draw.line([(40, 155), (width - 40, 155)], fill=(23, 54, 93), width=1)
    
    rows = [
        ("Cash and Cash Equivalents", "28.20", "25.00"),
        ("Accounts Receivable (Net)", "18.40", "16.50"),
        ("Inventories", "14.20", "12.40"),
        ("Total Current Assets", "64.40", "57.00"),
        ("Property, Plant & Equipment (Net)", "52.00", "41.00"),
        ("TOTAL ASSETS", "145.00", "120.00"),
        ("Accounts Payable", "18.20", "16.50"),
        ("Current Liabilities", "35.60", "32.00"),
        ("Total Debt (Borrowings)", "30.40", "24.40"),
        ("TOTAL LIABILITIES", "61.00", "52.00"),
        ("TOTAL STOCKHOLDERS' EQUITY", "84.00", "68.00"),
        ("TOTAL LIABILITIES AND EQUITY", "145.00", "120.00"),
    ]
    
    y = 175
    for item, fy23, fy22 in rows:
        is_bold = "TOTAL" in item
        color = (23, 54, 93) if is_bold else (40, 50, 70)
        draw.text((50, y), item, fill=color)
        draw.text((660, y), fy23, fill=color)
        draw.text((810, y), fy22, fill=color)
        
        y += 24
        draw.line([(40, y - 4), (width - 40, y - 4)], fill=(240, 243, 248), width=1)
        y += 14

    draw.text((40, height - 50), "Note: Audited under US GAAP by Independent Certified Public Accountants.", fill=(120, 130, 150))
    
    img.save(file_path, "PNG")
    print(f"Generated OCR Image: {file_path}")
    return file_path


# -------------------------------------------------------------------------- #
# 5. Structured JSON Data
# -------------------------------------------------------------------------- #
def generate_json_record():
    file_path = SAMPLE_INPUTS_DIR / "Apex_Technologies_Financial_Summary.json"
    data = {
        "company_name": "Apex Technologies Ltd.",
        "ticker": "APEX",
        "fiscal_year": 2023,
        "reporting_period": "FY2023",
        "currency": "USD",
        "scale": "Millions",
        "income_statement": {
            "revenue": 124.8,
            "cogs": 50.5,
            "gross_profit": 74.3,
            "operating_expenses": 51.2,
            "operating_profit": 23.1,
            "interest_expense": 1.5,
            "tax_expense": 4.54,
            "net_profit": 17.06
        },
        "balance_sheet": {
            "current_assets": 64.4,
            "cash_and_equivalents": 28.2,
            "inventory": 14.2,
            "accounts_receivable": 18.4,
            "current_liabilities": 35.6,
            "total_debt": 30.4,
            "total_liabilities": 61.0,
            "total_equity": 84.0,
            "total_assets": 145.0
        },
        "cash_flow": {
            "operating_cash_flow": 26.4,
            "capital_expenditures": -16.2,
            "free_cash_flow": 10.2
        },
        "ratios": {
            "gross_margin_pct": 59.54,
            "operating_margin_pct": 18.51,
            "net_margin_pct": 13.67,
            "current_ratio": 1.81,
            "quick_ratio": 1.31,
            "debt_to_equity": 0.36,
            "debt_ratio_pct": 42.07,
            "working_capital_millions": 28.8
        }
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Generated JSON: {file_path}")
    return file_path


# -------------------------------------------------------------------------- #
# 6. Copy PDF into sample_inputs as well
# -------------------------------------------------------------------------- #
def ensure_pdf_sample():
    src_pdf = BASE_DIR / "sample_financial_report.pdf"
    if not src_pdf.exists():
        src_pdf = SAMPLE_REPORTS_DIR / "Apex_Technologies_FY2023_Annual_Report.pdf"
    if src_pdf.exists():
        dest = SAMPLE_INPUTS_DIR / "Apex_Technologies_FY2023_Annual_Report.pdf"
        dest.write_bytes(src_pdf.read_bytes())
        print(f"Copied PDF: {dest}")


if __name__ == "__main__":
    print("Generating comprehensive multimodal sample inputs...")
    generate_excel_model()
    generate_csv_datasets()
    generate_txt_report()
    generate_ocr_image()
    generate_json_record()
    ensure_pdf_sample()
    print("All sample files successfully generated in 'sample_inputs/' folder!")
