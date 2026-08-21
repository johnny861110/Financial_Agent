"""Models carried across financial data provider boundaries."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import FinancialSnapshot


class DataQuality(BaseModel):
    """Quality metadata reported by the source data system."""

    score: float | None = Field(default=None, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    validation_failures: list[dict[str, Any]] = Field(default_factory=list)


class DataFreshness(BaseModel):
    """Freshness metadata for a filing snapshot."""

    updated_at: datetime | None = None
    is_stale: bool = False


class EvidenceReference(BaseModel):
    """Reference to structured or document evidence for a financial fact."""

    field: str | None = None
    source_type: str
    page_number: int | None = None
    section_title: str | None = None
    excerpt: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class SnapshotRecord(BaseModel):
    """Snapshot plus source, quality, and lifecycle metadata."""

    schema_version: str = "1.0"
    status: str = "ready"
    snapshot: FinancialSnapshot | None = None
    quality: DataQuality = Field(default_factory=DataQuality)
    freshness: DataFreshness = Field(default_factory=DataFreshness)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    source: str
    job_id: str | None = None
