"""AppTest regressions for the legacy UI/API bridge."""

import importlib

import pytest
from app.models.agent_models import AgentResponse
from streamlit.testing.v1 import AppTest


PERIOD = "2026Q1"


@pytest.fixture
def discovery_backend(monkeypatch):
    import ui.data_source as data_source

    def discovery(method, path, **kwargs):
        if path.endswith("/capabilities"):
            return {"schema_version": "1.0.0", "api_version": "v1"}
        if path.endswith("/stocks"):
            return {"stocks": ["3661"]}
        if path.endswith("/periods"):
            return {"periods": [PERIOD]}
        raise AssertionError(f"unexpected discovery request: {method} {path}")

    data_source.clear_cache()
    monkeypatch.setattr(data_source, "api_request", discovery)
    yield
    data_source.clear_cache()


def _app(module: str) -> AppTest:
    app = AppTest.from_string(f"import {module} as page; page.show()", default_timeout=30)
    app.run()
    assert not app.exception
    return app


def test_snapshot_null_metrics_and_download_survive_rerun(discovery_backend, monkeypatch):
    import ui.pages.snapshot as page

    snapshot = {
        "identification": {"company_name": "Example", "period": PERIOD, "stock_code": "3661"},
        "income_statement": {
            "net_revenue": None,
            "net_income": 10,
            "eps": None,
            "gross_profit": None,
            "operating_income": None,
        },
        "balance_sheet": {
            "total_assets": None,
            "total_liabilities": None,
            "equity": None,
            "cash_and_equivalents": None,
        },
        "margins": {"gross_margin": None, "operating_margin": None, "net_margin": None},
        "financial_structure": {"debt_ratio": None, "equity_ratio": None, "current_ratio": None},
        "returns": {"roa": None, "roe": None},
        "data_context": {},
    }

    monkeypatch.setattr(page, "api_request", lambda method, path, **kwargs: snapshot)
    app = _app("ui.pages.snapshot")
    next(button for button in app.button if button.label == "🔍 Analyze").click().run()
    assert not app.exception
    assert any(metric.value == "N/A" for metric in app.metric)
    app.run()
    assert not app.exception


@pytest.mark.parametrize(
    ("module", "button", "response"),
    [
        (
            "ui.pages.earnings_quality",
            "🔍 Analyze Filing",
            {
                "total_score": 72,
                "components": {"accrual_quality": 70},
                "red_flags": [],
                "commentary": "backend",
                "details": {"unit": "TWD thousand"},
            },
        ),
        (
            "ui.pages.roic_wacc",
            "🔍 Analyze Filing",
            {
                "roic": 0.2,
                "wacc": 0.1,
                "value_creation_gap": 0.1,
                "is_value_creating": True,
                "nopat": 20,
                "invested_capital": 100,
                "assumptions": {"beta": 1.0},
                "commentary": "backend",
            },
        ),
        (
            "ui.pages.factor",
            "🔍 Analyze Filing",
            {
                "quality": 1.2,
                "value": 0.1,
                "momentum": -0.2,
                "size": 0.3,
                "volatility": -0.4,
                "commentary": "backend",
                "details": {"peer_count": 2},
            },
        ),
        (
            "ui.pages.ews",
            "🔍 Run Warning Detection",
            {
                "warning_level": "low",
                "signal_count": 1,
                "triggered_signals": [
                    {
                        "signal_name": "Liquidity",
                        "severity": "low",
                        "current_value": 0.5,
                        "threshold_value": 1.0,
                        "description": "backend signal",
                    }
                ],
                "recommendation": "monitor",
                "commentary": "backend",
            },
        ),
    ],
)
def test_migrated_page_submits_and_renders_backend_shape(
    discovery_backend, monkeypatch, module, button, response
):
    page = importlib.import_module(module)
    calls = []

    def request(method, path, **kwargs):
        calls.append((method, path, kwargs.get("json")))
        return response

    monkeypatch.setattr(page, "api_request", request)
    app = _app(module)
    next(control for control in app.button if control.label == button).click().run()
    assert not app.exception
    rendered = (
        [item.value for item in app.success]
        + [item.value for item in app.caption]
        + [item.value for item in app.markdown]
        + [item.value for item in app.warning]
    )
    assert "backend" in " ".join(rendered)
    assert calls and calls[0][1].endswith(f"/3661/{PERIOD}")
    if module == "ui.pages.ews":
        assert any("Liquidity" in text for text in rendered)


def test_agent_mode_and_full_response_history_replay(discovery_backend, monkeypatch):
    import ui.pages.agent as page

    class Health:
        status_code = 200

    response = AgentResponse(
        query="test",
        answer="backend answer",
        confidence="high",
        confidence_score=0.9,
        verdict="BUY",
        research_plan=["plan step"],
        findings=[{"finding": "full finding"}],
        data={"full_payload": "retained"},
        sources=["filing"],
        analysis_steps=["step"],
        watch_items=["watch"],
    )
    monkeypatch.setattr(page.httpx, "get", lambda *args, **kwargs: Health())
    monkeypatch.setattr(page, "query_agent_api", lambda query: response)
    app = _app("ui.pages.agent")
    next(box for box in app.selectbox if box.label == "Agent mode").set_value("quick")
    app.chat_input[0].set_value("test question").run()
    assert not app.exception
    assert "backend answer" in " ".join(item.value for item in app.markdown)
    assert any("retained" in str(item.value) for item in app.json)
    # A second rerun replays the stored AgentResponse, not only answer metadata.
    app.run()
    assert "backend answer" in " ".join(item.value for item in app.markdown)
