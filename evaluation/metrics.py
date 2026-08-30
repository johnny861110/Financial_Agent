"""Measures over the evaluation set.

Scoped deliberately to what is decidable without an LLM: tool gating, citation
coverage, contradiction recall and verdict stability are all produced by
deterministic code, so they can be measured exactly and gated in CI.

Unsupported-claim rate is **not** here. It is a property of generated prose and
needs either a model or a human to judge, so measuring it would mean inventing
a proxy and then trusting the proxy. It is left to a Phase F follow-up that can
run against a real model, and its absence is stated rather than papered over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.tools import configure_tool_services
from app.agents.workflow import FinancialAgent
from app.core import DataLoader
from app.models.agent_models import AgentQuery
from evaluation.scenarios import PERIOD, STOCK, Scenario
from tests.helpers import RecordProvider


class EvaluationProvider(RecordProvider):
    """RecordProvider that can also serve filing text for narrative questions."""

    def __init__(self, records, chunks: list[dict[str, Any]] | None = None) -> None:
        super().__init__(records)
        self._chunks = chunks or []

    def get_context(
        self,
        stock_code: str,
        period: str,
        question: str | None = None,
        *,
        sections: list[str] | None = None,
        evidence_limit: int = 50,
    ) -> dict[str, Any] | None:
        if not self._chunks:
            return None
        return {"evidence_chunks": self._chunks[:evidence_limit]}


@dataclass
class ScenarioResult:
    scenario: str
    verdict: str | None
    confidence: float
    blocked: set[str] = field(default_factory=set)
    ran: set[str] = field(default_factory=set)
    contradictions: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    findings: int = 0


def run_scenario(scenario: Scenario) -> ScenarioResult:
    """Execute one scenario through the real agent workflow."""
    records = {}
    if scenario.record is not None:
        records[(STOCK, PERIOD)] = scenario.record
    for period, record in scenario.history.items():
        records[(STOCK, period)] = record

    provider = EvaluationProvider(records, scenario.chunks)
    loader = DataLoader(provider)
    agent = FinancialAgent()
    agent.data_loader = loader
    configure_tool_services(loader)

    response = agent.query(
        AgentQuery(query=scenario.query, stock_code=STOCK, period=PERIOD, mode="research")
    )

    tools = response.data.get("tools", {})
    blocked = {
        name
        for name, result in tools.items()
        if isinstance(result, dict) and (result.get("blocked_fields") or result.get("failed_rules"))
    }
    ran = {
        name
        for name, result in tools.items()
        if isinstance(result, dict) and result.get("status") == "success"
    }
    citations = [
        item
        for item in response.evidence
        if isinstance(item, dict) and item.get("source_type") == "filing_text"
    ]

    return ScenarioResult(
        scenario=scenario.name,
        verdict=response.verdict,
        confidence=response.confidence_score,
        blocked=blocked,
        ran=ran,
        contradictions=response.contradictions,
        citations=citations,
        findings=len(response.findings),
    )


def gating_accuracy(scenarios: list[Scenario], results: list[ScenarioResult]) -> float:
    """Fraction of gating expectations the planner got right.

    Counts both directions: a tool that should have been blocked and was not is
    as wrong as a tool that should have run and did not.
    """
    correct = total = 0
    for scenario, result in zip(scenarios, results):
        for tool in scenario.expect_blocked:
            total += 1
            correct += tool in result.blocked
        for tool in scenario.expect_ran:
            total += 1
            correct += tool in result.ran
    return correct / total if total else 1.0


def citation_coverage(results: list[ScenarioResult], narrative_names: set[str]) -> float:
    """Fraction of narrative answers carrying at least one locatable citation.

    A citation counts only if it can actually be followed or located: it needs
    a source URL or a page, not just a database id.

    This measures well-formedness, not correctness -- it cannot tell whether a
    page number points at the text it claims to. That gap is not theoretical:
    the producer attributed every chunk in a section to the section's first
    page, so a filing's citations were uniformly wrong while this metric read
    100%. Judging a page is right needs the source document, which the fixed
    scenarios deliberately do not carry; it belongs to the producer, which now
    tests page attribution directly.
    """
    narrative = [r for r in results if r.scenario in narrative_names]
    if not narrative:
        return 1.0
    cited = 0
    for result in narrative:
        usable = [
            c for c in result.citations if c.get("source_url") or c.get("page_number") is not None
        ]
        cited += bool(usable)
    return cited / len(narrative)


def contradiction_recall(scenarios: list[Scenario], results: list[ScenarioResult]) -> float:
    """Fraction of planted contradictions that were detected."""
    expected = [(s, r) for s, r in zip(scenarios, results) if s.expect_contradiction]
    if not expected:
        return 1.0
    return sum(bool(r.contradictions) for _, r in expected) / len(expected)


def verdict_stability(scenario: Scenario, runs: int = 3) -> bool:
    """The same filing must produce the same verdict every time.

    Instability here would mean the deterministic path is not deterministic,
    which undermines every other measure.
    """
    verdicts = {run_scenario(scenario).verdict for _ in range(runs)}
    return len(verdicts) == 1


@dataclass
class Report:
    gating_accuracy: float
    citation_coverage: float
    contradiction_recall: float
    results: list[ScenarioResult]

    def as_lines(self) -> list[str]:
        lines = [
            f"gating accuracy      {self.gating_accuracy:6.1%}",
            f"citation coverage    {self.citation_coverage:6.1%}",
            f"contradiction recall {self.contradiction_recall:6.1%}",
            "",
            f"{'scenario':<16}{'verdict':<10}{'conf':>6}  {'ran':<28}blocked",
        ]
        for result in self.results:
            lines.append(
                f"{result.scenario:<16}{str(result.verdict or '-'):<10}"
                f"{result.confidence:6.2f}  {','.join(sorted(result.ran)) or '-':<28}"
                f"{','.join(sorted(result.blocked)) or '-'}"
            )
        return lines


def evaluate(scenarios: list[Scenario] | None = None) -> Report:
    from evaluation.scenarios import all_scenarios

    scenarios = scenarios or all_scenarios()
    results = [run_scenario(s) for s in scenarios]
    narrative_names = {s.name for s in scenarios if s.narrative}
    return Report(
        gating_accuracy=gating_accuracy(scenarios, results),
        citation_coverage=citation_coverage(results, narrative_names),
        contradiction_recall=contradiction_recall(scenarios, results),
        results=results,
    )
