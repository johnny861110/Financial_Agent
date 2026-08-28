"""Intent-gated, bounded retrieval of filing narrative text."""

from typing import Any

import pytest

from app.agents.retrieval import (
    MAX_CHUNKS,
    MAX_TOTAL_CHARS,
    RetrievedContext,
    bound_chunks,
    citation,
    narrative_topics,
    retrieve,
)


def _chunk(chunk_id: int, content: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "chunk_id": chunk_id,
        "doc_id": 1,
        "page_number": 42,
        "section_type": "risk",
        "section_title": "風險因素",
        "content": content,
        "source_url": "https://example.com/f.pdf",
        "checksum": "abc123",
        "retrieval_score": 0.7,
    }
    payload.update(extra)
    return payload


class RecordingProvider:
    """Captures the retrieval arguments so the gate can be asserted."""

    def __init__(self, chunks: list[dict[str, Any]] | None = None, payload: Any = ...) -> None:
        self.calls: list[dict[str, Any]] = []
        self._chunks = chunks if chunks is not None else [_chunk(1, "風險說明")]
        self._payload = payload

    def get_context(self, stock_code, period, question=None, *, sections=None, evidence_limit=50):
        self.calls.append(
            {
                "stock_code": stock_code,
                "period": period,
                "question": question,
                "sections": sections,
                "evidence_limit": evidence_limit,
            }
        )
        if self._payload is not ...:
            return self._payload
        return {"evidence_chunks": self._chunks}


@pytest.mark.parametrize(
    "query,expected",
    [
        ("公司面臨哪些風險", ["risk"]),
        ("會計政策有什麼變更", ["accounting_policy"]),
        ("會計師出具什麼意見", ["auditor"]),
        ("會計政策與會計師意見", ["accounting_policy", "auditor"]),
        ("有哪些重大事項揭露", ["notes"]),
        ("what are the main risks", ["risk"]),
    ],
)
def test_narrative_questions_are_recognised(query, expected):
    assert narrative_topics(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "2330 的營收是多少",
        "毛利率趨勢如何",
        "ROIC 和 WACC 的差距",
        "跟同業比較 EPS",
    ],
)
def test_numeric_questions_do_not_trigger_retrieval(query):
    """Numeric questions must stay on the structured-fact path."""
    assert narrative_topics(query) == []

    provider = RecordingProvider()
    context = retrieve(provider, "2330", "2025Q1", query)

    assert provider.calls == [], "a numeric question must not call the provider"
    assert not context.used
    assert context.error is None


def test_narrative_question_requests_only_relevant_sections():
    provider = RecordingProvider()

    context = retrieve(provider, "2330", "2025Q1", "公司面臨哪些風險")

    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["question"] == "公司面臨哪些風險"
    assert call["sections"] == ["risk"]
    # Numeric sections are never requested: the fact path answers those better.
    assert "income_statement" not in (call["sections"] or [])
    assert context.used


def test_chunk_count_is_bounded():
    chunks = [_chunk(i, "短內容") for i in range(MAX_CHUNKS + 5)]

    assert len(bound_chunks(chunks)) == MAX_CHUNKS


def test_total_characters_are_bounded():
    """Chunk count alone is not enough: total prompt size must also be capped."""
    big = "字" * (MAX_TOTAL_CHARS // 2)
    chunks = [_chunk(i, big) for i in range(MAX_CHUNKS)]

    bounded = bound_chunks(chunks)

    assert sum(len(c["content"]) for c in bounded) <= MAX_TOTAL_CHARS
    assert len(bounded) < len(chunks)


def test_retrieval_failure_degrades_to_a_data_gap():
    class Failing:
        def get_context(self, *args, **kwargs):
            raise RuntimeError("producer unreachable")

    context = retrieve(Failing(), "2330", "2025Q1", "公司面臨哪些風險")

    assert not context.used
    assert context.error is not None
    assert "producer unreachable" in context.error


def test_provider_without_retrieval_support_degrades():
    class Legacy:
        def get_context(self, stock_code, period, question=None):
            raise TypeError("unexpected keyword argument 'sections'")

    context = retrieve(Legacy(), "2330", "2025Q1", "公司面臨哪些風險")

    assert not context.used
    assert "does not support question retrieval" in context.error


def test_missing_context_is_reported_not_silently_empty():
    context = retrieve(RecordingProvider(payload=None), "2330", "2025Q1", "公司面臨哪些風險")

    assert not context.used
    assert context.error == "No filing context is available for this period"


def test_empty_chunks_are_reported():
    context = retrieve(RecordingProvider(chunks=[]), "2330", "2025Q1", "公司面臨哪些風險")

    assert not context.used
    assert context.error == "No filing text matched this question"


def test_citation_names_section_page_and_chunk():
    assert citation(_chunk(7, "x")) == "風險因素 · p.42 · chunk 7"


def test_citation_survives_missing_metadata():
    assert citation({"content": "x"}) == "filing"


def test_state_payload_is_serialisable():
    context = RetrievedContext(question="q", topics=["risk"], sections=["risk"])
    context.chunks = [_chunk(1, "內容")]

    state = context.as_state()

    assert state["chunk_count"] == 1
    assert state["sections"] == ["risk"]
    assert state["chunks"][0]["chunk_id"] == 1


def test_narrative_question_produces_cited_evidence_end_to_end(tmp_path):
    """A narrative question must surface filing text as citable report evidence."""
    import json

    from app.agents.tools import configure_tool_services
    from app.agents.workflow import FinancialAgent
    from app.core import DataLoader
    from app.data import JsonFinancialDataProvider
    from app.models.agent_models import AgentQuery

    for index, period in enumerate(["2024Q4", "2025Q1"]):
        (tmp_path / f"2330_{period}_enhanced.json").write_text(
            json.dumps(
                {
                    "stock_code": "2330",
                    "company_name": "T",
                    "report_year": int(period[:4]),
                    "report_season": int(period[-1]),
                    "report_period": period,
                    "cash_and_equivalents": 900 + index,
                    "accounts_receivable": 180 + index,
                    "inventory": 150 + index,
                    "total_assets": 5000 + index,
                    "total_liabilities": 2000 + index,
                    "equity": 3000 + index,
                    "net_revenue": 1000 + index,
                    "gross_profit": 400 + index,
                    "operating_income": 250 + index,
                    "net_income": 200 + index,
                    "eps": 2.0,
                    "operating_cash_flow": 220 + index,
                }
            ),
            encoding="utf-8",
        )

    provider = JsonFinancialDataProvider(tmp_path)
    # The JSON provider has no filing text, so stand in for a producer that does.
    provider.get_context = lambda *a, **k: {  # type: ignore[method-assign]
        "evidence_chunks": [_chunk(11, "本公司之利率風險主要來自投資部位")]
    }

    loader = DataLoader(provider)
    agent = FinancialAgent()
    agent.data_loader = loader
    configure_tool_services(loader)

    response = agent.query(
        AgentQuery(
            query="2330 公司面臨哪些風險",
            stock_code="2330",
            period="2025Q1",
            mode="quick",
        )
    )

    filing_evidence = [
        item for item in response.evidence if item.get("source_type") == "filing_text"
    ]
    assert filing_evidence, "retrieved filing text must appear as report evidence"
    cited = filing_evidence[0]
    assert cited["chunk_id"] == 11
    assert cited["citation"] == "風險因素 · p.42 · chunk 11"
    assert cited["source_url"] == "https://example.com/f.pdf"
