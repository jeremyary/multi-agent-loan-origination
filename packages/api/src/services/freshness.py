# This project was developed with assistance from AI tools.
"""Document freshness validation.

Pure function that checks whether extracted date fields fall within
acceptable recency thresholds for each document type. Stale or future-dated
documents get a quality flag that surfaces in the completeness response.
"""

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Map doc_type -> (date field name to check, max age in days)
# Only doc types with time-sensitive date fields are listed.
_FRESHNESS_THRESHOLDS: dict[str, tuple[str, int]] = {
    "pay_stub": ("pay_period_end", 30),
    "bank_statement": ("statement_period_end", 60),
}

# Date formats to try when parsing extracted date strings
_DATE_FORMATS = [
    "%Y-%m-%d",  # 2026-01-15
    "%m/%d/%Y",  # 01/15/2026
    "%m-%d-%Y",  # 01-15-2026
    "%Y/%m/%d",  # 2026/01/15
    "%d/%m/%Y",  # 15/01/2026
    "%B %d, %Y",  # January 15, 2026
    "%b %d, %Y",  # Jan 15, 2026
]


def _parse_date(value: str) -> date | None:
    """Try multiple date formats to parse a string into a date."""
    from datetime import datetime

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def check_freshness(
    doc_type: str,
    extractions: list[dict],
    reference_date: date | None = None,
) -> str | None:
    """Check if a document's date fields are within freshness thresholds.

    Args:
        doc_type: The document type (e.g. "pay_stub", "bank_statement").
        extractions: List of extraction dicts with field_name/field_value.
        reference_date: Date to compare against (defaults to today).

    Returns:
        "wrong_period" if the document is stale, "future_date" if the date
        is in the future, or None if fresh / no threshold applies.
    """
    threshold = _FRESHNESS_THRESHOLDS.get(doc_type)
    if threshold is None:
        return None

    field_name, max_days = threshold
    ref = reference_date or date.today()

    # Find the date field in extractions
    date_value = None
    for ext in extractions:
        if ext.get("field_name", "").lower() == field_name:
            date_value = ext.get("field_value")
            break

    if date_value is None:
        return None

    parsed = _parse_date(str(date_value))
    if parsed is None:
        logger.warning(
            "Could not parse date '%s' from field '%s' on %s",
            date_value,
            field_name,
            doc_type,
        )
        return None

    if parsed > ref:
        return "future_date"

    age = ref - parsed
    if age > timedelta(days=max_days):
        return "wrong_period"

    return None
