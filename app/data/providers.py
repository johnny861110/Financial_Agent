"""Provider implementations for local and remote financial data."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx

from app.data.models import DataFreshness, EvidenceReference, SnapshotRecord
from app.models import FinancialSnapshot


class FinancialDataProviderError(RuntimeError):
    """Base error for provider failures."""


class FinancialDataProviderUnavailable(FinancialDataProviderError):
    """Raised when a provider cannot be reached or has a server failure."""


class FinancialDataContractError(FinancialDataProviderError):
    """Raised when a provider violates the expected data contract."""


@runtime_checkable
class FinancialDataProvider(Protocol):
    """Stable data access interface consumed by analysis services."""

    def load_record(self, stock_code: str, period: str) -> SnapshotRecord | None: ...

    def list_available_periods(self, stock_code: str) -> list[str]: ...

    def list_all_stocks(self) -> list[str]: ...

    def get_context(
        self, stock_code: str, period: str, question: str | None = None
    ) -> dict[str, Any] | None: ...

    def request_refresh(self, stock_code: str, period: str) -> dict[str, Any]: ...

    def get_job(self, job_id: str) -> dict[str, Any]: ...


class JsonFinancialDataProvider:
    """Read legacy enhanced JSON snapshots from the local filesystem."""

    def __init__(self, data_path: str | Path) -> None:
        self.data_path = Path(data_path)

    def load_record(self, stock_code: str, period: str) -> SnapshotRecord | None:
        file_path = self.data_path / f"{stock_code}_{period}_enhanced.json"
        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            snapshot = FinancialSnapshot(**data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise FinancialDataContractError(f"Unable to load {file_path.name}: {exc}") from exc

        evidence = [
            EvidenceReference(
                field=field,
                source_type="json",
                excerpt=file_path.name,
                confidence=1.0,
            )
            for field in FinancialSnapshot.model_fields
            if getattr(snapshot, field, None) is not None
        ]
        return SnapshotRecord(snapshot=snapshot, source="json", evidence=evidence)

    def list_available_periods(self, stock_code: str) -> list[str]:
        periods = {
            file.stem.split("_")[1]
            for file in self.data_path.glob(f"{stock_code}_*_enhanced.json")
            if len(file.stem.split("_")) >= 2
        }
        return sorted(periods)

    def list_all_stocks(self) -> list[str]:
        stocks = {
            file.stem.split("_")[0]
            for file in self.data_path.glob("*_enhanced.json")
            if file.stem.split("_")
        }
        return sorted(stocks)

    def get_context(
        self, stock_code: str, period: str, question: str | None = None
    ) -> dict[str, Any] | None:
        record = self.load_record(stock_code, period)
        return record.model_dump(mode="json") if record else None

    def request_refresh(self, stock_code: str, period: str) -> dict[str, Any]:
        raise FinancialDataProviderUnavailable("The JSON provider cannot refresh source data")

    def get_job(self, job_id: str) -> dict[str, Any]:
        raise FinancialDataProviderUnavailable("The JSON provider does not support jobs")


class FinancialReportsProvider:
    """Consume the versioned FinancialReports HTTP API."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        max_retries: int = 2,
        cache_ttl_seconds: float = 300.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self._client = client or httpx.Client(base_url=self.base_url, timeout=timeout)
        self._record_cache: dict[tuple[str, str], tuple[float, SnapshotRecord]] = {}

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(method, path, **kwargs)
                if response.status_code >= 500:
                    raise FinancialDataProviderUnavailable(
                        f"FinancialReports returned HTTP {response.status_code}"
                    )
                return response
            except (
                httpx.TimeoutException,
                httpx.TransportError,
                FinancialDataProviderUnavailable,
            ) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(0.1 * (2**attempt))

        raise FinancialDataProviderUnavailable(
            f"FinancialReports is unavailable: {last_error}"
        ) from last_error

    @staticmethod
    def _response_object(response: httpx.Response) -> dict[str, Any]:
        body = response.json()
        if not isinstance(body, dict):
            raise FinancialDataContractError("FinancialReports returned a non-object response")
        return body

    def load_record(self, stock_code: str, period: str) -> SnapshotRecord | None:
        cache_key = (stock_code, period)
        cached = self._record_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] <= self.cache_ttl_seconds:
            return cached[1].model_copy(deep=True)

        try:
            response = self._request("GET", f"/v1/filings/{stock_code}/{period}/snapshot")
        except FinancialDataProviderUnavailable:
            if cached:
                stale = cached[1].model_copy(deep=True)
                stale.freshness = DataFreshness(
                    updated_at=stale.freshness.updated_at,
                    is_stale=True,
                )
                stale.status = "stale"
                return stale
            raise
        if response.status_code == 404:
            self._record_cache.pop(cache_key, None)
            return None
        if response.status_code == 202:
            body = self._response_object(response)
            return SnapshotRecord(
                status="processing",
                source="financial_reports",
                job_id=body.get("job_id"),
            )
        if response.status_code == 422:
            raise FinancialDataContractError(f"Invalid stock or period: {response.text}")
        response.raise_for_status()

        try:
            body = self._response_object(response)
            snapshot = self._map_snapshot(body)
            record = SnapshotRecord(
                schema_version=str(body.get("schema_version", "1.0")),
                status=str(body.get("status", "ready")),
                snapshot=snapshot,
                quality=body.get("quality", {}),
                freshness=body.get("freshness", {}),
                evidence=body.get("evidence", []),
                metrics=body.get("metrics", {}),
                events=body.get("events", []),
                source="financial_reports",
                job_id=body.get("job_id"),
            )
            self._record_cache[cache_key] = (time.monotonic(), record.model_copy(deep=True))
            return record
        except (ValueError, TypeError, KeyError) as exc:
            raise FinancialDataContractError(
                f"Invalid FinancialReports snapshot response: {exc}"
            ) from exc

    @staticmethod
    def _map_snapshot(body: dict[str, Any]) -> FinancialSnapshot:
        identity = body.get("identity") or {}
        source = body.get("snapshot") or {}
        period = str(identity.get("period") or source.get("report_period") or "")
        if len(period) != 6 or period[4] != "Q" or period[5] not in "1234":
            raise ValueError(f"Invalid period in response: {period!r}")

        identity_fields = {
            "stock_code",
            "company_name",
            "report_year",
            "report_season",
            "report_period",
        }
        fields = {
            name: source[name]
            for name in FinancialSnapshot.model_fields
            if name not in identity_fields and source.get(name) is not None
        }
        fields["eps"] = source.get("eps", source.get("eps_basic"))
        fields.update(
            {
                "stock_code": str(identity.get("stock_code") or source.get("stock_code") or ""),
                "company_name": str(
                    identity.get("company_name")
                    or source.get("company_name")
                    or identity.get("stock_code")
                    or ""
                ),
                "report_year": int(period[:4]),
                "report_season": int(period[5]),
                "report_period": period,
            }
        )
        return FinancialSnapshot(**fields)

    def list_available_periods(self, stock_code: str) -> list[str]:
        response = self._request("GET", f"/v1/stocks/{stock_code}/periods")
        if response.status_code == 404:
            return []
        response.raise_for_status()
        body = self._response_object(response)
        return sorted(str(period) for period in body.get("periods", []))

    def list_all_stocks(self) -> list[str]:
        response = self._request("GET", "/v1/stocks")
        response.raise_for_status()
        body = self._response_object(response)
        stocks = body.get("stocks", [])
        return sorted(
            str(item.get("stock_code")) if isinstance(item, dict) else str(item) for item in stocks
        )

    def get_context(
        self, stock_code: str, period: str, question: str | None = None
    ) -> dict[str, Any] | None:
        params = {"question": question} if question else None
        response = self._request("GET", f"/v1/filings/{stock_code}/{period}/context", params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return self._response_object(response)

    def request_refresh(self, stock_code: str, period: str) -> dict[str, Any]:
        response = self._request("POST", f"/v1/filings/{stock_code}/{period}/refresh")
        if response.status_code not in (200, 202):
            response.raise_for_status()
        return self._response_object(response)

    def get_job(self, job_id: str) -> dict[str, Any]:
        response = self._request("GET", f"/v1/jobs/{job_id}")
        if response.status_code == 404:
            raise FinancialDataContractError(f"Unknown FinancialReports job: {job_id}")
        response.raise_for_status()
        return self._response_object(response)


class FallbackFinancialDataProvider:
    """Use fallback data only when the primary provider is unavailable."""

    def __init__(self, primary: FinancialDataProvider, fallback: FinancialDataProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def load_record(self, stock_code: str, period: str) -> SnapshotRecord | None:
        try:
            return self.primary.load_record(stock_code, period)
        except FinancialDataProviderUnavailable:
            return self.fallback.load_record(stock_code, period)

    def list_available_periods(self, stock_code: str) -> list[str]:
        try:
            return self.primary.list_available_periods(stock_code)
        except FinancialDataProviderUnavailable:
            return self.fallback.list_available_periods(stock_code)

    def list_all_stocks(self) -> list[str]:
        try:
            return self.primary.list_all_stocks()
        except FinancialDataProviderUnavailable:
            return self.fallback.list_all_stocks()

    def get_context(
        self, stock_code: str, period: str, question: str | None = None
    ) -> dict[str, Any] | None:
        try:
            return self.primary.get_context(stock_code, period, question)
        except FinancialDataProviderUnavailable:
            return self.fallback.get_context(stock_code, period, question)

    def request_refresh(self, stock_code: str, period: str) -> dict[str, Any]:
        return self.primary.request_refresh(stock_code, period)

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self.primary.get_job(job_id)
