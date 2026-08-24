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
    assert record.identity is not None
    assert record.identity.filing_key == "2330_2025Q1"
    assert record.identity.industry == "Semiconductor"
    assert record.snapshot is not None
    assert record.snapshot.eps == 2.5
    assert record.snapshot.report_season == 1
    assert record.quality.score == 0.9
    assert record.pipeline_status == "validated"
    assert record.quality.validation_failures[0]["rule_name"] == "balance_sheet_equation"
    assert record.evidence[0].source_type == "xbrl"
    assert record.evidence[0].source_url == "https://example.test/report.xml"
    assert record.facts[0].field == "net_revenue"
    assert record.facts[0].unit == "TWD_thousands"
    assert record.metric_records[0].unit == "ratio"
    assert record.field_availability[0].state == "present"
    assert record.validation[0].passed is False
    assert record.comparisons[0].compare_period == "2024Q1"
    assert record.insight_cards[0].card_type == "performance_summary"
    assert record.source_documents[0].checksum == "abc123"
    assert record.pipeline_state[0].stage == "validate"
    assert any(item["field"] == "net_revenue" for item in record.agent_evidence())


def test_financial_reports_provider_maps_not_ready_to_processing():
    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                409,
                json={
                    "schema_version": "1.0.0",
                    "error": {
                        "code": "filing_not_ready",
                        "message": "filing has not reached validated",
                        "data_state": "missing",
                    },
                },
            )
        ),
    )
    provider = FinancialReportsProvider(
        "http://financial-reports.test", max_retries=0, client=client
    )

    record = provider.load_record("2330", "2025Q1")

    assert record is not None
    assert record.status == "processing"
    assert record.snapshot is None


def test_financial_reports_provider_paginates_stocks_and_periods():
    requests: list[tuple[str, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        requests.append((request.url.path, offset))
        if request.url.path == "/v1/stocks":
            items = (
                [{"stock_code": str(index)} for index in range(100)]
                if offset == 0
                else [{"stock_code": "final"}]
            )
            return httpx.Response(
                200,
                json={
                    "stocks": items,
                    "pagination": {"limit": 100, "offset": offset, "total": 101},
                },
            )
        return httpx.Response(
            200,
            json={
                "periods": ["2024Q4", "2025Q1"],
                "pagination": {"limit": 100, "offset": 0, "total": 2},
            },
        )

    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(handler),
    )
    provider = FinancialReportsProvider(
        "http://financial-reports.test", max_retries=0, client=client
    )

    stocks = provider.list_all_stocks()
    periods = provider.list_available_periods("2330")

    assert len(stocks) == 101
    assert "final" in stocks
    assert periods == ["2024Q4", "2025Q1"]
    assert ("/v1/stocks", 100) in requests


def test_financial_reports_provider_exposes_capabilities():
    client = httpx.Client(
        base_url="http://financial-reports.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "schema_version": "1.0.0",
                    "api_version": "v1",
                    "data_states": {"missing": "not supplied"},
                    "fields": [{"name": "net_revenue"}],
                },
            )
        ),
    )
    provider = FinancialReportsProvider(
        "http://financial-reports.test", max_retries=0, client=client
    )

    capabilities = provider.get_capabilities()

    assert capabilities["api_version"] == "v1"
    assert capabilities["fields"][0]["name"] == "net_revenue"


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
