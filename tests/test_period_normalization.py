"""Tests for reporting-period parsing.

A period reaches FinancialReports as a URL segment and the producer answers
anything but YYYYQn with 422 invalid_period. These tests pin the shapes that
users, LLMs and the keyword classifier actually produce.
"""

import pytest

from app.agents.workflow import FinancialAgent
from app.core import extract_period, normalize_period, split_period


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026Q1", "2026Q1"),
        ("2026q1", "2026Q1"),
        ("2026Q01", "2026Q1"),
        ("2026-Q1", "2026Q1"),
        ("2026 Q1", "2026Q1"),
        ("2026/Q1", "2026Q1"),
        ("2026年Q1", "2026Q1"),
        ("26Q1", "2026Q1"),
        ("Q1 2026", "2026Q1"),
        ("２０２６Ｑ１", "2026Q1"),
        ("2026第一季", "2026Q1"),
        ("2026 第一季", "2026Q1"),
        ("2026年第一季", "2026Q1"),
        ("2026年第一季度", "2026Q1"),
        ("2026 第 1 季", "2026Q1"),
        ("2025年第四季", "2025Q4"),
        ("  2026Q2  ", "2026Q2"),
    ],
)
def test_normalize_period_accepts_the_shapes_users_produce(raw, expected):
    assert normalize_period(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "2026",  # a year is not a period; guessing a quarter would be worse
        "下季",
        "2026Q5",
        "2026Q0",
        "abc",
        "20261",
    ],
)
def test_normalize_period_rejects_non_periods(raw):
    assert normalize_period(raw) is None


def test_extract_period_finds_a_period_inside_free_text():
    assert extract_period("幫我彙總 3661 2026 第一季財報表現") == "2026Q1"
    assert extract_period("Compare 3661 with 2330 in 2025Q1") == "2025Q1"
    assert extract_period("How has revenue trended for 3661?") is None


def test_split_period_removes_the_period_so_a_year_is_not_read_as_a_ticker():
    period, remainder = split_period("幫我彙總 3661 2026 第一季財報表現")
    assert period == "2026Q1"
    assert "2026" not in remainder
    assert "3661" in remainder


def test_keyword_classification_does_not_mistake_the_year_for_a_peer_stock():
    """The original failure: "3661 2026 第一季" yielded peer_stocks ['3661', '2026']."""
    agent = FinancialAgent.__new__(FinancialAgent)
    _, entities = FinancialAgent._keyword_classification(agent, "幫我彙總 3661 2026 第一季財報表現")

    assert entities["period"] == "2026Q1"
    assert entities["stock_code"] == "3661"
    assert "peer_stocks" not in entities


def test_keyword_classification_still_finds_real_peers():
    agent = FinancialAgent.__new__(FinancialAgent)
    _, entities = FinancialAgent._keyword_classification(
        agent, "Compare 3661 with 2330 and 2454 in 2025Q1"
    )

    assert entities["period"] == "2025Q1"
    assert entities["peer_stocks"] == ["3661", "2330", "2454"]


def test_apply_entities_normalizes_an_llm_period():
    """An LLM asked for a period happily returns a bare year plus an invented field."""
    agent = FinancialAgent.__new__(FinancialAgent)
    state = {"period": "2025Q1", "stock_code": "3661", "entities": {}}
    llm_entities = {"stock_code": "3661", "period": "2026 第一季"}

    FinancialAgent._apply_entities(agent, state, llm_entities)

    assert state["period"] == "2026Q1"
    assert state["entities"]["period"] == "2026Q1"


def test_apply_entities_falls_back_to_the_keyword_period_when_the_llm_drops_the_quarter():
    agent = FinancialAgent.__new__(FinancialAgent)
    state = {"period": "2025Q1", "stock_code": "3661", "entities": {}}
    llm_entities = {"stock_code": "3661", "period": "2026", "financial_statement": "第一季財報"}
    _, keyword_entities = FinancialAgent._keyword_classification(
        agent, "幫我彙總 3661 2026 第一季財報表現"
    )

    FinancialAgent._apply_entities(agent, state, llm_entities, keyword_entities)

    assert state["period"] == "2026Q1"


def test_apply_entities_keeps_the_caller_period_when_nothing_parses():
    """An unusable period must not overwrite one the caller already supplied."""
    agent = FinancialAgent.__new__(FinancialAgent)
    state = {"period": "2025Q1", "stock_code": "3661", "entities": {}}

    FinancialAgent._apply_entities(agent, state, {"period": "sometime next year"})

    assert state["period"] == "2025Q1"
    assert state["entities"]["period_raw"] == "sometime next year"
    assert "period" not in state["entities"]
