"""
FIN SIGHT AI - Text Cleaner
Cleans and normalises extracted PDF text while preserving financial content.
"""
import re
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Patterns that rarely carry useful information for financial analysis
_NOISE_PATTERNS = [
    r"\x00",            # null bytes
    r"[\uf000-\uf0ff]", # Windows font glyphs (Private Use Area)
    r"[\u200b-\u200f]", # zero-width spaces
    r"\r",              # carriage returns (keep \n)
]

_COMPILED_NOISE = re.compile("|".join(_NOISE_PATTERNS))


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text.

    Steps:
    1. Remove null bytes and artefact characters.
    2. Normalise whitespace (collapse multiple spaces/tabs).
    3. Collapse more than two consecutive blank lines to two.
    4. Strip leading/trailing whitespace per line.
    5. Preserve page markers (--- PAGE N ---).
    """
    if not text:
        return ""

    # Step 1 – remove noise characters
    text = _COMPILED_NOISE.sub("", text)

    # Step 2 – normalise tabs and spaces (but not newlines)
    text = re.sub(r"[ \t]+", " ", text)

    # Step 3 – strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]

    # Step 4 – collapse runs of empty lines
    cleaned_lines = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    # Step 5 – rejoin and strip overall
    cleaned = "\n".join(cleaned_lines).strip()

    logger.debug("Text cleaned: %d -> %d chars", len(text), len(cleaned))
    return cleaned


def clean_financial_value(value_str: str) -> str:
    """
    Normalise a raw financial value string.
    Removes currency symbols, commas, and extra spaces but keeps
    minus signs and decimal points.

    Example: "₹ 1,23,456.78 Cr" → "123456.78 Cr"
    """
    # Remove currency symbols
    value_str = re.sub(r"[₹$€£¥]", "", value_str)
    # Remove commas used as thousands separators
    value_str = re.sub(r"(\d),(\d)", r"\1\2", value_str)
    # Collapse spaces
    value_str = re.sub(r"\s+", " ", value_str).strip()
    return value_str


def normalize_number(value_str: str) -> float | None:
    """
    Parse a financial number string to a float.
    Returns None if parsing fails.
    Handles: negative parentheses like (1234), minus sign, commas.
    """
    if not value_str:
        return None

    s = value_str.strip()

    # (1234) → -1234
    paren_match = re.fullmatch(r"\(([0-9,\.]+)\)", s)
    if paren_match:
        s = "-" + paren_match.group(1)

    # Remove commas
    s = s.replace(",", "")

    # Remove trailing % or currency units
    s = re.sub(r"[%₹$€£¥]", "", s).strip()

    try:
        return float(s)
    except (ValueError, TypeError):
        return None
