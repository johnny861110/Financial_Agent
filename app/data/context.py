"""Schema-aware financial context consumed by deterministic services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.data.models import (
    CanonicalFact,
    DataFreshness,
    DataQuality,
    EvidenceReference,
    FieldAvailability,
    MetricRecord,
    SnapshotRecord,
    ValidationRecord,
)


class FinancialContextError(ValueError):
    """Base error for invalid or unavailable canonical financial data."""


class FieldUnavailableError(FinancialContextError):
    """Raised when a required canonical field is not present."""

    def __init__(self, field: str, state: str, reason: str | None = None) -> None:
        detail = f"Required field {field!r} is {state}"
        if reason:
            detail = f"{detail}: {reason}"
        super().__init__(detail)
        self.field = field
        self.state = state
        self.reason = reason


class UnitMismatchError(FinancialContextError):
    """Raised when a field or metric uses an unexpected unit."""

    def __init__(self, name: str, expected: str, actual: str) -> None:
        super().__init__(f"{name!r} uses unit {actual!r}; expected {expected!r}")
        self.name = name
        self.expected = expected
        self.actual = actual


@dataclass(frozen=True)
class CanonicalFinancialContext:
    """Indexed, schema-aware view of one provider filing record."""

    record: SnapshotRecord

    @property
    def stock_code(self) -> str:
        if self.record.identity:
            return self.record.identity.stock_code
        if self.record.snapshot:
            return self.record.snapshot.stock_code
        return ""

    @property
    def period(self) -> str:
        if self.record.identity:
            return self.record.identity.period
        if self.record.snapshot:
            return self.record.snapshot.report_period
        return ""

    @property
    def company_name(self) -> str:
        if self.record.identity:
            return self.record.identity.company_name
        if self.record.snapshot:
            return self.record.snapshot.company_name
        return self.stock_code

    @property
    def quality(self) -> DataQuality:
        return self.record.quality

    @property
    def freshness(self) -> DataFreshness:
        return self.record.freshness

    @property
    def has_analysis_data(self) -> bool:
        return self.record.snapshot is not None or bool(self.record.facts)

    def availability(self, field: str) -> FieldAvailability:
        for item in self.record.field_availability:
            if item.field == field:
                return item

        value = self._snapshot_value(field)
        return FieldAvailability(
            field=field,
            statement="legacy_snapshot",
            unit=self._legacy_unit(field),
            state="present" if value is not None else "missing",
            reason=None if value is not None else "Field is absent from the provider record",
        )

    def optional_fact(self, field: str, expected_unit: str | None = None) -> CanonicalFact | None:
        for fact in self.record.facts:
            if fact.field != field:
                continue
            self._require_unit(field, expected_unit, fact.unit)
            return fact
        return None

    def required_fact(self, field: str, expected_unit: str | None = None) -> CanonicalFact:
        fact = self.optional_fact(field, expected_unit)
        if fact is not None:
            return fact
        availability = self.availability(field)
        raise FieldUnavailableError(field, availability.state, availability.reason)

    def optional_value(self, field: str, expected_unit: str | None = None) -> float | None:
        fact = self.optional_fact(field, expected_unit)
        if fact is not None:
            return fact.value

        availability = self.availability(field)
        if availability.state != "present":
            return None
        value = self._snapshot_value(field)
        if value is None:
            return None
        self._require_unit(field, expected_unit, self._legacy_unit(field))
        return float(value)

    def required_value(self, field: str, expected_unit: str | None = None) -> float:
        value = self.optional_value(field, expected_unit)
        if value is not None:
            return value
        availability = self.availability(field)
        raise FieldUnavailableError(field, availability.state, availability.reason)

    def metric(self, name: str, expected_unit: str | None = None) -> MetricRecord | None:
        for metric in self.record.metric_records:
            if metric.name != name:
                continue
            self._require_unit(name, expected_unit, metric.unit)
            return metric
        return None

    def metric_value(self, name: str, expected_unit: str | None = None) -> float | None:
        metric = self.metric(name, expected_unit)
        if metric is not None:
            return metric.value
        raw = self.record.metrics.get(name)
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, dict) and isinstance(raw.get("value"), (int, float)):
            actual_unit = raw.get("unit")
            if isinstance(actual_unit, str):
                self._require_unit(name, expected_unit, actual_unit)
            return float(raw["value"])
        return None

    def ratio_percent(
        self,
        metric_name: str,
        numerator_field: str,
        denominator_field: str,
        *,
        annualize: float = 1.0,
    ) -> float | None:
        metric = self.metric(metric_name)
        if metric is not None:
            if metric.unit == "ratio":
                return metric.value * 100
            if metric.unit == "percent":
                return metric.value
            raise UnitMismatchError(metric_name, "ratio or percent", metric.unit)

        legacy_metric = self.metric_value(metric_name)
        if legacy_metric is not None:
            return legacy_metric * 100

        numerator = self.optional_value(numerator_field, "TWD_thousands")
        denominator = self.optional_value(denominator_field, "TWD_thousands")
        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator * 100 * annualize

    def failed_validations(
        self,
        fields: Iterable[str] | None = None,
        severities: Iterable[str] | None = None,
    ) -> list[ValidationRecord]:
        field_set = set(fields or [])
        severity_set = set(severities or [])
        failures = [item for item in self.record.validation if not item.passed]
        if severity_set:
            failures = [item for item in failures if item.severity in severity_set]
        if field_set:
            failures = [
                item
                for item in failures
                if any(field in (item.message or "") for field in field_set)
                or any(field in item.rule_name for field in field_set)
            ]
        return failures

    def evidence_for(self, fields: Iterable[str], limit: int = 20) -> list[EvidenceReference]:
        requested = set(fields)
        evidence: list[EvidenceReference] = []
        seen: set[tuple[int | None, int | None, str | None]] = set()

        candidates = list(self.record.evidence)
        for fact in self.record.facts:
            if fact.field in requested:
                candidates.extend(fact.evidence)

        for item in candidates:
            if item.field not in requested:
                continue
            key = (item.fact_id, item.source_document_id, item.excerpt)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(item)
            if len(evidence) >= limit:
                break
        return evidence

    def field_states(self, fields: Iterable[str]) -> dict[str, str]:
        return {field: self.availability(field).state for field in fields}

    def _snapshot_value(self, field: str) -> float | None:
        if self.record.snapshot is None:
            return None
        attribute = {"eps_basic": "eps"}.get(field, field)
        value = getattr(self.record.snapshot, attribute, None)
        return float(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _legacy_unit(field: str) -> str:
        if field in {"eps", "eps_basic"}:
            return "TWD_per_share"
        return "TWD_thousands"

    @staticmethod
    def _require_unit(name: str, expected: str | None, actual: str) -> None:
        if expected is not None and actual != expected:
            raise UnitMismatchError(name, expected, actual)
