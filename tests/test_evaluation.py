"""Gate the evaluation metrics in CI.

The evaluation set answers a question the unit tests cannot: does the system as
a whole still behave acceptably across the range of filing states it will meet?
Thresholds here are the floor, not the target -- a drop below them means a
regression in behaviour that individual unit tests did not catch.
"""

from __future__ import annotations

import pytest

from evaluation.metrics import evaluate, verdict_stability
from evaluation.scenarios import all_scenarios, by_name


@pytest.fixture(scope="module")
def report():
    return evaluate()


def test_every_filing_state_is_covered():
    """The set must keep spanning the states the system actually meets."""
    names = {scenario.name for scenario in all_scenarios()}

    assert names == {
        "complete",
        "partial",
        "not_applicable",
        "stale",
        "invalid",
        "processing",
        "absent",
        "narrative",
        "contradiction",
    }


def test_tool_gating_is_exact(report):
    """Gating is deterministic, so anything below perfect is a real defect."""
    assert report.gating_accuracy == 1.0, (
        "a tool ran that should have been blocked, or was blocked when it " "should have run"
    )


def test_narrative_answers_are_cited(report):
    assert report.citation_coverage == 1.0


def test_planted_contradictions_are_found(report):
    assert report.contradiction_recall == 1.0


def test_absent_and_processing_filings_assert_nothing(report):
    """No data must mean no findings and no confidence, never a guess."""
    for name in ("absent", "processing"):
        result = next(r for r in report.results if r.scenario == name)
        assert result.findings == 0, f"{name} produced findings from no data"
        assert result.confidence == 0.0
        assert result.verdict == "資料不足"


def test_degraded_data_lowers_confidence(report):
    """A filing failing validation must not read as confidently as a clean one."""
    clean = next(r for r in report.results if r.scenario == "complete")
    invalid = next(r for r in report.results if r.scenario == "invalid")

    assert invalid.confidence < clean.confidence
    assert invalid.confidence > 0, "degraded is not the same as impossible"


def test_a_missing_field_blocks_only_what_needs_it(report):
    """The precision the canonical-context work exists to provide."""
    partial = next(r for r in report.results if r.scenario == "partial")

    assert "ews" in partial.blocked
    assert {"snapshot", "roic_wacc", "earnings_quality"} <= partial.ran


def test_verdicts_are_reproducible():
    """The deterministic path must actually be deterministic."""
    assert verdict_stability(by_name("complete"))
    assert verdict_stability(by_name("invalid"))
