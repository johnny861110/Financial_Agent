"""Display logic for citations, field states, blocked tools and pipeline state."""

from ui.presentation import (
    FIELD_STATE_DISPLAY,
    blocked_tools,
    citation_for,
    group_field_states,
    pipeline_view,
    split_data_gaps,
    split_evidence,
)


def _chunk(**overrides):
    payload = {
        "source_type": "filing_text",
        "chunk_id": 11,
        "doc_id": 2,
        "page_number": 43,
        "section_title": "風險因素",
        "section_type": "risk",
        "source_url": "https://example.com/f.pdf",
        "checksum": "abc123def456789",
        "excerpt": "利率風險說明",
        "retrieval_score": 0.688,
    }
    payload.update(overrides)
    return payload


def test_citation_prefers_a_followable_url():
    citation = citation_for(_chunk())

    assert citation.url == "https://example.com/f.pdf"
    assert citation.is_linkable
    assert citation.label == "風險因素 · p.43"
    assert citation.score == 0.688


def test_database_ids_are_a_detail_not_the_citation():
    """A chunk id means nothing to a reader; the document URL is the citation."""
    citation = citation_for(_chunk())

    assert "chunk 11" not in citation.label
    assert "doc 2" not in citation.label
    assert "chunk 11" in citation.detail
    assert "doc 2" in citation.detail


def test_citation_degrades_when_no_url_exists():
    citation = citation_for(_chunk(source_url=None))

    assert citation.url is None
    assert not citation.is_linkable
    # Still identifies where in the filing the text came from.
    assert citation.label == "風險因素 · p.43"


def test_citation_never_surfaces_a_local_path():
    citation = citation_for(_chunk(local_path="/internal/secret/path.pdf"))

    rendered = f"{citation.label} {citation.url} {citation.detail}"
    assert "/internal/secret" not in rendered


def test_citation_survives_missing_metadata():
    citation = citation_for({"content": "text"})

    assert citation.label == "Filing text"
    assert citation.detail is None


def test_evidence_splits_filing_text_from_structured_facts():
    evidence = [
        _chunk(),
        {"source_type": "xbrl", "field": "net_revenue", "value": 100.0},
    ]

    citations, structured = split_evidence(evidence)

    assert len(citations) == 1
    assert len(structured) == 1
    assert structured[0]["field"] == "net_revenue"


def test_field_states_group_by_state_with_absences_first():
    groups = group_field_states(
        {
            "net_revenue": "present",
            "inventory": "not_applicable",
            "operating_cash_flow": "missing",
            "equity": "provider_failure",
        }
    )

    assert [g.state for g in groups] == [
        "provider_failure",
        "missing",
        "not_applicable",
        "present",
    ]


def test_missing_and_not_applicable_read_differently():
    """The distinction the whole canonical-context migration exists to preserve."""
    assert FIELD_STATE_DISPLAY["missing"][1] != FIELD_STATE_DISPLAY["not_applicable"][1]
    assert "not applicable" in FIELD_STATE_DISPLAY["not_applicable"][1].lower()
    assert "missing" in FIELD_STATE_DISPLAY["missing"][1].lower()


def test_unknown_state_does_not_crash_rendering():
    groups = group_field_states({"weird": "something_new"})

    assert groups[0].icon == "❓"


def test_blocked_tools_explain_each_field_and_rule():
    results = {
        "ews": {
            "status": "insufficient_data",
            "finding": "ews was not run",
            "blocked_fields": {"cash_and_equivalents": "missing"},
            "failed_rules": ["balance_sheet_equation"],
        },
        "snapshot": {"status": "success", "blocked_fields": {}, "failed_rules": []},
    }

    blocked = blocked_tools(results)

    assert [b.tool for b in blocked] == ["ews"]
    reasons = blocked[0].reasons()
    assert "cash_and_equivalents: missing from the filing" in reasons
    assert "validation failed: balance_sheet_equation" in reasons


def test_successful_tools_are_not_reported_as_blocked():
    assert blocked_tools({"snapshot": {"status": "success"}}) == []


def test_validation_failures_separate_from_ordinary_gaps():
    validation, ordinary = split_data_gaps(
        [
            "Validation failed: balance_sheet_equation",
            "operating_cash_flow",
            "filing_text: No filing text matched this question",
        ]
    )

    assert validation == ["Validation failed: balance_sheet_equation"]
    assert len(ordinary) == 2


def test_pipeline_view_names_the_failed_stage():
    view = pipeline_view(
        {"status": "stale"},
        {
            "pipeline_state": [
                {"stage": "ingest", "status": "completed"},
                {"stage": "extract", "status": "failed"},
            ]
        },
    )

    assert view.status == "stale"
    assert view.failed_stage == "extract"
    assert view.has_failure
    assert ("ingest", "completed") in view.stage_states


def test_pipeline_view_without_failures():
    view = pipeline_view(
        {"status": "ready"}, {"pipeline_state": [{"stage": "ingest", "status": "completed"}]}
    )

    assert not view.has_failure
    assert view.failed_stage is None


def test_pipeline_view_tolerates_absent_record():
    view = pipeline_view({"status": "missing"}, None)

    assert view.status == "missing"
    assert view.stage_states == []


def test_field_states_reach_the_agent_response(tmp_path):
    """The UI reads readiness.field_states, so the response must carry it."""
    import json

    from app.agents.tools import configure_tool_services
    from app.agents.workflow import FinancialAgent
    from app.core import DataLoader
    from app.data import JsonFinancialDataProvider
    from app.models.agent_models import AgentQuery

    payload = {
        "stock_code": "2330",
        "company_name": "T",
        "report_year": 2025,
        "report_season": 1,
        "report_period": "2025Q1",
        "total_assets": 5000.0,
        "total_liabilities": 2000.0,
        "equity": 3000.0,
        "net_revenue": 1000.0,
        "operating_income": 250.0,
        "net_income": 200.0,
        "accounts_receivable": 180.0,
        "inventory": 150.0,
        "eps": 2.0,
        # cash_and_equivalents deliberately absent -> ews must be blocked
    }
    (tmp_path / "2330_2025Q1_enhanced.json").write_text(json.dumps(payload), encoding="utf-8")

    loader = DataLoader(JsonFinancialDataProvider(tmp_path))
    agent = FinancialAgent()
    agent.data_loader = loader
    configure_tool_services(loader)

    response = agent.query(
        AgentQuery(query="有沒有預警訊號", stock_code="2330", period="2025Q1", mode="quick")
    )

    states = response.data["data_readiness"]["field_states"]
    assert states["cash_and_equivalents"] == "missing"
    assert states["net_revenue"] == "present"

    # And the blocked tool is renderable from the same response.
    blocked = blocked_tools(response.data["tools"])
    assert [b.tool for b in blocked] == ["ews"]
    assert "cash_and_equivalents: missing from the filing" in blocked[0].reasons()
