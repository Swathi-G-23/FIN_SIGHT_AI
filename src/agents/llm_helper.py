"""
FIN SIGHT AI - LLM Helper
Provides a single interface for LLM calls across providers.
Falls back gracefully to demo mode when no API key is configured.
"""
from typing import Optional

from src.utils.config import DEMO_MODE, LLM_PROVIDER, LLM_MODEL, GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_llm_instance = None


def get_llm():
    """Return a cached LangChain LLM instance or None in demo mode."""
    global _llm_instance

    if DEMO_MODE:
        return None

    if _llm_instance is not None:
        return _llm_instance

    try:
        if LLM_PROVIDER == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            _llm_instance = ChatGoogleGenerativeAI(
                model=LLM_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=0.1,
            )
        elif LLM_PROVIDER == "openai":
            from langchain_openai import ChatOpenAI
            _llm_instance = ChatOpenAI(
                model=LLM_MODEL,
                openai_api_key=OPENAI_API_KEY,
                temperature=0.1,
            )
        elif LLM_PROVIDER == "anthropic":
            from langchain_anthropic import ChatAnthropic
            _llm_instance = ChatAnthropic(
                model=LLM_MODEL,
                anthropic_api_key=ANTHROPIC_API_KEY,
                temperature=0.1,
            )
        else:
            logger.warning("Unknown LLM provider '%s'. Running in demo mode.", LLM_PROVIDER)
            return None

        logger.info("LLM initialised: provider=%s model=%s", LLM_PROVIDER, LLM_MODEL)
        return _llm_instance

    except Exception as exc:
        logger.error("Failed to initialise LLM: %s", exc)
        return None


def llm_call(prompt: str, system: str = "") -> str:
    """
    Make a single LLM call.

    Args:
        prompt: User message.
        system: Optional system message.

    Returns:
        LLM response text, or a demo-mode placeholder.
    """
    llm = get_llm()

    if llm is None:
        # Demo mode — return a structured placeholder
        return _demo_response(prompt)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        response = llm.invoke(messages)
        return response.content

    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return f"[LLM Error: {exc}]\n\n{_demo_response(prompt)}"


def _demo_response(prompt: str) -> str:
    """
    Generate an offline structured response based on rule-based analysis.
    """
    return (
        "### 📊 Financial Performance Intelligence\n\n"
        "The system has processed filing records, extracted reported line items, and computed analytical ratios. "
        "Review the compiled Financial Metrics, Python-verified Ratio Analysis, and Risk Findings for audited numerical evidence.\n\n"
        f"**Query Evaluated**: {prompt[:200]}"
    )
