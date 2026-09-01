"""Core utilities and helpers."""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
import re
import statistics
import unicodedata

if TYPE_CHECKING:
    from app.data.context import CanonicalFinancialContext


class InsufficientDataError(ValueError):
    """Raised when a financial calculation cannot run because required fields are missing."""

    def __init__(self, message: str, missing_fields: Optional[List[str]] = None):
        super().__init__(message)
        self.missing_fields = missing_fields or []


def missing_fields(record: object, fields: List[str]) -> List[str]:
    """Return required field names whose value is None."""
    return [field for field in fields if getattr(record, field, None) is None]


def require_fields(record: object, fields: List[str], context: str) -> None:
    """Raise a structured error if any required fields are missing."""
    missing = missing_fields(record, fields)
    if missing:
        raise InsufficientDataError(
            f"Insufficient data for {context}: missing {', '.join(missing)}",
            missing,
        )


def required_float(record: object, field: str, context: str) -> float:
    """Return a required numeric field as float after validating it is present."""
    require_fields(record, [field], context)
    value = getattr(record, field)
    return float(value)


def required_context_values(
    context: "CanonicalFinancialContext",
    fields: List[str],
    expected_unit: str,
    activity: str,
) -> Dict[str, float]:
    """
    Validate that canonical fields are usable (present, correct unit) on a
    CanonicalFinancialContext, raising the same InsufficientDataError contract
    as require_fields for missing/null/not_applicable/provider_failure states.
    """
    values: Dict[str, float] = {}
    missing: List[str] = []
    for field in fields:
        value = context.optional_value(field, expected_unit)
        if value is None:
            missing.append(field)
        else:
            values[field] = value
    if missing:
        raise InsufficientDataError(
            f"Insufficient data for {activity}: missing {', '.join(missing)}",
            missing,
        )
    return values


def calculate_z_score(value: float, mean: float, std_dev: float) -> float:
    """
    Calculate z-score for factor exposure.

    Args:
        value: Raw value
        mean: Population mean
        std_dev: Population standard deviation

    Returns:
        Z-score
    """
    if std_dev == 0:
        return 0.0
    return (value - mean) / std_dev


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default return value if division by zero

    Returns:
        Division result or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_growth_rate(current: float, previous: float) -> float:
    """
    Calculate growth rate as percentage.

    Args:
        current: Current period value
        previous: Previous period value

    Returns:
        Growth rate as percentage
    """
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    """
    Normalize a value to 0-100 scale.

    Args:
        value: Value to normalize
        min_val: Minimum expected value
        max_val: Maximum expected value

    Returns:
        Normalized score (0-100)
    """
    if max_val == min_val:
        return 50.0

    normalized = ((value - min_val) / (max_val - min_val)) * 100
    return max(0.0, min(100.0, normalized))


def calculate_volatility(values: List[float]) -> float:
    """
    Calculate coefficient of variation (volatility measure).

    Args:
        values: List of numeric values

    Returns:
        Coefficient of variation (std_dev / mean)
    """
    if len(values) < 2:
        return 0.0

    mean = statistics.mean(values)
    if mean == 0:
        return 0.0

    std_dev = statistics.stdev(values)
    return std_dev / mean


def format_large_number(value: float, unit: str = "thousand") -> str:
    """
    Format large numbers for display.

    Args:
        value: Numeric value
        unit: Unit of the value (thousand, million, billion)

    Returns:
        Formatted string
    """
    multipliers = {
        "thousand": 1_000,
        "million": 1_000_000,
        "billion": 1_000_000_000,
    }

    multiplier = multipliers.get(unit.lower(), 1)
    actual_value = value * multiplier

    if actual_value >= 1_000_000_000:
        return f"{actual_value / 1_000_000_000:.2f}B"
    elif actual_value >= 1_000_000:
        return f"{actual_value / 1_000_000:.2f}M"
    elif actual_value >= 1_000:
        return f"{actual_value / 1_000:.2f}K"
    else:
        return f"{actual_value:.2f}"


def interpret_score(score: float) -> str:
    """
    Interpret a 0-100 score into qualitative categories.

    Args:
        score: Score value (0-100)

    Returns:
        Qualitative interpretation
    """
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    elif score >= 20:
        return "Poor"
    else:
        return "Critical"


# ---------------------------------------------------------------------------
# Reporting period parsing
#
# The FinancialReports v1 API rejects anything but YYYYQn, so a period has to be
# normalized before it reaches a provider. Free-text queries arrive in several
# shapes -- "2026Q1", "2026 第一季", "26Q1" -- and an LLM asked for a period will
# happily return a bare year.
# ---------------------------------------------------------------------------

_QUARTER_DIGITS = {
    "一": "1",
    "壹": "1",
    "二": "2",
    "貳": "2",
    "兩": "2",
    "三": "3",
    "參": "3",
    "叁": "3",
    "四": "4",
    "肆": "4",
}

# Ordered by specificity: the Chinese quarter form has to win over the bare
# "YYYYQn" form for inputs that contain both a year and a quarter word.
_PERIOD_PATTERNS = (
    re.compile(r"(?P<year>\d{4}|\d{2})\s*年?\s*第\s*(?P<quarter>[一二三四壹貳兩參叁肆1-4])\s*季(?:度)?"),
    re.compile(r"(?P<year>\d{4}|\d{2})\s*[-/年.]?\s*[Qq]\s*0?(?P<quarter>[1-4])(?!\d)"),
    re.compile(r"[Qq]\s*0?(?P<quarter>[1-4])\s*[-/, ]\s*(?P<year>\d{4})(?!\d)"),
)


def _build_period(year: str, quarter: str) -> str:
    """Assemble a YYYYQn label from a matched year and quarter fragment."""
    quarter = _QUARTER_DIGITS.get(quarter, quarter)
    if len(year) == 2:
        year = f"20{year}"
    return f"{year}Q{quarter}"


def normalize_period(raw: Optional[str]) -> Optional[str]:
    """
    Normalize a single reporting-period token to the canonical ``YYYYQn`` form.

    Accepts the shapes users and LLMs actually produce -- ``2026Q1``, ``2026q1``,
    ``2026-Q1``, ``26Q1``, ``2026Q01``, ``2026年第一季``, ``Q1 2026``.

    A bare year is deliberately *not* resolved: guessing a quarter is worse than
    reporting that the period is unusable.

    Args:
        raw: Period token to normalize

    Returns:
        Canonical ``YYYYQn`` string, or None if the token is not a period
    """
    if not raw:
        return None

    # NFKC folds full-width digits and letters ("２０２６Ｑ１") to ASCII.
    candidate = unicodedata.normalize("NFKC", str(raw)).strip()
    if not candidate:
        return None

    for pattern in _PERIOD_PATTERNS:
        match = pattern.fullmatch(candidate)
        if match:
            return _build_period(match.group("year"), match.group("quarter"))
    return None


def extract_period(text: Optional[str]) -> Optional[str]:
    """
    Find the first reporting period inside free text.

    Unlike :func:`normalize_period` this searches rather than matching the whole
    string, so it can pull "2026Q1" out of "幫我彙總 3661 2026 第一季財報表現".

    Args:
        text: Free-form query text

    Returns:
        Canonical ``YYYYQn`` string, or None if the text names no period
    """
    if not text:
        return None

    candidate = unicodedata.normalize("NFKC", str(text))
    for pattern in _PERIOD_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return _build_period(match.group("year"), match.group("quarter"))
    return None


def split_period(text: Optional[str]) -> Tuple[Optional[str], str]:
    """
    Split free text into the period it names and everything else.

    Callers that also scan the text for stock codes need the remainder rather
    than offsets: a year such as "2026" is indistinguishable from a four-digit
    ticker, so the period fragment has to be removed before the ticker scan.

    Args:
        text: Free-form query text

    Returns:
        ``(period, remainder)`` where period is canonical ``YYYYQn`` or None, and
        remainder is the NFKC-normalized text with the period fragment removed
    """
    if not text:
        return None, ""

    candidate = unicodedata.normalize("NFKC", str(text))
    for pattern in _PERIOD_PATTERNS:
        match = pattern.search(candidate)
        if match:
            period = _build_period(match.group("year"), match.group("quarter"))
            return period, candidate[: match.start()] + " " + candidate[match.end() :]
    return None, candidate
