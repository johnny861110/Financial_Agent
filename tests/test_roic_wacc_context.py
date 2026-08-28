"""Field-state, unit, and validation-aware tests for ROICWACCService."""

import pytest

from app.core import DataLoader, InsufficientDataError
from app.data import CanonicalFact, FieldAvailability, UnitMismatchError, ValidationRecord
from app.services import ROICWACCService
from tests.helpers import RecordProvider, make_record

CLEAN_SNAPSHOT = dict(
    operating_income=200.0,
    equity=3000.0,
    total_liabilities=2000.0,
    total_assets=5000.0,
)


def test_analyze_uses_canonical_context_for_complete_data():
    record = make_record("2025Q1", snapshot_overrides=CLEAN_SNAPSHOT)
    service = ROICWACCService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    analysis = service.analyze("2330", "2025Q1")

    assert analysis is not None
    assert analysis.nopat == pytest.approx(160.0)
    assert analysis.invested_capital == pytest.approx(5000.0)
    assert analysis.roic == pytest.approx(3.2)
    assert analysis.cost_of_equity == pytest.approx(8.0)
    assert analysis.cost_of_debt == pytest.approx(4.0)
    assert analysis.wacc == pytest.approx(6.4)
    assert "Value destruction" in analysis.commentary


def test_analyze_raises_for_missing_required_field():
    record = make_record("2025Q1", snapshot_overrides={**CLEAN_SNAPSHOT, "equity": None})
    service = ROICWACCService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(InsufficientDataError) as exc_info:
        service.analyze("2330", "2025Q1")

    assert "equity" in exc_info.value.missing_fields


def test_analyze_treats_not_applicable_as_unusable():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        field_availability=[
            FieldAvailability(
                field="equity",
                statement="balance_sheet",
                unit="TWD_thousands",
                state="not_applicable",
                reason="Non-standard filing",
            )
        ],
    )
    service = ROICWACCService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(InsufficientDataError) as exc_info:
        service.analyze("2330", "2025Q1")

    assert "equity" in exc_info.value.missing_fields


def test_analyze_raises_on_unit_mismatch():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        facts=[
            CanonicalFact(
                id=1,
                field="operating_income",
                value=200.0,
                unit="USD_thousands",
                statement="income_statement",
                period_type="duration",
                source_type="xbrl",
                confidence=1.0,
            )
        ],
    )
    service = ROICWACCService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(UnitMismatchError):
        service.analyze("2330", "2025Q1")


def test_analyze_surfaces_blocking_validation_failures_in_commentary():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        validation=[
            ValidationRecord(
                rule_name="equity_reconciliation",
                passed=False,
                severity="error",
                message="equity failed reconciliation check",
            ),
            ValidationRecord(rule_name="revenue_positive", passed=True, severity="info"),
        ],
    )
    service = ROICWACCService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    analysis = service.analyze("2330", "2025Q1")

    assert analysis is not None
    assert "equity failed reconciliation check" in analysis.commentary


def test_analyze_skips_leverage_heuristic_when_total_assets_unavailable():
    """total_assets is not a required field; missing it must not fabricate a 0% debt ratio."""
    record = make_record("2025Q1", snapshot_overrides={**CLEAN_SNAPSHOT, "total_assets": None})
    service = ROICWACCService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    analysis = service.analyze("2330", "2025Q1")

    assert analysis is not None
    # cost_of_debt falls back to the base rate alone: 3% pretax * (1 - 20% tax) = 2.4%
    assert analysis.cost_of_debt == pytest.approx(2.4)
    assert "Conservative capital structure" not in analysis.commentary
    assert "High leverage" not in analysis.commentary
