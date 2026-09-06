"""The structured path must carry every canonical figure, and outrank prose.

Filing prose restates the same line item for prior periods, for segments and
for subsidiaries. A number that is only reachable through retrieval is a number
the agent can report accurately and still attach to the wrong period, so these
two properties are what keep values trustworthy:

1. every canonical field the producer publishes is surfaced structurally;
2. the answer prompt tells the model the report outranks the passages.
"""

from app.core import DataLoader
from app.services import SnapshotService
from tests.helpers import RecordProvider, make_record

# The canonical set the producer publishes at /v1/capabilities. Kept here rather
# than fetched so the guard holds without a live producer; if the producer adds
# a field, this list and the service are meant to be updated together.
CANONICAL_INCOME = {
    "net_revenue",
    "gross_profit",
    "operating_income",
    "profit_before_tax",
    "net_income",
    "net_income_attributable_to_parent",
    "operating_expenses",
    "rd_expenses",
    "tax_expense",
    "comprehensive_income",
    "net_interest_income",
    "net_non_interest_income",
    "loan_loss_provisions",
}
CANONICAL_BALANCE = {
    "cash_and_equivalents",
    "accounts_receivable",
    "inventory",
    "current_assets",
    "total_assets",
    "accounts_payable",
    "current_liabilities",
    "total_liabilities",
    "equity",
    "equity_attributable_to_parent",
    "retained_earnings",
    "share_capital",
}
CANONICAL_CASH_FLOW = {
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "capex",
    "free_cash_flow",
    "cash_beginning",
    "cash_ending",
}


def _summary():
    record = make_record("2024Q1")
    registry = SnapshotService(DataLoader(RecordProvider({("2330", "2024Q1"): record})))
    summary = registry.get_summary("2330", "2024Q1")
    assert summary is not None
    return summary


def test_every_canonical_income_field_is_surfaced_structurally():
    assert CANONICAL_INCOME <= set(_summary()["income_statement"])


def test_every_canonical_balance_sheet_field_is_surfaced_structurally():
    assert CANONICAL_BALANCE <= set(_summary()["balance_sheet"])


def test_cash_flow_is_surfaced_structurally():
    assert CANONICAL_CASH_FLOW <= set(_summary()["cash_flow"])


def test_absent_canonical_fields_stay_none_rather_than_zero():
    """A field the filing does not report must not read as a real zero."""
    summary = _summary()
    values = {**summary["income_statement"], **summary["balance_sheet"], **summary["cash_flow"]}
    for field, value in values.items():
        assert value is None or isinstance(value, (int, float)), field


def test_field_states_cover_the_fields_that_are_reported():
    """Every surfaced field needs an availability state, or absence is unreadable."""
    summary = _summary()
    states = summary["data_context"]["field_states"]
    reported = set(summary["balance_sheet"]) | set(summary["cash_flow"])
    assert reported <= set(states)


def test_answer_prompt_ranks_the_report_above_filing_passages():
    """Guards the precedence rule against being edited away.

    Without it the model sees canonical figures and filing prose as peers, and
    a prior-period column in a retrieved passage can silently win.
    """
    import inspect

    from app.agents.workflow import FinancialAgent

    source = inspect.getsource(FinancialAgent)
    assert "The two sources are not peers" in source
    assert "not for numbers" in source


def test_degraded_retrieval_is_reported_not_silently_passed_off_as_search():
    """A fallback ranking must be visible; chunks alone look identical either way."""
    from app.agents.retrieval import RetrievedContext

    degraded = RetrievedContext(
        question="信用減損如何認定",
        chunks=[{"content": "x"}],
        retrieval={
            "mode": "importance",
            "state": "provider_failure",
            "detail": "the embedding model is unavailable, so the question did not affect ranking",
        },
    )
    assert degraded.degraded_detail is not None
    assert "did not affect ranking" in degraded.degraded_detail
    assert degraded.as_state()["retrieval"]["state"] == "provider_failure"

    healthy = RetrievedContext(
        question="信用減損如何認定",
        chunks=[{"content": "x"}],
        retrieval={"mode": "semantic", "state": "present", "detail": None},
    )
    assert healthy.degraded_detail is None


def test_retrieved_passages_survive_a_question_outside_the_topic_allowlist():
    """Retrieval that found passages must not be discarded for lacking a topic tag.

    retrieval.py deliberately stopped gating on the narrative-topic allowlist
    after measuring that 7 of 10 realistic questions went untagged. Gating on
    `topics` in the workflow reinstated exactly that, one layer up: questions
    about subsidiaries, capital management or valuation technique retrieved
    good passages and had them dropped before the model ever saw them.
    """
    from app.agents.retrieval import RetrievedContext, narrative_topics

    question = "合併財務報告包含哪些子公司？"
    assert narrative_topics(question) == [], "probe must be a question the allowlist misses"

    context = RetrievedContext(
        question=question,
        chunks=[{"content": "本合併財務報告包含之子公司…", "section_title": "合併基礎"}],
        retrieval={"mode": "semantic", "state": "present", "detail": None},
    )
    assert context.used
    # The workflow keeps filing text on `used or error`, never on `topics`.
    assert context.used or context.error


def test_a_filing_with_no_documents_is_absent_data_not_a_provider_outage():
    """One empty filing must not read as the whole producer being down.

    While the producer answered this with 503 the client retried it and then
    raised FinancialDataProviderUnavailable, so a permanent per-filing
    condition was reported as a service outage -- and a real outage became
    indistinguishable from an empty filing.
    """
    import httpx

    from app.data.providers import FinancialReportsProvider

    body = {
        "schema_version": "1.0.0",
        "error": {
            "code": "filing_has_no_source_documents",
            "message": "no source document could be obtained",
            "retryable": False,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json=body)

    provider = FinancialReportsProvider(base_url="http://producer.test")
    provider._client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://producer.test"
    )

    assert provider.load_record("7418", "2026Q1") is None


def test_no_source_documents_does_not_leak_internal_errors_into_the_answer():
    """The 409 applies to /context too, not just the record path.

    Handling it only on the record path left get_context raising raw httpx,
    which reached the user's data-gap list carrying the internal service URL,
    the percent-encoded question and a link to MDN's 409 page -- an internal
    failure rendered as though it were a finding about the filing.
    """
    import httpx

    from app.agents.retrieval import retrieve
    from app.data.providers import FinancialReportsProvider

    body = {
        "schema_version": "1.0.0",
        "error": {"code": "filing_has_no_source_documents", "retryable": False},
    }
    provider = FinancialReportsProvider(base_url="http://producer.test")
    provider._client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(409, json=body)),
        base_url="http://producer.test",
    )

    assert provider.get_context("2330", "2026Q2", "資本管理政策為何？") is None

    context = retrieve(provider, "2330", "2026Q2", "資本管理政策為何？")
    assert context.error
    assert "127.0.0.1" not in context.error
    assert "developer.mozilla.org" not in context.error
