"""Models carried across financial data provider boundaries."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models import FinancialSnapshot


class DataQuality(BaseModel):
    """Quality metadata reported by the source data system."""

    score: float | None = Field(default=None, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    validation_failures: list[dict[str, Any]] = Field(default_factory=list)
    state: str | None = None
    validation_total: int = Field(default=0, ge=0)
    validation_failed: int = Field(default=0, ge=0)
    structured_source_coverage: float | None = Field(default=None, ge=0, le=1)


class DataFreshness(BaseModel):
    """Freshness metadata for a filing snapshot."""

    updated_at: datetime | None = None
    is_stale: bool = False
    state: str | None = None
    latest_source_at: datetime | None = None
    stale_after_seconds: int | None = Field(default=None, ge=0)


class EvidenceReference(BaseModel):
    """Reference to structured or document evidence for a financial fact."""

    field: str | None = None
    source_type: str
    page_number: int | None = None
    section_title: str | None = None
    excerpt: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    fact_id: int | None = None
    source_document_id: int | None = None
    doc_id: int | None = None
    raw_text: str | None = None
    extraction_method: str | None = None
    source_url: str | None = None
    checksum: str | None = None


DataState = Literal["present", "missing", "null", "not_applicable", "provider_failure"]


class FilingIdentityRecord(BaseModel):
    """Stable filing identity supplied by FinancialReports."""

    stock_code: str
    period: str
    filing_key: str
    company_name: str
    company_name_zh: str | None = None
    company_name_en: str | None = None
    industry: str | None = None
    market: str | None = None


class CanonicalFact(BaseModel):
    """Canonical fact with provenance preserved from FinancialReports."""

    id: int
    field: str
    value: float
    unit: str
    statement: str
    period_start: str | None = None
    period_end: str | None = None
    period_type: Literal["duration", "instant"]
    source_type: str
    confidence: float = Field(ge=0, le=1)
    xbrl_tag: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class FieldAvailability(BaseModel):
    field: str
    statement: str
    unit: str
    state: DataState
    reason: str | None = None


class MetricRecord(BaseModel):
    name: str
    value: float
    unit: str
    formula: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)


class ValidationRecord(BaseModel):
    rule_name: str
    passed: bool
    severity: str
    message: str | None = None
    checked_at: datetime | None = None


class ComparisonRecord(BaseModel):
    field: str
    compare_type: Literal["yoy", "qoq"]
    compare_period: str | None = None
    current_value: float
    prior_value: float
    change_abs: float | None = None
    change_pct: float | None = None
    direction: Literal["up", "down", "flat"] | None = None
    significance: Literal["large", "moderate", "small"] | None = None
    interpretation: str | None = None


class InsightCardRecord(BaseModel):
    id: int
    card_type: str
    title: str
    summary: str
    data_points: dict[str, Any] = Field(default_factory=dict)
    sentiment: Literal["positive", "negative", "neutral"] | None = None
    confidence: float = Field(ge=0, le=1)
    generated_at: datetime | None = None


class SourceDocumentRecord(BaseModel):
    id: int
    doc_type: str
    url: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    checksum: str | None = None
    downloaded_at: datetime | None = None
    parse_status: str


class PipelineRunRecord(BaseModel):
    stage: str
    status: Literal["started", "completed", "failed", "skipped"]
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None


class SnapshotRecord(BaseModel):
    """Snapshot plus source, quality, and lifecycle metadata."""

    schema_version: str = "1.0"
    status: str = "ready"
    pipeline_status: str | None = None
    identity: FilingIdentityRecord | None = None
    snapshot: FinancialSnapshot | None = None
    quality: DataQuality = Field(default_factory=DataQuality)
    freshness: DataFreshness = Field(default_factory=DataFreshness)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    metric_records: list[MetricRecord] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    facts: list[CanonicalFact] = Field(default_factory=list)
    field_availability: list[FieldAvailability] = Field(default_factory=list)
    validation: list[ValidationRecord] = Field(default_factory=list)
    comparisons: list[ComparisonRecord] = Field(default_factory=list)
    insight_cards: list[InsightCardRecord] = Field(default_factory=list)
    source_documents: list[SourceDocumentRecord] = Field(default_factory=list)
    pipeline_state: list[PipelineRunRecord] = Field(default_factory=list)
    source: str
    job_id: str | None = None

    def agent_evidence(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return bounded structured evidence suitable for Agent state."""
        items = [item.model_dump(mode="json") for item in self.evidence]
        seen = {(item.get("field"), item.get("source_type"), item.get("excerpt")) for item in items}
        for fact in self.facts:
            key = (fact.field, fact.source_type, None)
            if key in seen:
                continue
            items.append(
                {
                    "field": fact.field,
                    "value": fact.value,
                    "unit": fact.unit,
                    "statement": fact.statement,
                    "period_start": fact.period_start,
                    "period_end": fact.period_end,
                    "source_type": fact.source_type,
                    "confidence": fact.confidence,
                    "xbrl_tag": fact.xbrl_tag,
                }
            )
            if len(items) >= limit:
                break
        return items[:limit]
