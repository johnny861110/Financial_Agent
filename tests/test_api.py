"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.core import DataLoader
from app.main import app
from app.services.factory import ServiceRegistry
from tests.helpers import RecordProvider, make_record

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Financial Report Agent API"
    assert data["version"] == "2.0.0"


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "financial-agent"


def test_liveness_and_readiness_endpoints():
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert ready.json()["data_provider"] == "json"


def test_missing_data_status_is_structured():
    response = client.get("/api/data/999999/2025Q4/status")
    assert response.status_code == 200
    assert response.json()["status"] == "missing"
    assert response.json()["available"] is False


def test_json_refresh_returns_service_unavailable():
    response = client.post("/api/data/999999/2025Q4/refresh")
    assert response.status_code == 503


def test_data_capabilities_and_missing_record_endpoints():
    capabilities = client.get("/api/data/capabilities")
    missing = client.get("/api/data/999999/2025Q4/record")

    assert capabilities.status_code == 200
    assert capabilities.json()["source"] == "json"
    assert missing.status_code == 404


def test_management_score_endpoint():
    """Test management score calculation endpoint."""
    response = client.post(
        "/api/scores/management",
        json={
            "ceo_tenure_years": 5,
            "cfo_tenure_years": 4,
            "board_independence_ratio": 0.4,
            "insider_buys": 3,
            "insider_sells": 1,
            "governance_incidents": 0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_score" in data
    assert "components" in data
    assert "commentary" in data


def test_peer_comparison_endpoint():
    """Test peer comparison endpoint."""
    # Note: This will fail without actual data files
    # In production, would use test fixtures
    response = client.post(
        "/api/peers/compare",
        json={
            "stock_codes": ["2330", "2454"],
            "period": "2023Q3",
            "metrics": ["Gross Margin", "ROE"],
        },
    )

    # Expected to fail without data, but tests the endpoint exists
    assert response.status_code in [200, 404]


def test_agent_query_endpoint():
    """Test agent query endpoint."""
    # Note: This requires OpenAI API key in environment
    response = client.post(
        "/api/agent/query",
        json={
            "query": "What is the financial health of company 2330?",
            "stock_code": "2330",
            "period": "2023Q3",
        },
    )

    assert response.status_code == 200


def test_roic_wacc_missing_fields_returns_structured_error(monkeypatch):
    """ROIC/WACC should report missing data instead of raising a server error.

    Injects the service registry so the suite stays reproducible on a fresh
    clone; the repository's data/ directory is gitignored and absent in CI.
    """
    record = make_record("2024Q1", snapshot_overrides={"operating_income": None, "equity": None})
    registry = ServiceRegistry.build(DataLoader(RecordProvider({("2330", "2024Q1"): record})))
    monkeypatch.setattr("app.api.financials.get_service_registry", lambda: registry)

    response = client.post("/api/roic_wacc/2330/2024Q1", json={})

    assert response.status_code == 422
    data = response.json()["detail"]
    assert data["error"] == "insufficient_data"
    assert "missing_fields" in data
    assert "operating_income" in data["missing_fields"]


# ---------------------------------------------------------------------------
# Period contract and provider-fault translation
#
# A malformed period used to reach the provider and come back as "data not
# found", and a provider outage used to surface as a bare 500. Both hid the
# real problem from the caller.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_period",
    ["2026", "第一季", "not-a-period", "2026Q9"],
)
def test_snapshot_rejects_a_malformed_period_as_422(bad_period):
    response = client.get(f"/api/financials/3661/{bad_period}")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_period"
    assert "YYYYQn" in detail["message"]


def test_snapshot_accepts_an_unconventional_but_parseable_period():
    """A period the caller can write, normalized rather than rejected."""
    canonical = client.get("/api/financials/2330/2023Q3")
    chinese = client.get("/api/financials/2330/2023年第三季")

    assert canonical.status_code == chinese.status_code
    assert canonical.json() == chinese.json()


def test_missing_filing_is_still_a_404_not_a_422():
    """A well-formed period for data that does not exist is a different failure."""
    response = client.get("/api/financials/2330/2019Q1")

    assert response.status_code == 404


def test_data_discovery_endpoints_list_stocks_and_periods(monkeypatch):
    # data/ is gitignored, so read from a stub; it lists periods oldest first,
    # which makes the endpoint's newest-first ordering observable.
    provider = RecordProvider(
        {
            ("2330", "2023Q4"): make_record("2023Q4"),
            ("2330", "2024Q2"): make_record("2024Q2"),
            ("2330", "2024Q1"): make_record("2024Q1"),
            ("2454", "2024Q1"): make_record("2024Q1", stock_code="2454"),
        }
    )
    monkeypatch.setattr("app.api.data.get_data_provider", lambda: provider)

    stocks = client.get("/api/data/stocks")
    periods = client.get("/api/data/2330/periods")

    assert stocks.status_code == 200
    assert stocks.json()["stocks"] == ["2330", "2454"]
    assert periods.status_code == 200
    body = periods.json()
    assert body["stock_code"] == "2330"
    assert body["periods"] == ["2024Q2", "2024Q1", "2023Q4"]


def test_provider_outage_is_reported_as_503_not_500(monkeypatch):
    """A FinancialReports outage is an upstream fault, not a broken route."""
    from app.data.providers import FinancialDataProviderUnavailable
    from app.services import factory as service_factory

    def explode(*_args, **_kwargs):
        raise FinancialDataProviderUnavailable("FinancialReports is unavailable: timed out")

    registry = service_factory.get_service_registry()
    monkeypatch.setattr(registry.snapshot, "get_summary", explode)

    response = client.get("/api/financials/2330/2023Q3")

    assert response.status_code == 503
    assert response.json()["error"] == "data_source_unavailable"


def test_provider_contract_breach_is_reported_as_502(monkeypatch):
    from app.data.providers import FinancialDataContractError
    from app.services import factory as service_factory

    def explode(*_args, **_kwargs):
        raise FinancialDataContractError("Invalid FinancialReports snapshot response")

    registry = service_factory.get_service_registry()
    monkeypatch.setattr(registry.snapshot, "get_summary", explode)

    response = client.get("/api/financials/2330/2023Q3")

    assert response.status_code == 502
    assert response.json()["error"] == "data_source_contract"
