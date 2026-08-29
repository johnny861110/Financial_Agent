"""A fixed evaluation set of filing states.

Every other test asks whether one behaviour is correct. This asks whether the
system as a whole still behaves acceptably across the range of filings it will
actually meet: complete, partially reported, stale, failing validation, still
processing, and narrative-heavy.

The set is deliberately fixed and hand-built rather than sampled from the live
corpus, so a regression shows up as a metric moving rather than as the data
having changed underneath it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.data import (
    DataFreshness,
    DataQuality,
    FieldAvailability,
    SnapshotRecord,
    ValidationRecord,
)
from tests.helpers import make_record

# Fields every gated tool needs; scenarios vary which of them are available.
FULL_SNAPSHOT: dict[str, Any] = {
    "net_revenue": 1000.0,
    "gross_profit": 400.0,
    "operating_income": 250.0,
    "net_income": 200.0,
    "total_assets": 5000.0,
    "total_liabilities": 2000.0,
    "equity": 3000.0,
    "cash_and_equivalents": 800.0,
    "accounts_receivable": 300.0,
    "inventory": 250.0,
    "operating_cash_flow": 220.0,
    "eps": 2.0,
}

STOCK = "2330"
PERIOD = "2025Q1"


@dataclass
class Scenario:
    """One filing state, with what the system is expected to do about it."""

    name: str
    description: str
    record: SnapshotRecord | None
    # Earlier periods, when the scenario needs multi-period analysis. Trend and
    # the historical half of earnings quality are inert without them.
    history: dict[str, SnapshotRecord] = field(default_factory=dict)
    query: str = "請完整分析這家公司"
    # Tools the planner must refuse to run, given this filing's field states.
    expect_blocked: set[str] = field(default_factory=set)
    # Tools that must still produce a finding.
    expect_ran: set[str] = field(default_factory=set)
    expect_contradiction: bool = False
    # Filing text the stub producer should return for a narrative question.
    chunks: list[dict[str, Any]] = field(default_factory=list)
    narrative: bool = False


def _chunk(chunk_id: int, content: str, section: str = "risk") -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "doc_id": 1,
        "page_number": 40 + chunk_id,
        "section_type": section,
        "section_title": "風險因素" if section == "risk" else "會計政策",
        "content": content,
        "source_url": "https://example.com/filing.pdf",
        "checksum": "deadbeef0123",
        "retrieval_score": 0.7,
    }


def _history(periods: tuple[str, ...] = ("2024Q2", "2024Q3", "2024Q4")) -> dict:
    """Prior periods with mild growth, so trend has something to measure."""
    return {
        period: make_record(
            period,
            snapshot_overrides={
                **FULL_SNAPSHOT,
                "net_revenue": FULL_SNAPSHOT["net_revenue"] - 60 * (index + 1),
                "net_income": FULL_SNAPSHOT["net_income"] - 15 * (index + 1),
            },
        )
        for index, period in enumerate(reversed(periods))
    }


def _complete() -> Scenario:
    return Scenario(
        name="complete",
        description="Every required field present and validated, with history",
        record=make_record(PERIOD, snapshot_overrides=FULL_SNAPSHOT),
        history=_history(),
        expect_ran={"snapshot", "trend", "earnings_quality", "roic_wacc", "ews"},
    )


def _partial() -> Scenario:
    """One absent field must block only the tools that require it."""
    record = make_record(PERIOD, snapshot_overrides={**FULL_SNAPSHOT, "cash_and_equivalents": None})
    return Scenario(
        name="partial",
        description="cash_and_equivalents absent; only EWS requires it",
        record=record,
        expect_blocked={"ews"},
        expect_ran={"snapshot", "roic_wacc", "earnings_quality"},
    )


def _not_applicable() -> Scenario:
    """not_applicable is not the same as missing, and must not read as zero."""
    record = make_record(
        PERIOD,
        snapshot_overrides=FULL_SNAPSHOT,
        field_availability=[
            FieldAvailability(
                field="inventory",
                statement="balance_sheet",
                unit="TWD_thousands",
                state="not_applicable",
                reason="Bank-sector filing",
            )
        ],
    )
    return Scenario(
        name="not_applicable",
        description="Bank filing where inventory does not apply",
        record=record,
        expect_blocked={"ews", "earnings_quality"},
        expect_ran={"snapshot", "roic_wacc"},
    )


def _stale() -> Scenario:
    record = make_record(PERIOD, snapshot_overrides=FULL_SNAPSHOT)
    record.freshness = DataFreshness(
        updated_at=datetime.now(timezone.utc) - timedelta(days=400),
        is_stale=True,
        state="stale",
    )
    return Scenario(
        name="stale",
        description="Data is usable but a newer filing may exist",
        record=record,
        expect_ran={"snapshot", "roic_wacc", "earnings_quality", "ews"},
    )


def _invalid() -> Scenario:
    record = make_record(
        PERIOD,
        snapshot_overrides=FULL_SNAPSHOT,
        validation=[
            ValidationRecord(
                rule_name="balance_sheet_equation",
                passed=False,
                severity="error",
                message="total_assets does not equal liabilities plus equity",
            )
        ],
    )
    record.quality = DataQuality(score=0.4, validation_total=1, validation_failed=1)
    return Scenario(
        name="invalid",
        description="Producer reports a failed balance-sheet reconciliation",
        record=record,
        expect_ran={"snapshot", "roic_wacc", "earnings_quality", "ews"},
    )


def _processing() -> Scenario:
    record = SnapshotRecord(status="processing", source="test", job_id="job-1")
    return Scenario(
        name="processing",
        description="Filing is still being built; nothing may be asserted from it",
        record=record,
        expect_blocked=set(),
        expect_ran=set(),
    )


def _absent() -> Scenario:
    return Scenario(
        name="absent",
        description="No such filing",
        record=None,
        expect_ran=set(),
    )


def _narrative() -> Scenario:
    return Scenario(
        name="narrative",
        description="A question about risk disclosures, answerable only from filing text",
        record=make_record(PERIOD, snapshot_overrides=FULL_SNAPSHOT),
        query="公司面臨哪些主要風險",
        narrative=True,
        chunks=[
            _chunk(11, "本公司之利率風險主要來自投資部位及金融債務。"),
            _chunk(12, "匯率風險來自非功能性貨幣之應收與應付帳款。"),
        ],
        expect_ran={"ews"},
    )


def _contradiction() -> Scenario:
    """Value creation alongside weak earnings quality must be flagged.

    Tuned so both halves genuinely hold: operating income is high against a
    small capital base, so ROIC clears WACC comfortably, while net income is
    driven by non-operating items and unsupported by cash, so accrual quality
    and one-off dependence both score badly.
    """
    record = make_record(
        PERIOD,
        snapshot_overrides={
            **FULL_SNAPSHOT,
            "operating_income": 900.0,
            "equity": 1000.0,
            "total_liabilities": 500.0,
            # Net income far above operating income: non-operating driven.
            "net_income": 2000.0,
            # ...and barely any of it converts to cash, so accruals dominate.
            "operating_cash_flow": 100.0,
        },
    )
    return Scenario(
        name="contradiction",
        description="Strong ROIC against accrual-driven, non-operating earnings",
        record=record,
        expect_ran={"roic_wacc", "earnings_quality"},
        expect_contradiction=True,
    )


def all_scenarios() -> list[Scenario]:
    return [
        _complete(),
        _partial(),
        _not_applicable(),
        _stale(),
        _invalid(),
        _processing(),
        _absent(),
        _narrative(),
        _contradiction(),
    ]


def by_name(name: str) -> Scenario:
    for scenario in all_scenarios():
        if scenario.name == name:
            return scenario
    raise KeyError(name)
