"""Tests for schema-aware deterministic financial contexts."""

import pytest

from app.core import DataLoader
from app.data import (
    CanonicalFact,
    CanonicalFinancialContext,
    FieldAvailability,
    FieldUnavailableError,
    FilingIdentityRecord,
    SnapshotRecord,
    UnitMismatchError,
    ValidationRecord,
)
from app.models import FinancialSnapshot
from app.services import SnapshotService, TrendService


class RecordProvider:
    def __init__(self, records: dict[tuple[str, str], SnapshotRecord]) -> None:
        self.records = records

    def load_record(self, stock_code: str, period: str) -> SnapshotRecord | None:
        return self.records.get((stock_code, period))

    def list_available_periods(self, stock_code: str) -> list[str]:
        return sorted(period for code, period in self.records if code == stock_code)

    def list_all_stocks(self) -> list[str]:
        return sorted({code for code, _ in self.records})

    def get_context(self, stock_code: str, period: str, question: str | None = None) -> dict | None:
        item = self.load_record(stock_code, period)
        return item.model_dump(mode="json") if item else None

    def request_refresh(self, stock_code: str, period: str) -> dict:
        raise NotImplementedError

    def get_job(self, job_id: str) -> dict:
        raise NotImplementedError

    def get_capabilities(self) -> dict:
        return {"schema_version": "1.0.0"}


def snapshot(period: str, *, gross_profit: float | None = 40.0) -> FinancialSnapshot:
    return FinancialSnapshot(
        stock_code="2330",
        company_name="TSMC",
        report_year=int(period[:4]),
        report_season=int(period[-1]),
        report_period=period,
        net_revenue=100.0,
        gross_profit=gross_profit,
        operating_income=20.0,
        net_income=10.0,
        eps=2.0,
        total_assets=200.0,
        total_liabilities=80.0,
        equity=120.0,
    )


def record(period: str, *, gross_profit: float | None = 40.0) -> SnapshotRecord:
    return SnapshotRecord(
        schema_version="1.0.0",
        source="test",
        identity=FilingIdentityRecord(
            stock_code="2330",
            period=period,
            filing_key=f"2330_{period}",
            company_name="TSMC",
        ),
        snapshot=snapshot(period, gross_profit=gross_profit),
    )


def test_context_preserves_absence_states_and_rejects_unit_mismatch():
    item = record("2025Q1")
    item.facts = [
        CanonicalFact(
            id=1,
            field="net_revenue",
            value=100.0,
            unit="TWD_thousands",
            statement="income_statement",
            period_type="duration",
            source_type="xbrl",
            confidence=1.0,
        )
    ]
    item.field_availability = [
        FieldAvailability(
            field="inventory",
            statement="balance_sheet",
            unit="TWD_thousands",
            state="not_applicable",
            reason="Bank-sector filing",
        )
    ]
    context = CanonicalFinancialContext(item)

    assert context.required_fact("net_revenue", "TWD_thousands").id == 1
    assert context.optional_value("inventory", "TWD_thousands") is None
    with pytest.raises(FieldUnavailableError) as unavailable:
        context.required_value("inventory", "TWD_thousands")
    assert unavailable.value.state == "not_applicable"
    with pytest.raises(UnitMismatchError):
        context.required_fact("net_revenue", "TWD")


def test_context_filters_validation_failures():
    item = record("2025Q1")
    item.validation = [
        ValidationRecord(
            rule_name="balance_sheet_equation",
            passed=False,
            severity="error",
            message="total_assets does not balance",
        ),
        ValidationRecord(rule_name="revenue_positive", passed=True, severity="info"),
    ]
    context = CanonicalFinancialContext(item)

    assert [failure.rule_name for failure in context.failed_validations(["total_assets"])] == [
        "balance_sheet_equation"
    ]


def test_snapshot_summary_uses_producer_metric_and_exposes_context():
    item = record("2025Q1")
    item.metrics = {"gross_margin": 0.55}
    item.field_availability = [
        FieldAvailability(
            field="gross_profit",
            statement="income_statement",
            unit="TWD_thousands",
            state="missing",
        )
    ]
    service = SnapshotService(DataLoader(RecordProvider({("2330", "2025Q1"): item})))

    summary = service.get_summary("2330", "2025Q1")

    assert summary is not None
    assert summary["income_statement"]["gross_profit"] is None
    assert summary["margins"]["gross_margin"] == 55.0
    assert summary["data_context"]["field_states"]["gross_profit"] == "missing"


def test_trend_does_not_invent_zero_for_missing_derived_metric():
    first = record("2024Q1", gross_profit=None)
    first.field_availability = [
        FieldAvailability(
            field="gross_profit",
            statement="income_statement",
            unit="TWD_thousands",
            state="missing",
        )
    ]
    second = record("2025Q1", gross_profit=50.0)
    loader = DataLoader(RecordProvider({("2330", "2024Q1"): first, ("2330", "2025Q1"): second}))

    analysis = TrendService(loader).analyze_trend("2330")

    assert analysis is not None
    gross_margin = next(
        metric for metric in analysis.metrics if metric.metric_name == "Gross Margin (%)"
    )
    assert gross_margin.periods == ["2025Q1"]
    assert gross_margin.values == [50.0]
