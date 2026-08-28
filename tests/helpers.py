"""Shared test helpers for canonical-context service tests."""

from typing import Any, Dict, List, Optional, Tuple

from app.data import FilingIdentityRecord, SnapshotRecord
from app.models import FinancialSnapshot


class RecordProvider:
    """Minimal FinancialDataProvider stub backed by an in-memory record map."""

    def __init__(self, records: Dict[Tuple[str, str], SnapshotRecord]) -> None:
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


def make_snapshot(
    period: str,
    *,
    stock_code: str = "2330",
    company_name: str = "TSMC",
    **overrides: Any,
) -> FinancialSnapshot:
    """Build a FinancialSnapshot with sensible complete defaults, override as needed."""
    defaults: Dict[str, Any] = dict(
        stock_code=stock_code,
        company_name=company_name,
        report_year=int(period[:4]),
        report_season=int(period[-1]),
        report_period=period,
        net_revenue=1000.0,
        gross_profit=400.0,
        operating_income=200.0,
        net_income=150.0,
        eps=2.0,
        total_assets=5000.0,
        total_liabilities=2000.0,
        equity=3000.0,
        cash_and_equivalents=800.0,
        accounts_receivable=300.0,
        inventory=250.0,
        operating_cash_flow=180.0,
    )
    defaults.update(overrides)
    return FinancialSnapshot(**defaults)


def make_record(
    period: str,
    *,
    stock_code: str = "2330",
    company_name: str = "TSMC",
    snapshot_overrides: Optional[Dict[str, Any]] = None,
    field_availability: Optional[List] = None,
    facts: Optional[List] = None,
    validation: Optional[List] = None,
    **record_overrides: Any,
) -> SnapshotRecord:
    """Build a SnapshotRecord with an identity and snapshot, override any field."""
    snapshot = make_snapshot(
        period, stock_code=stock_code, company_name=company_name, **(snapshot_overrides or {})
    )
    defaults: Dict[str, Any] = dict(
        schema_version="1.0.0",
        source="test",
        identity=FilingIdentityRecord(
            stock_code=stock_code,
            period=period,
            filing_key=f"{stock_code}_{period}",
            company_name=company_name,
        ),
        snapshot=snapshot,
        field_availability=field_availability or [],
        facts=facts or [],
        validation=validation or [],
    )
    defaults.update(record_overrides)
    return SnapshotRecord(**defaults)
