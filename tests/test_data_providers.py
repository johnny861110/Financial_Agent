"""Contract tests for financial data providers."""

import json
from pathlib import Path

import httpx
import pytest

from app.core.data_loader import DataLoader
from app.data import (
    FallbackFinancialDataProvider,
    FinancialDataProviderUnavailable,
    FinancialReportsProvider,
    JsonFinancialDataProvider,
)


CONTRACT_FIXTURE = Path(__file__).parent / "fixtures" / "financial_reports_snapshot_v1.json"


def _snapshot_payload(stock_code: str = "2330", period: str = "2025Q1") -> dict:
    return {
        "stock_code": stock_code,
        "company_name": "Test Company",
        "report_year": int(period[:4]),
        "report_season": int(period[-1]),
        "report_period": period,
        "net_revenue": 1000.0,
        "gross_profit": 400.0,
        "operating_income": 250.0,
        "net_income": 200.0,
        "eps": 2.5,
        "total_assets": 5000.0,
        "total_liabilities": 2000.0,
        "equity": 3000.0,
    }


def test_json_provider_and_data_loader_compatibility(tmp_path):
    payload = _snapshot_payload()
    path = tmp_path / "2330_2025Q1_enhanced.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    provider = JsonFinancialDataProvider(tmp_path)

    record = provider.load_record("2330", "2025Q1")
    snapshot = DataLoader(provider).load_snapshot("2330", "2025Q1")

    assert record is not None
    assert record.source == "json"
    assert snapshot is not None
    assert snapshot.eps == 2.5
    assert any(item.field == "net_revenue" for item in record.evidence)
    assert provider.list_available_periods("2330") == ["2025Q1"]
    assert provider.list_all_stocks() == ["2330"]


def test_financial_reports_provider_maps_canonical_snapshot():
    contract = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/filings/2330/2025Q1/snapshot"
        return httpx.Response(200, json=contract)

    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(handler),
    )
    provider = FinancialReportsProvider(
        "http://financial-reports.test", max_retries=0, client=client
    )

    record = provider.load_record("2330", "2025Q1")

    assert record is not None
    assert record.snapshot is not None
    assert record.snapshot.eps == 2.5
    assert record.snapshot.report_season == 1
    assert record.quality.score == 0.9
    assert record.evidence[0].source_type == "xbrl"


def test_financial_reports_provider_retries_server_failure():
    contract = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=contract)

    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(handler),
    )
    provider = FinancialReportsProvider(
        "http://financial-reports.test", max_retries=1, client=client
    )

    assert provider.load_record("2330", "2025Q1") is not None
    assert attempts == 2


def test_financial_reports_provider_uses_stale_cache_during_outage():
    contract = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(200, json=contract)
        return httpx.Response(503)

    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(handler),
    )
    provider = FinancialReportsProvider(
        "http://financial-reports.test",
        max_retries=0,
        cache_ttl_seconds=0,
        client=client,
    )

    assert provider.load_record("2330", "2025Q1") is not None
    stale = provider.load_record("2330", "2025Q1")

    assert stale is not None
    assert stale.status == "stale"
    assert stale.freshness.is_stale is True


def test_fallback_is_used_only_when_remote_is_unavailable(tmp_path):
    payload = _snapshot_payload()
    (tmp_path / "2330_2025Q1_enhanced.json").write_text(json.dumps(payload), encoding="utf-8")

    def unavailable(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(unavailable),
    )
    remote = FinancialReportsProvider("http://financial-reports.test", max_retries=0, client=client)
    provider = FallbackFinancialDataProvider(remote, JsonFinancialDataProvider(tmp_path))

    record = provider.load_record("2330", "2025Q1")

    assert record is not None
    assert record.source == "json"


def test_remote_not_found_does_not_fall_back(tmp_path):
    payload = _snapshot_payload()
    (tmp_path / "2330_2025Q1_enhanced.json").write_text(json.dumps(payload), encoding="utf-8")

    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(lambda _: httpx.Response(404)),
    )
    remote = FinancialReportsProvider("http://financial-reports.test", max_retries=0, client=client)
    provider = FallbackFinancialDataProvider(remote, JsonFinancialDataProvider(tmp_path))

    assert provider.load_record("2330", "2025Q1") is None


def test_json_refresh_is_explicitly_unsupported(tmp_path):
    with pytest.raises(FinancialDataProviderUnavailable):
        JsonFinancialDataProvider(tmp_path).request_refresh("2330", "2025Q1")
