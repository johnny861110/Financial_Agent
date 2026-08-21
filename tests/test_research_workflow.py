"""End-to-end test for the deterministic multi-tool research workflow."""

import json

from app.agents.tools import configure_tool_services
from app.agents.workflow import FinancialAgent
from app.core import DataLoader
from app.data import JsonFinancialDataProvider
from app.models.agent_models import AgentQuery


def _period_payload(period: str, index: int) -> dict:
    return {
        "stock_code": "2330",
        "company_name": "Test Company",
        "report_year": int(period[:4]),
        "report_season": int(period[-1]),
        "report_period": period,
        "cash_and_equivalents": 900 + index * 20,
        "accounts_receivable": 180 + index * 8,
        "inventory": 150 + index * 5,
        "current_assets": 1800 + index * 50,
        "current_liabilities": 700 + index * 20,
        "total_assets": 5000 + index * 100,
        "total_liabilities": 2000 + index * 30,
        "equity": 3000 + index * 70,
        "net_revenue": 1000 + index * 80,
        "gross_profit": 400 + index * 35,
        "operating_income": 250 + index * 25,
        "net_income": 200 + index * 20,
        "eps": 2.0 + index * 0.2,
        "operating_cash_flow": 220 + index * 22,
        "investing_cash_flow": -100 - index * 5,
        "financing_cash_flow": -50,
    }


def test_research_mode_runs_multiple_tools_and_builds_report(tmp_path):
    periods = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1"]
    for index, period in enumerate(periods):
        (tmp_path / f"2330_{period}_enhanced.json").write_text(
            json.dumps(_period_payload(period, index)), encoding="utf-8"
        )

    loader = DataLoader(JsonFinancialDataProvider(tmp_path))
    agent = FinancialAgent()
    agent.data_loader = loader
    configure_tool_services(loader)

    response = agent.query(
        AgentQuery(
            query="請完整分析 2330 是否值得持有",
            stock_code="2330",
            period="2025Q1",
            mode="research",
        )
    )

    assert response.verdict in {"偏正向", "中性", "警戒"}
    assert len(response.research_plan) >= 5
    assert len(response.findings) >= 3
    assert response.confidence_score > 0
    assert "json" in response.sources
    assert response.data["success"] is True
