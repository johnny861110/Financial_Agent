"""Deterministic tool-eligibility tests for the schema-aware tool contracts."""

import json

from app.agents.tools import (
    TOOL_REGISTRY,
    TOOL_REQUIREMENTS,
    configure_tool_services,
    evaluate_eligibility,
    required_fields_for_planning,
)
from app.agents.workflow import FinancialAgent
from app.core import DataLoader
from app.data import JsonFinancialDataProvider
from app.models.agent_models import AgentQuery
from app.services.earnings_quality_service import EARNINGS_QUALITY_REQUIRED_FIELDS
from app.services.ews_service import EWS_REQUIRED_FIELDS
from app.services.factor_service import FACTOR_MONEY_FIELDS
from app.services.roic_wacc_service import ROIC_WACC_REQUIRED_FIELDS


def _all_present(fields) -> dict[str, str]:
    return {field: "present" for field in fields}


def test_every_planner_tool_declares_requirements():
    """A tool must not reach the planner without declaring what it needs.

    Guards the omission that let `factor` run ungated: it was simply absent
    from the old hardcoded map.
    """
    assert set(TOOL_REGISTRY) == set(TOOL_REQUIREMENTS)


def test_requirements_are_the_service_constants_not_copies():
    """Regression for planner/service drift.

    The old hardcoded map listed 5 fields for ews while EarlyWarningService
    required 6, and had no factor entry at all. Requirements must be the
    service's own list so the two cannot disagree.
    """
    assert TOOL_REQUIREMENTS["ews"].required_fields == EWS_REQUIRED_FIELDS
    assert "cash_and_equivalents" in TOOL_REQUIREMENTS["ews"].required_fields
    assert TOOL_REQUIREMENTS["earnings_quality"].required_fields == EARNINGS_QUALITY_REQUIRED_FIELDS
    assert TOOL_REQUIREMENTS["roic_wacc"].required_fields == ROIC_WACC_REQUIRED_FIELDS
    assert TOOL_REQUIREMENTS["factor"].required_fields == FACTOR_MONEY_FIELDS
    assert TOOL_REQUIREMENTS["factor"].extra_unit_fields == {"eps_basic": "TWD_per_share"}


def test_planning_fields_cover_every_gated_field():
    planning_fields = set(required_fields_for_planning())
    for requirements in TOOL_REQUIREMENTS.values():
        assert set(requirements.all_required_fields) <= planning_fields


def test_tool_is_eligible_when_every_required_field_is_present():
    states = _all_present(required_fields_for_planning())

    assert evaluate_eligibility("ews", states) is None
    assert evaluate_eligibility("factor", states) is None


def test_unusable_field_states_block_the_tool():
    """missing, null, not_applicable and provider_failure all block."""
    for state in ("missing", "null", "not_applicable", "provider_failure"):
        states = _all_present(required_fields_for_planning())
        states["cash_and_equivalents"] = state

        blocked = evaluate_eligibility("ews", states)

        assert blocked is not None, f"state {state!r} should block"
        assert blocked["status"] == "insufficient_data"
        assert blocked["blocked_fields"] == {"cash_and_equivalents": state}
        assert blocked["missing_fields"] == ["cash_and_equivalents"]
        assert "cash_and_equivalents" in blocked["finding"]
        assert state in blocked["finding"]


def test_undeterminable_field_blocks_rather_than_passing():
    """A field whose state is unknown must never read as eligible."""
    states = _all_present(required_fields_for_planning())
    del states["cash_and_equivalents"]

    blocked = evaluate_eligibility("ews", states)

    assert blocked is not None
    assert blocked["blocked_fields"] == {"cash_and_equivalents": "unknown"}


def test_a_tools_gate_ignores_fields_it_does_not_require():
    """roic_wacc does not need cash_and_equivalents, so it stays eligible."""
    states = _all_present(required_fields_for_planning())
    states["cash_and_equivalents"] = "missing"

    assert evaluate_eligibility("roic_wacc", states) is None
    assert evaluate_eligibility("ews", states) is not None


def test_assumption_only_tools_stay_eligible_without_filing_data():
    assert TOOL_REQUIREMENTS["management"].uses_filing_data is False
    assert evaluate_eligibility("management", {}) is None


def test_best_effort_tools_declare_an_empty_gate_and_stay_eligible():
    for name in ("snapshot", "trend", "peer", "capital_allocation"):
        assert TOOL_REQUIREMENTS[name].required_fields == []
        assert evaluate_eligibility(name, {}) is None


# No tool opts into the stale/quality/validation gates today -- picking those
# thresholds is a product decision, not an engineering one. The machinery is
# live and exercised here by overriding one tool's declaration, so opting a
# tool in later is a one-line change rather than new plumbing.


def test_stale_data_blocks_only_tools_that_require_freshness(monkeypatch):
    states = _all_present(required_fields_for_planning())

    assert evaluate_eligibility("ews", states, is_stale=True) is None

    monkeypatch.setitem(
        TOOL_REQUIREMENTS,
        "ews",
        TOOL_REQUIREMENTS["ews"].model_copy(update={"allows_stale": False}),
    )

    blocked = evaluate_eligibility("ews", states, is_stale=True)
    assert blocked is not None
    assert "stale" in blocked["finding"]


def test_quality_threshold_blocks_below_the_declared_minimum(monkeypatch):
    states = _all_present(required_fields_for_planning())
    monkeypatch.setitem(
        TOOL_REQUIREMENTS,
        "ews",
        TOOL_REQUIREMENTS["ews"].model_copy(update={"min_quality": 0.6}),
    )

    assert evaluate_eligibility("ews", states, quality_score=0.9) is None

    blocked = evaluate_eligibility("ews", states, quality_score=0.4)
    assert blocked is not None
    assert "quality" in blocked["finding"]


def test_blocking_validation_rule_blocks_the_tool(monkeypatch):
    states = _all_present(required_fields_for_planning())
    monkeypatch.setitem(
        TOOL_REQUIREMENTS,
        "ews",
        TOOL_REQUIREMENTS["ews"].model_copy(
            update={"blocking_validation_rules": ["balance_sheet_equation"]}
        ),
    )

    # A failed rule the tool does not declare as blocking is not a gate.
    assert evaluate_eligibility("ews", states, failed_rules=["unrelated_rule"]) is None

    blocked = evaluate_eligibility(
        "ews", states, failed_rules=["balance_sheet_equation", "unrelated_rule"]
    )
    assert blocked is not None
    assert blocked["failed_rules"] == ["balance_sheet_equation"]
    assert "balance_sheet_equation" in blocked["finding"]


def _write_filing(directory, period: str, index: int, **overrides) -> None:
    payload = {
        "stock_code": "2330",
        "company_name": "Test Company",
        "report_year": int(period[:4]),
        "report_season": int(period[-1]),
        "report_period": period,
        "cash_and_equivalents": 900 + index * 20,
        "accounts_receivable": 180 + index * 8,
        "inventory": 150 + index * 5,
        "total_assets": 5000 + index * 100,
        "total_liabilities": 2000 + index * 30,
        "equity": 3000 + index * 70,
        "net_revenue": 1000 + index * 80,
        "gross_profit": 400 + index * 35,
        "operating_income": 250 + index * 25,
        "net_income": 200 + index * 20,
        "eps": 2.0 + index * 0.2,
        "operating_cash_flow": 220 + index * 22,
    }
    payload.update(overrides)
    payload = {key: value for key, value in payload.items() if value is not None}
    (directory / f"2330_{period}_enhanced.json").write_text(json.dumps(payload), encoding="utf-8")


def test_blocked_tool_short_circuits_end_to_end(tmp_path):
    """A filing missing one field blocks only the tools that require it.

    This is the case the previous gate could not catch at all: it read
    producer-reported quality.missing_fields, which JsonFinancialDataProvider
    never populates, so nothing was ever blocked before invocation.
    """
    for index, period in enumerate(["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1"]):
        _write_filing(tmp_path, period, index, cash_and_equivalents=None)

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

    tools = response.data["tools"]
    assert tools["ews"]["status"] == "insufficient_data"
    assert tools["ews"]["blocked_fields"] == {"cash_and_equivalents": "missing"}

    # Tools that do not require the absent field are unaffected.
    assert tools["roic_wacc"]["status"] == "success"
    assert tools["earnings_quality"]["status"] == "success"


def test_confidence_reflects_degraded_data(tmp_path):
    """A run with a blocked tool is less confident than a complete one."""
    complete = tmp_path / "complete"
    degraded = tmp_path / "degraded"
    complete.mkdir()
    degraded.mkdir()

    periods = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1"]
    for index, period in enumerate(periods):
        _write_filing(complete, period, index)
        _write_filing(degraded, period, index, cash_and_equivalents=None)

    def run(directory) -> float:
        loader = DataLoader(JsonFinancialDataProvider(directory))
        agent = FinancialAgent()
        agent.data_loader = loader
        configure_tool_services(loader)
        return agent.query(
            AgentQuery(
                query="請完整分析 2330 是否值得持有",
                stock_code="2330",
                period="2025Q1",
                mode="research",
            )
        ).confidence_score

    complete_score = run(complete)
    degraded_score = run(degraded)

    assert 0 < degraded_score < complete_score
