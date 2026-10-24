"""
FIN SIGHT AI - Financial Metric Extraction
Extracts financial values from document text using regex patterns and keyword matching.
"""
import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from src.utils.config import FINANCIAL_KEYWORDS
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Unit multipliers (to normalise to base currency unit)
UNIT_MULTIPLIERS = {
    "crore": 1e7,
    "cr": 1e7,
    "lakh": 1e5,
    "lac": 1e5,
    "million": 1e6,
    "mn": 1e6,
    "billion": 1e9,
    "bn": 1e9,
    "thousand": 1e3,
    "k": 1e3,
    "lakhs": 1e5,
    "crores": 1e7,
    "millions": 1e6,
    "billions": 1e9,
}


@dataclass
class ExtractedMetric:
    """A single extracted financial metric."""
    metric_key: str
    metric_label: str          # Label as found in the document
    raw_value: str             # Original string from document
    numeric_value: Optional[float]
    unit: str = ""             # e.g. "crore", "million"
    unit_multiplier: float = 1.0
    normalized_value: Optional[float] = None  # numeric_value * multiplier
    period: str = ""           # Reporting period if detectable
    page_number: int = 0
    confidence: str = "medium" # "high", "medium", "low"
    is_extracted: bool = True  # True = from doc, False = calculated
    source_text: str = ""      # Snippet of source text for tracing


def _parse_number(s: str) -> Optional[float]:
    """Parse a numeric string, handling parentheses for negatives and commas."""
    s = s.strip()
    negative = False

    # Parentheses → negative
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
        negative = True

    # Remove commas and whitespace
    s = re.sub(r"[,\s]", "", s)

    # Handle trailing minus
    if s.endswith("-"):
        s = "-" + s[:-1]
        negative = False

    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def _detect_unit(context: str) -> tuple[str, float]:
    """Detect financial unit from surrounding context."""
    ctx_lower = context.lower()
    for unit, mult in UNIT_MULTIPLIERS.items():
        if unit in ctx_lower:
            return unit, mult
    return "", 1.0


def _detect_period(context: str) -> str:
    """Try to detect the reporting period (year) near a value."""
    # Match patterns like FY2023, FY 2023, 2022-23, 2023
    patterns = [
        r"FY\s*(\d{4})",
        r"(\d{4}[-–]\d{2,4})",
        r"year\s+ended\s+\w+\s+(\d{4})",
        r"(\d{4})",
    ]
    for p in patterns:
        m = re.search(p, context, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


# Number pattern: handles commas, decimals, negatives/parentheses
_NUM_RE = re.compile(
    r"[\(\-]?\s*[\d,]+(?:\.\d+)?\s*\)?"
)

_FULL_NUM_PATTERN = re.compile(
    r"[\(\-]?\s*[\d,]+(?:\.\d+)?\s*(?:crore|cr|lakh|lac|million|mn|billion|bn|thousand|lakhs|crores|millions|billions)?\s*\)?"
    ,re.IGNORECASE,
)


def extract_financial_metrics(
    pages: List[Any],  # List[PageContent]
) -> Dict[str, List[ExtractedMetric]]:
    """
    Extract financial metrics from document pages.

    Args:
        pages: List of PageContent objects.

    Returns:
        Dict mapping metric_key → list of ExtractedMetric (may have multiple periods).
    """
    start = time.time()
    results: Dict[str, List[ExtractedMetric]] = {k: [] for k in FINANCIAL_KEYWORDS}

    for page in pages:
        text = page.text
        if not text.strip():
            continue

        lines = text.split("\n")
        for line_idx, line in enumerate(lines):
            line_lower = line.lower()

            for metric_key, keywords in FINANCIAL_KEYWORDS.items():
                for keyword in keywords:
                    if keyword not in line_lower:
                        continue

                    # Found a keyword match — look for numbers on this line
                    # and the next 2 lines
                    context_lines = lines[line_idx: line_idx + 3]
                    context = " ".join(context_lines)

                    numbers = _FULL_NUM_PATTERN.findall(context)
                    if not numbers:
                        continue

                    unit, mult = _detect_unit(context)
                    period = _detect_period(context)

                    for raw_val in numbers[:2]:  # take up to 2 values (e.g., current & prior year)
                        raw_val = raw_val.strip()
                        # Strip unit name from the value for parsing
                        val_clean = re.sub(
                            r"(?i)(crore|cr|lakh|lac|million|mn|billion|bn|thousand|lakhs|crores|millions|billions)",
                            "", raw_val
                        ).strip()
                        numeric = _parse_number(val_clean)
                        if numeric is None:
                            continue

                        normalized = numeric * mult if mult != 1.0 else numeric

                        metric = ExtractedMetric(
                            metric_key=metric_key,
                            metric_label=keyword.title(),
                            raw_value=raw_val,
                            numeric_value=numeric,
                            unit=unit,
                            unit_multiplier=mult,
                            normalized_value=normalized,
                            period=period,
                            page_number=page.page_number,
                            confidence="high" if keyword == line_lower.strip() else "medium",
                            is_extracted=True,
                            source_text=line[:200],
                        )
                        # De-duplicate: don't add the same (value, period) twice
                        existing = results[metric_key]
                        duplicate = any(
                            abs((m.numeric_value or 0) - (metric.numeric_value or 0)) < 0.01
                            and m.period == metric.period
                            for m in existing
                        )
                        if not duplicate:
                            results[metric_key].append(metric)

    elapsed = time.time() - start
    found = {k: v for k, v in results.items() if v}
    logger.info(
        "Metric extraction: %d metric types found, %.2fs",
        len(found), elapsed,
    )
    return results


def get_best_metric(
    metrics: Dict[str, List[ExtractedMetric]],
    key: str,
    period: str = "",
) -> Optional[ExtractedMetric]:
    """
    Return the best (most confident) metric for a given key and optional period.
    """
    candidates = metrics.get(key, [])
    if not candidates:
        return None

    if period:
        period_candidates = [m for m in candidates if m.period == period]
        if period_candidates:
            candidates = period_candidates

    # Sort by confidence score
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    candidates = sorted(candidates, key=lambda m: confidence_order.get(m.confidence, 3))
    return candidates[0]


def metrics_summary(metrics: Dict[str, List[ExtractedMetric]]) -> Dict[str, Any]:
    """
    Build a flat summary dict of best-available metrics.
    """
    summary = {}
    for key in FINANCIAL_KEYWORDS:
        best = get_best_metric(metrics, key)
        if best:
            summary[key] = {
                "value": best.numeric_value,
                "unit": best.unit,
                "period": best.period,
                "page": best.page_number,
                "raw": best.raw_value,
                "normalized": best.normalized_value,
            }
    return summary
