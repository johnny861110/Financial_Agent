"""Data readiness checks shared by APIs and agent workflows."""

from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.data.models import SnapshotRecord
from app.data.providers import (
    FinancialDataContractError,
    FinancialDataProvider,
    FinancialDataProviderUnavailable,
)


ReadinessStatus = Literal[
    "ready",
    "low_quality",
    "stale",
    "processing",
    "missing",
    "failed",
]


class DataReadiness(BaseModel):
    """Decision-ready view of source data state."""

    stock_code: str
    period: str
    status: ReadinessStatus
    available: bool
    quality_score: float | None = Field(default=None, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source: str | None = None
    job_id: str | None = None


class DataReadinessService:
    """Interpret provider records into stable application states."""

    def __init__(
        self,
        provider: FinancialDataProvider,
        min_quality_score: float | None = None,
    ) -> None:
        self.provider = provider
        self.min_quality_score = (
            get_settings().min_data_quality_score
            if min_quality_score is None
            else min_quality_score
        )

    def check(self, stock_code: str, period: str) -> DataReadiness:
        try:
            record = self.provider.load_record(stock_code, period)
        except (FinancialDataProviderUnavailable, FinancialDataContractError) as exc:
            return DataReadiness(
                stock_code=stock_code,
                period=period,
                status="failed",
                available=False,
                warnings=[str(exc)],
            )
        return self._from_record(stock_code, period, record)

    def _from_record(
        self, stock_code: str, period: str, record: SnapshotRecord | None
    ) -> DataReadiness:
        if record is None:
            return DataReadiness(
                stock_code=stock_code,
                period=period,
                status="missing",
                available=False,
            )
        if record.status == "processing" or record.snapshot is None:
            return DataReadiness(
                stock_code=stock_code,
                period=period,
                status="processing",
                available=False,
                source=record.source,
                job_id=record.job_id,
            )

        score = record.quality.score
        if record.freshness.is_stale:
            return DataReadiness(
                stock_code=stock_code,
                period=period,
                status="stale",
                available=True,
                quality_score=score,
                missing_fields=record.quality.missing_fields,
                source=record.source,
                warnings=["The latest available filing data is stale"],
            )
        if score is not None and score < self.min_quality_score:
            return DataReadiness(
                stock_code=stock_code,
                period=period,
                status="low_quality",
                available=True,
                quality_score=score,
                missing_fields=record.quality.missing_fields,
                source=record.source,
                warnings=[
                    f"Data quality {score:.2f} is below the required {self.min_quality_score:.2f}"
                ],
            )
        return DataReadiness(
            stock_code=stock_code,
            period=period,
            status="ready",
            available=True,
            quality_score=score,
            missing_fields=record.quality.missing_fields,
            source=record.source,
        )

    def request_refresh(self, stock_code: str, period: str) -> dict:
        return self.provider.request_refresh(stock_code, period)

    def get_job(self, job_id: str) -> dict:
        return self.provider.get_job(job_id)
