"""Field-state-aware tests for PeerService.

PeerService never raised InsufficientDataError -- it silently skipped a
company missing from the provider entirely. The canonical-context migration
extends that same "skip, don't fabricate" principle to the metric level: a
company missing one metric's inputs is excluded from that metric's
comparison specifically, instead of contributing a fabricated 0% (the
previous behavior for FinancialSnapshot's computed properties).
"""

import inspect

from app.agents.tools import configure_tool_services, tool_peer_compare
from app.agents.workflow import FinancialAgent, _composer_report_view
from app.core import DataLoader
from app.services import PeerService
from tests.helpers import RecordProvider, make_record

TSMC = dict(
    net_revenue=1000.0,
    gross_profit=500.0,  # 50% gross margin
    operating_income=300.0,  # 30% operating margin
    net_income=200.0,
    equity=2000.0,
    total_assets=5000.0,
    total_liabilities=2000.0,
    current_assets=1000.0,
    current_liabilities=500.0,  # current ratio 2.0
)

MEDIATEK = dict(
    net_revenue=800.0,
    gross_profit=320.0,  # 40% gross margin
    operating_income=160.0,  # 20% operating margin
    net_income=80.0,
    equity=1000.0,
    total_assets=3000.0,
    total_liabilities=1500.0,
    current_assets=600.0,
    current_liabilities=300.0,  # current ratio 2.0
)

FORMOSA_INCOMPLETE = dict(
    net_revenue=1200.0,
    gross_profit=None,  # missing: excluded from gross-margin comparison only
    operating_income=100.0,
    net_income=50.0,
    equity=3000.0,
    total_assets=6000.0,
    total_liabilities=4000.0,
    current_assets=None,  # missing: excluded from current-ratio comparison
    current_liabilities=None,
)


def _provider():
    return RecordProvider(
        {
            ("2330", "2025Q1"): make_record(
                "2025Q1", stock_code="2330", company_name="TSMC", snapshot_overrides=TSMC
            ),
            ("2454", "2025Q1"): make_record(
                "2025Q1", stock_code="2454", company_name="MediaTek", snapshot_overrides=MEDIATEK
            ),
            ("1301", "2025Q1"): make_record(
                "2025Q1",
                stock_code="1301",
                company_name="Formosa",
                snapshot_overrides=FORMOSA_INCOMPLETE,
            ),
        }
    )


def test_compare_peers_excludes_company_missing_one_metrics_inputs():
    service = PeerService(DataLoader(_provider()))

    analysis = service.compare_peers(["2330", "2454", "1301"], "2025Q1")

    assert analysis is not None
    gross_margin = next(c for c in analysis.comparisons if c.metric_name == "Gross Margin (%)")
    assert set(gross_margin.companies) == {"TSMC", "MediaTek"}
    assert gross_margin.best_performer == "TSMC"

    operating_margin = next(
        c for c in analysis.comparisons if c.metric_name == "Operating Margin (%)"
    )
    assert set(operating_margin.companies) == {"TSMC", "MediaTek", "Formosa"}


def test_compare_peers_returns_none_with_fewer_than_two_companies():
    service = PeerService(DataLoader(_provider()))

    analysis = service.compare_peers(["2330", "9999"], "2025Q1")

    assert analysis is None


def test_compare_peers_current_ratio_excludes_missing_company():
    service = PeerService(DataLoader(_provider()))

    analysis = service.compare_peers(["2330", "2454", "1301"], "2025Q1", metrics=["Current Ratio"])

    assert analysis is not None
    assert len(analysis.comparisons) == 1
    current_ratio = analysis.comparisons[0]
    assert set(current_ratio.companies) == {"TSMC", "MediaTek"}


def test_summary_names_the_real_leader_when_companies_have_names():
    """
    Comparisons carry company names; the summary used to match them against
    stock codes as text, so with real names every count was zero and the first
    peer listed was declared the leader.
    """
    service = PeerService(DataLoader(_provider()))

    analysis = service.compare_peers(["2454", "2330"], "2025Q1")

    assert analysis is not None
    assert analysis.summary.startswith("Overall leader: 2330 ")


def test_summary_claims_no_leader_when_no_metric_resolves_to_a_peer():
    service = PeerService(DataLoader(_provider()))
    analysis = service.compare_peers(["2454", "2330"], "2025Q1")
    assert analysis is not None
    for comparison in analysis.comparisons:
        comparison.companies = ["Unknown A", "Unknown B"]

    contexts = [service.data_loader.load_context(code, "2025Q1") for code in ["2454", "2330"]]
    summary = service._generate_summary(analysis.comparisons, contexts)

    assert summary == "Peer comparison completed"


def test_summary_names_the_leader_by_code_and_name():
    """The comparison rows name companies; a bare code could not be tied to them."""
    service = PeerService(DataLoader(_provider()))

    analysis = service.compare_peers(["2454", "2330"], "2025Q1")

    assert analysis is not None
    assert analysis.summary.startswith("Overall leader: 2330 TSMC (")


def test_peer_tool_reports_every_company_as_evidence(monkeypatch):
    """
    The tool used to return no evidence, so the executor filled in the primary
    company's figures and the answer to "比較聯發科和台積電" described 聯發科 alone.
    """
    # monkeypatch restores the shared registry, so no other test sees this one.
    monkeypatch.setattr("app.agents.tools._service_registry", None)
    configure_tool_services(DataLoader(_provider()))

    result = tool_peer_compare.invoke({"stock_codes": "2454,2330", "period": "2025Q1"})

    rows = [row for row in result["evidence"] if row["field"] == "Gross Margin (%)"]
    assert {row["company"] for row in rows} == {"TSMC", "MediaTek"}
    assert all(row["source_type"] == "peer_comparison" for row in rows)
    assert next(row for row in rows if row["company"] == "TSMC")["rank"] == 1


def test_composer_keeps_peer_rows_when_the_evidence_budget_runs_out():
    filler = [
        {"field": f"field_{i}", "value": i, "unit": "TWD_thousands", "source_type": "finmind"}
        for i in range(2000)
    ]
    peer = {
        "field": "Gross Margin (%)",
        "company": "TSMC",
        "value": 50.0,
        "unit": "percent",
        "rank": 1,
        "source_type": "peer_comparison",
    }

    view = _composer_report_view({"findings": [], "supporting_evidence": filler + [peer]})

    assert view["supporting_evidence_omitted"] > 0
    assert view["supporting_evidence"][0]["company"] == "TSMC"
    assert view["supporting_evidence"][0]["rank"] == 1


def test_composer_prompt_asks_for_every_compared_company():
    source = inspect.getsource(FinancialAgent._answer_composer_node)

    assert "answer it for every company in them" in source
