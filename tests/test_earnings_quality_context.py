"""Field-state, unit, and validation-aware tests for EarningsQualityService."""

import pytest

from app.core import DataLoader, InsufficientDataError
from app.data import CanonicalFact, FieldAvailability, UnitMismatchError, ValidationRecord
from app.services import EarningsQualityService
from tests.helpers import RecordProvider, make_record

CLEAN_SNAPSHOT = dict(
    net_revenue=1000.0,
    gross_profit=400.0,
    operating_income=200.0,
    net_income=190.0,
    total_assets=5000.0,
    total_liabilities=2000.0,
    equity=3000.0,
    cash_and_equivalents=800.0,
    accounts_receivable=300.0,
    inventory=250.0,
    operating_cash_flow=195.0,
)


def test_calculate_score_uses_canonical_context_for_complete_data():
    periods = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1"]
    records = {
        ("2330", period): make_record(period, snapshot_overrides=CLEAN_SNAPSHOT)
        for period in periods
    }
    service = EarningsQualityService(DataLoader(RecordProvider(records)))

    score = service.calculate_score("2330", "2025Q1")

    assert score is not None
    assert score.accrual_quality == 100.0
    assert score.working_capital_behavior == 100.0
    assert score.one_off_dependency == 100.0
    assert score.earnings_stability == 100.0
    assert score.red_flags == []
    assert score.details["num_red_flags"] == 0


def test_calculate_score_raises_for_missing_required_field():
    record = make_record("2025Q1", snapshot_overrides={**CLEAN_SNAPSHOT, "inventory": None})
    service = EarningsQualityService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(InsufficientDataError) as exc_info:
        service.calculate_score("2330", "2025Q1")

    assert "inventory" in exc_info.value.missing_fields


def test_calculate_score_treats_not_applicable_as_unusable():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        field_availability=[
            FieldAvailability(
                field="inventory",
                statement="balance_sheet",
                unit="TWD_thousands",
                state="not_applicable",
                reason="Bank-sector filing",
            )
        ],
    )
    service = EarningsQualityService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(InsufficientDataError) as exc_info:
        service.calculate_score("2330", "2025Q1")

    assert "inventory" in exc_info.value.missing_fields


def test_calculate_score_raises_on_unit_mismatch():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        facts=[
            CanonicalFact(
                id=1,
                field="net_income",
                value=190.0,
                unit="USD_thousands",
                statement="income_statement",
                period_type="duration",
                source_type="xbrl",
                confidence=1.0,
            )
        ],
    )
    service = EarningsQualityService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(UnitMismatchError):
        service.calculate_score("2330", "2025Q1")


def test_calculate_score_surfaces_blocking_validation_failures_as_red_flags():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        validation=[
            ValidationRecord(
                rule_name="net_income_reconciliation",
                passed=False,
                severity="error",
                message="net_income failed reconciliation check",
            ),
            ValidationRecord(rule_name="revenue_positive", passed=True, severity="info"),
        ],
    )
    service = EarningsQualityService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    score = service.calculate_score("2330", "2025Q1")

    assert score is not None
    assert any("net_income failed reconciliation check" in flag for flag in score.red_flags)
