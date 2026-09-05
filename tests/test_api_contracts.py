"""Contract tests for the public deterministic API responses."""

from app.core import DataLoader
from app.models.api_models import FinancialSnapshotResponse
from app.main import app
from app.services.factory import ServiceRegistry
from tests.helpers import RecordProvider, make_record


def test_snapshot_contract_preserves_nullable_financial_values(monkeypatch):
    record = make_record(
        "2024Q1",
        snapshot_overrides={"net_revenue": None, "gross_profit": None, "equity": None},
    )
    registry = ServiceRegistry.build(DataLoader(RecordProvider({("2330", "2024Q1"): record})))
    result = registry.snapshot.get_summary("2330", "2024Q1")
    assert result is not None
    result["units"] = {"monetary": "TWD_thousands"}
    body = FinancialSnapshotResponse.model_validate(result).model_dump(mode="json")
    assert body["income_statement"]["net_revenue"] is None
    assert body["income_statement"]["gross_profit"] is None
    assert body["balance_sheet"]["equity"] is None
    assert body["identification"]["unit"] == "thousand"
    assert body["units"]["monetary"] == "TWD_thousands"


def test_openapi_has_populated_response_schemas():
    schemas = app.openapi()["components"]["schemas"]
    paths = app.openapi()["paths"]

    expected = {
        ("/api/financials/{stock_code}/{period}", "get"),
        ("/api/trend/{stock_code}", "get"),
        ("/api/peers/compare", "post"),
        ("/api/scores/management", "post"),
        ("/api/scores/earnings_quality/{stock_code}/{period}", "get"),
        ("/api/roic_wacc/{stock_code}/{period}", "post"),
        ("/api/factors/{stock_code}/{period}", "post"),
        ("/api/capital_allocation/{stock_code}/{period}", "post"),
        ("/api/ews/{stock_code}/{period}", "get"),
        ("/api/data/stocks", "get"),
        ("/api/data/{stock_code}/periods", "get"),
    }

    for path, method in expected:
        response = paths[path][method]["responses"]["200"]
        schema = response["content"]["application/json"]["schema"]
        assert "$ref" in schema or schema.get("type") == "object"

    assert "FinancialSnapshotResponse" in schemas
    assert "TrendResponse" in schemas
    assert "PeerResponse" in schemas
    assert "UnitsMetadata" in schemas
