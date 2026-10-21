"""Tests for resolving company names in a question to stock codes.

Users ask about 台積電, not 2330. The producer's /v1/stocks carries each
company's Chinese short name; the intent router uses it the way it uses a
ticker typed into the question.
"""

from types import SimpleNamespace

import httpx

from app.agents.workflow import FinancialAgent, _codes_named_in
from app.data.providers import FinancialReportsProvider

NAMES = {"2330": "台積電", "2454": "聯發科", "3661": "世芯-KY", "2881": "富邦金"}


def test_codes_named_in_finds_a_company_name():
    assert _codes_named_in("台積電 2025Q4 獲利品質如何?", NAMES) == ["2330"]


def test_codes_named_in_keeps_question_order_for_peers():
    assert _codes_named_in("比較聯發科和台積電的毛利率", NAMES) == ["2454", "2330"]


def test_codes_named_in_accepts_a_name_without_its_listing_suffix():
    assert _codes_named_in("世芯 2026Q1 營收", NAMES) == ["3661"]
    assert _codes_named_in("世芯-KY 2026Q1 營收", NAMES) == ["3661"]


def test_codes_named_in_prefers_the_longer_name_at_one_position():
    names = {"1111": "富邦", "2881": "富邦金"}
    assert _codes_named_in("富邦金的資本配置", names) == ["2881"]


def test_codes_named_in_finds_nothing_in_an_unrelated_question():
    assert _codes_named_in("半導體產業的趨勢", NAMES) == []


def _provider_serving(items: list[dict]) -> tuple[FinancialReportsProvider, list[str]]:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert request.url.path == "/v1/stocks"
        return httpx.Response(
            200,
            json={
                "schema_version": "1.0.0",
                "items": items,
                "stocks": items,
                "pagination": {"limit": 100, "offset": 0, "total": len(items)},
            },
        )

    client = httpx.Client(
        base_url="http://financial-reports.test", transport=httpx.MockTransport(handler)
    )
    provider = FinancialReportsProvider(
        "http://financial-reports.test", max_retries=0, client=client
    )
    return provider, calls


def test_provider_company_names_skips_unnamed_and_placeholder_rows():
    provider, _ = _provider_serving(
        [
            {"stock_code": "2330", "name_zh": "台積電"},
            {"stock_code": "7418", "name_zh": None},
            # A stock code stored as its own name, as the producer once did.
            {"stock_code": "2454", "name_zh": "2454"},
        ]
    )

    assert provider.company_names() == {"2330": "台積電"}


def test_provider_company_names_are_cached():
    provider, calls = _provider_serving([{"stock_code": "2330", "name_zh": "台積電"}])

    provider.company_names()
    provider.company_names()

    assert calls == ["/v1/stocks"]


def test_provider_list_all_stocks_still_returns_codes():
    provider, _ = _provider_serving(
        [{"stock_code": "2454", "name_zh": "聯發科"}, {"stock_code": "2330", "name_zh": "台積電"}]
    )

    assert provider.list_all_stocks() == ["2330", "2454"]


class _NamesProvider:
    def __init__(self, names: dict[str, str] | Exception) -> None:
        self.names = names

    def company_names(self) -> dict[str, str]:
        if isinstance(self.names, Exception):
            raise self.names
        return self.names


def _agent_with(names: dict[str, str] | Exception) -> FinancialAgent:
    agent = FinancialAgent.__new__(FinancialAgent)
    agent.data_loader = SimpleNamespace(provider=_NamesProvider(names))
    agent.settings = SimpleNamespace(openai_api_key="")
    return agent


def test_router_resolves_a_company_name_without_an_llm():
    agent = _agent_with(NAMES)
    state = {"query": "台積電 2025Q4 獲利品質如何?", "stock_code": "9999", "period": "2025Q1"}

    FinancialAgent._intent_router_node(agent, state)

    assert state["stock_code"] == "2330"
    assert state["period"] == "2025Q4"


def test_router_resolves_named_peers():
    agent = _agent_with(NAMES)
    state = {"query": "比較台積電和聯發科 2025Q4", "stock_code": "9999", "period": "2025Q4"}

    FinancialAgent._intent_router_node(agent, state)

    assert state["stock_code"] == "2330"
    assert state["entities"]["peer_stocks"] == ["2330", "2454"]


def test_router_prefers_a_typed_ticker_over_a_name():
    agent = _agent_with(NAMES)
    state = {"query": "2454 台積電 2025Q4", "stock_code": "9999", "period": "2025Q4"}

    FinancialAgent._intent_router_node(agent, state)

    assert state["stock_code"] == "2454"


def test_router_survives_an_unavailable_name_directory():
    agent = _agent_with(RuntimeError("FinancialReports is unavailable"))
    state = {"query": "台積電 2025Q4", "stock_code": "2330", "period": "2025Q1"}

    FinancialAgent._intent_router_node(agent, state)

    assert state["stock_code"] == "2330"
    assert state["period"] == "2025Q4"


def test_apply_entities_replaces_llm_peer_names_with_resolved_codes():
    agent = FinancialAgent.__new__(FinancialAgent)
    state = {"period": "2025Q4", "stock_code": "2330", "entities": {}}

    FinancialAgent._apply_entities(
        agent,
        state,
        {"stock_code": "台積電", "peer_stocks": ["台積電", "聯發科"]},
        {"stock_code": "2330", "peer_stocks": ["2330", "2454"]},
    )

    assert state["entities"]["peer_stocks"] == ["2330", "2454"]
    assert state["entities"]["peer_stocks_raw"] == ["台積電", "聯發科"]


def test_apply_entities_uses_the_resolved_code_when_the_llm_omits_stock_code():
    """The LLM may put companies under stock_code_1/stock_code_2 instead."""
    agent = FinancialAgent.__new__(FinancialAgent)
    state = {"period": "2025Q4", "stock_code": "9999", "entities": {}}

    FinancialAgent._apply_entities(
        agent,
        state,
        {"stock_code_1": "聯發科", "stock_code_2": "台積電"},
        {"stock_code": "2454", "peer_stocks": ["2454", "2330"]},
    )

    assert state["stock_code"] == "2454"
    assert state["entities"]["peer_stocks"] == ["2454", "2330"]
