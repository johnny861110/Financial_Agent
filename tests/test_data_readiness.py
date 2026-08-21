"""Tests for provider lifecycle and quality decisions."""

from typing import Any

from app.data.models import DataFreshness, DataQuality, SnapshotRecord
from app.data.readiness import DataReadinessService
from app.models import FinancialSnapshot


def _snapshot() -> FinancialSnapshot:
    return FinancialSnapshot(
        stock_code="2330",
        company_name="Test Company",
        report_year=2025,
        report_season=1,
        report_period="2025Q1",
    )


class StubProvider:
    def __init__(self, record: SnapshotRecord | None) -> None:
        self.record = record

    def load_record(self, stock_code: str, period: str) -> SnapshotRecord | None:
        return self.record

    def list_available_periods(self, stock_code: str) -> list[str]:
        return []

    def list_all_stocks(self) -> list[str]:
        return []

    def get_context(
        self, stock_code: str, period: str, question: str | None = None
    ) -> dict[str, Any] | None:
        return None

    def request_refresh(self, stock_code: str, period: str) -> dict[str, Any]:
        return {"job_id": "job-1"}

    def get_job(self, job_id: str) -> dict[str, Any]:
        return {"job_id": job_id, "status": "processing"}


def test_readiness_reports_missing_data():
    readiness = DataReadinessService(StubProvider(None)).check("2330", "2025Q1")
    assert readiness.status == "missing"
    assert readiness.available is False


def test_readiness_reports_low_quality():
    provider = StubProvider(
        SnapshotRecord(
            snapshot=_snapshot(),
            quality=DataQuality(score=0.4, missing_fields=["operating_cash_flow"]),
            source="financial_reports",
        )
    )
    readiness = DataReadinessService(provider, min_quality_score=0.6).check("2330", "2025Q1")
    assert readiness.status == "low_quality"
    assert readiness.available is True
    assert readiness.missing_fields == ["operating_cash_flow"]


def test_stale_data_remains_available():
    provider = StubProvider(
        SnapshotRecord(
            snapshot=_snapshot(),
            freshness=DataFreshness(is_stale=True),
            source="financial_reports",
        )
    )
    readiness = DataReadinessService(provider).check("2330", "2025Q1")
    assert readiness.status == "stale"
    assert readiness.available is True


def test_processing_record_exposes_job_id():
    provider = StubProvider(
        SnapshotRecord(
            status="processing",
            source="financial_reports",
            job_id="job-1",
        )
    )
    readiness = DataReadinessService(provider).check("2330", "2025Q1")
    assert readiness.status == "processing"
    assert readiness.job_id == "job-1"
