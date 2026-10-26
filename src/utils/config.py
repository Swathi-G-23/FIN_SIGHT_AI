"""
FIN SIGHT AI - Configuration Management
Loads and validates application configuration from environment variables.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# ------------------------------------------------------------------ #
# Base paths
# ------------------------------------------------------------------ #
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
INDEXES_DIR = DATA_DIR / "indexes"
UPLOADS_DIR = DATA_DIR / "uploads"

for _d in [DATA_DIR, REPORTS_DIR, INDEXES_DIR, UPLOADS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ #
# LLM Provider & Streamlit Cloud Secrets Fallback
# ------------------------------------------------------------------ #
def _get_setting(key: str, default: str = "") -> str:
    """Retrieve setting from environment variable with Streamlit secrets fallback."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default

LLM_PROVIDER = _get_setting("LLM_PROVIDER", "demo").lower()
LLM_MODEL = _get_setting("LLM_MODEL", "gemini-1.5-flash")

GOOGLE_API_KEY = _get_setting("GOOGLE_API_KEY", "")
OPENAI_API_KEY = _get_setting("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = _get_setting("ANTHROPIC_API_KEY", "")

# Determine if we have a real LLM available
def is_demo_mode() -> bool:
    """Return True when no real LLM API key is configured."""
    if LLM_PROVIDER == "demo":
        return True
    if LLM_PROVIDER == "gemini" and not GOOGLE_API_KEY:
        return True
    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        return True
    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        return True
    return False

DEMO_MODE = is_demo_mode()

# ------------------------------------------------------------------ #
# Document Processing
# ------------------------------------------------------------------ #
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# ------------------------------------------------------------------ #
# Retrieval
# ------------------------------------------------------------------ #
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# ------------------------------------------------------------------ #
# Logging
# ------------------------------------------------------------------ #
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ------------------------------------------------------------------ #
# AWS
# ------------------------------------------------------------------ #
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "fin-sight-ai-documents")

# ------------------------------------------------------------------ #
# Financial keywords used for metric extraction
# ------------------------------------------------------------------ #
FINANCIAL_KEYWORDS = {
    "revenue": [
        "total revenue", "net revenue", "revenue from operations",
        "total income", "gross revenue", "sales", "turnover",
        "net sales", "revenue",
    ],
    "net_profit": [
        "net profit", "profit after tax", "pat", "net income",
        "net earnings", "profit for the year", "net profit after tax",
        "profit attributable",
    ],
    "operating_profit": [
        "operating profit", "ebit", "profit from operations",
        "operating income", "ebitda",
    ],
    "total_assets": ["total assets", "assets total"],
    "total_liabilities": ["total liabilities", "liabilities total"],
    "total_equity": [
        "total equity", "shareholders equity", "stockholders equity",
        "net worth", "total net worth", "equity",
    ],
    "current_assets": ["current assets", "total current assets"],
    "current_liabilities": [
        "current liabilities", "total current liabilities",
    ],
    "total_debt": [
        "total debt", "long term debt", "long-term debt",
        "borrowings", "total borrowings",
    ],
    "operating_cash_flow": [
        "cash from operations", "operating cash flow",
        "net cash from operating activities",
        "cash generated from operations",
    ],
    "gross_profit": [
        "gross profit", "gross margin",
    ],
    "operating_expenses": [
        "operating expenses", "total operating expenses",
        "opex", "expenses",
    ],
}
