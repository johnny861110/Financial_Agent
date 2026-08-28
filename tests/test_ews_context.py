"""Field-state, unit, and validation-aware tests for EarlyWarningService."""

import pytest

from app.core import DataLoader, InsufficientDataError
from app.data import CanonicalFact, FieldAvailability, UnitMismatchError, ValidationRecord
from app.services import EarlyWarningService
from tests.helpers import RecordProvider, make_record

CLEAN_SNAPSHOT = dict(
    net_revenue=1000.0,
    gross_profit=400.0,
    operating_income=200.0,
    net_income=150.0,
    total_assets=5000.0,
    total_liabilities=2000.0,  # debt ratio 40% is below the 70% critical threshold
    equity=3000.0,
    cash_and_equivalents=800.0,
    accounts_receivable=300.0,
    inventory=250.0,
    operating_cash_flow=150.0,  # positive, no cash-burn signal
)


def test_detect_warnings_uses_canonical_context_for_complete_data():
    record = make_record("2025Q1", snapshot_overrides=CLEAN_SNAPSHOT)
    service = EarlyWarningService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    result = service.detect_warnings("2330", "2025Q1")

    assert result is not None
    assert result.warning_level == "none"
    assert result.triggered_signals == []


def test_detect_warnings_raises_for_missing_required_field():
    record = make_record("2025Q1", snapshot_overrides={**CLEAN_SNAPSHOT, "total_liabilities": None})
    service = EarlyWarningService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(InsufficientDataError) as exc_info:
        service.detect_warnings("2330", "2025Q1")

    assert "total_liabilities" in exc_info.value.missing_fields


def test_detect_warnings_treats_not_applicable_as_unusable():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        field_availability=[
            FieldAvailability(
                field="total_liabilities",
                statement="balance_sheet",
                unit="TWD_thousands",
                state="not_applicable",
                reason="Bank-sector filing",
            )
        ],
    )
    service = EarlyWarningService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(InsufficientDataError) as exc_info:
        service.detect_warnings("2330", "2025Q1")

    assert "total_liabilities" in exc_info.value.missing_fields


def test_detect_warnings_raises_on_unit_mismatch():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        facts=[
            CanonicalFact(
                id=1,
                field="total_assets",
                value=5000.0,
                unit="USD_thousands",
                statement="balance_sheet",
                period_type="instant",
                source_type="xbrl",
                confidence=1.0,
            )
        ],
    )
    service = EarlyWarningService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    with pytest.raises(UnitMismatchError):
        service.detect_warnings("2330", "2025Q1")


def test_detect_warnings_surfaces_blocking_validation_failures_as_signals():
    record = make_record(
        "2025Q1",
        snapshot_overrides=CLEAN_SNAPSHOT,
        validation=[
            ValidationRecord(
                rule_name="balance_sheet_equation",
                passed=False,
                severity="error",
                message="total_assets does not balance",
            ),
            ValidationRecord(rule_name="revenue_positive", passed=True, severity="info"),
        ],
    )
    service = EarlyWarningService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    result = service.detect_warnings("2330", "2025Q1")

    assert result is not None
    assert any(
        signal.signal_name == "Data Validation Failure: balance_sheet_equation"
        and signal.description == "total_assets does not balance"
        for signal in result.triggered_signals
    )
