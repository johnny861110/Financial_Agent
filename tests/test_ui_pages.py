"""Tests that the Streamlit pages render what they claim to.

The page under repair had a "Data Source" selectbox that was never read and a
period pinned to 2025Q1 in code. Neither shows up in an import check or an API
test -- only in what the page actually puts on screen -- so these run the pages
headlessly through Streamlit's own AppTest harness.
"""

import pytest

from streamlit.testing.v1 import AppTest


PERIODS = ["2026Q1", "2025Q4", "2025Q1"]
CAPABILITIES = {"schema_version": "1.0.0", "api_version": "v1"}


@pytest.fixture
def fake_backend(monkeypatch):
    """Answer the discovery calls the sidebar makes, without a running API."""
    import ui.data_source as data_source

    def fake_request(method, path, **kwargs):
        if path.endswith("/capabilities"):
            return dict(CAPABILITIES)
        if path.endswith("/stocks"):
            return {"stocks": ["2330", "3661"]}
        if path.endswith("/periods"):
            return {"stock_code": "3661", "periods": list(PERIODS)}
        raise AssertionError(f"unexpected call: {method} {path}")

    # st.cache_data memoizes across tests; clear so each case sees this stub.
    data_source.clear_cache()
    monkeypatch.setattr(data_source, "api_request", fake_request)
    yield
    data_source.clear_cache()


def run_page(module: str) -> AppTest:
    app = AppTest.from_string(f"import {module} as page; page.show()", default_timeout=30)
    app.run()
    return app


def test_agent_page_offers_real_periods_instead_of_a_hardcoded_one(fake_backend):
    app = run_page("ui.pages.agent")

    assert not app.exception
    periods = [box for box in app.selectbox if box.label == "Period"]
    assert periods, "the agent page must offer a period selector"
    assert list(periods[0].options) == PERIODS
    assert periods[0].value == "2026Q1", "the newest period should be preselected"


def test_agent_page_has_no_data_source_picker(fake_backend):
    """The provider is server-side config; a picker here only misleads."""
    app = run_page("ui.pages.agent")

    labels = [box.label for box in app.selectbox]
    assert "Source" not in labels
    assert not any("CSV Upload" in str(box.options) for box in app.selectbox)


def test_agent_page_reports_the_live_data_source(fake_backend):
    app = run_page("ui.pages.agent")

    rendered = " ".join(el.value for el in app.success)
    assert "FinancialReports API v1" in rendered
    assert "1.0.0" in rendered


def test_agent_page_warns_when_the_backend_serves_local_json(fake_backend, monkeypatch):
    import ui.data_source as data_source

    data_source.clear_cache()
    monkeypatch.setattr(
        data_source,
        "api_request",
        lambda method, path, **kw: (
            {"schema_version": "legacy-json", "api_version": None, "source": "json"}
            if path.endswith("/capabilities")
            else {"stocks": [], "periods": list(PERIODS), "stock_code": "3661"}
        ),
    )

    app = run_page("ui.pages.agent")

    assert "Local JSON" in " ".join(el.value for el in app.warning)


def test_snapshot_page_offers_the_periods_the_backend_can_serve(fake_backend):
    app = run_page("ui.pages.snapshot")

    assert not app.exception
    periods = [box for box in app.selectbox if box.label == "Period"]
    assert periods and list(periods[0].options) == PERIODS


def test_pages_surface_an_unreachable_backend_instead_of_a_blank_picker(monkeypatch):
    """A dead API must be visible on the page, not silently absent."""
    import httpx

    import ui.data_source as data_source

    data_source.clear_cache()

    def refuse(method, path, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(data_source, "api_request", refuse)

    app = run_page("ui.pages.agent")

    assert not app.exception
    assert any("unreachable" in el.value for el in app.error)
    data_source.clear_cache()
