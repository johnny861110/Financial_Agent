"""Regression checks for the workbench/backend boundary."""

from app.agents.workflow import FinancialAgent
from app.core.config import Settings
from app.models.agent_models import AgentQuery


def test_explicit_research_target_does_not_discover_unrelated_filings(monkeypatch):
    agent = FinancialAgent()

    def forbidden_discovery():
        raise AssertionError("an explicit filing must not enumerate the entire provider")

    class Graph:
        def invoke(self, state, config):
            assert state["stock_code"] == "2330"
            assert state["period"] == "2025Q1"
            return {**state, "final_answer": "No fixture findings", "report": {}}

    monkeypatch.setattr(agent, "_default_stock_period", forbidden_discovery)
    monkeypatch.setattr(agent, "graph", Graph())
    result = agent.query(AgentQuery(query="snapshot", stock_code="2330", period="2025Q1"))
    assert result.answer == "No fixture findings"


def test_workbench_defaults_match_documented_provider_policy(monkeypatch):
    for name in ("DATA_PROVIDER", "ALLOW_JSON_FALLBACK", "API_CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.data_provider == "financial_reports"
    assert settings.allow_json_fallback is False
    assert "http://localhost:5173" in settings.api_cors_origins.split(",")
    assert "*" not in settings.api_cors_origins.split(",")
