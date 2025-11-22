"""Core utilities and helpers."""

from typing import List, Dict, Any
import statistics


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
