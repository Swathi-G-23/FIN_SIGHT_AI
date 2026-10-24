"""
FIN SIGHT AI - Main Application Entry Point
Configures enterprise light theme, shared multimodal session state,
and automatically navigates to the primary starting page: 1_Upload_Report.py
"""
import streamlit as st

# Page configuration — must be the FIRST Streamlit call
st.set_page_config(
    page_title="FIN SIGHT AI — Financial Intelligence Platform",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Enterprise Light Theme
from src.ui.theme import apply_light_theme, render_sidebar_brand
apply_light_theme()

# ------------------------------------------------------------------ #
# Session State Initialisation
# ------------------------------------------------------------------ #
if "document_session" not in st.session_state:
    st.session_state.document_session = None

if "all_records" not in st.session_state:
    st.session_state.all_records = []

if "selected_company" not in st.session_state:
    st.session_state.selected_company = None

if "selected_period" not in st.session_state:
    st.session_state.selected_period = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_workflow_state" not in st.session_state:
    st.session_state.last_workflow_state = None

if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}

# Direct user immediately to the starting Ingestion Portal page
st.switch_page("pages/1_Upload_Report.py")
