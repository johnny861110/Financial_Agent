"""Golden scenarios: the questions, and what a correct answer must and must not say.

Every case here exists because a real answer failed it. This is not a list of
things that would be nice; it is the record of what has already gone wrong once,
turned into a gate.

Two rules kept the assertions honest:

1. **Expected figures are derived, never typed in.** A scenario states which
   canonical field it is about; the runner reads the value from the API and
   builds the acceptable renderings. Hardcoding "104.85 億元" would make the
   gate fail on the next re-ingest and teach everyone to ignore it.

2. **Assertions are about substance, not phrasing.** An LLM writes the prose, so
   requiring an exact sentence would fail on wording. What is asserted is: a
   figure the answer must carry, a claim it must not make, a source it must
   cite, a plan it must have run.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    """One question and the properties its answer must hold."""

    id: str
    why: str
    query: str
    stock_code: str
    period: str
    mode: str = "auto"

    # Canonical fields whose value must appear in the answer, in any of the
    # renderings the runner derives from the live API.
    must_state_fields: tuple[str, ...] = ()

    # Substrings that must appear literally (units, section headings, terms).
    must_contain: tuple[str, ...] = ()

    # Substrings that must not appear. Used for leaked internals, placeholder
    # strings, and self-contradiction.
    must_not_contain: tuple[str, ...] = ()

    # Fields the report must NOT list as a data gap, because the value is
    # obtainable. The single most important assertion class here.
    must_not_report_gap: tuple[str, ...] = ()

    # Fields the report MUST list as a data gap, because they genuinely are
    # absent. Guards against a fix that hides real absence to make gaps go away.
    must_report_gap: tuple[str, ...] = ()

    # Minimum number of tools the plan must contain.
    min_tools: int = 1

    # The answer must cite at least this many filing passages.
    min_filing_citations: int = 0

    # Fields that must resolve to this state in the readiness contract.
    expect_field_states: dict[str, str] = field(default_factory=dict)

    # Every significant figure in the answer must trace to a value the backend
    # supplied. A model that computes rather than copies is unsound however
    # well it tests: asked to scale one figure it produced "348,213.47 萬元"
    # from 348,213,466 thousands, wrong by a factor of 100.
    forbid_invented_numbers: bool = False


# --- Scenarios -------------------------------------------------------------

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="numeric-revenue",
        why=(
            "The structured path must answer a figure question exactly. This "
            "failed twice: once returning 500 when the prompt overflowed, once "
            "answering '營業收入尚未提供' for a period whose revenue the "
            "producer had returned."
        ),
        query="2025Q1 的營業收入是多少？",
        stock_code="3661",
        period="2025Q1",
        mode="quick",
        must_state_fields=("net_revenue",),
        must_not_contain=("尚未提供", "無法提供", "資料缺失", "not available"),
        forbid_invented_numbers=True,
    ),
    Scenario(
        id="free-cash-flow-is-not-a-gap",
        why=(
            "The producer publishes free_cash_flow and declares it 'missing' in "
            "the same response, so the agent reported 自由現金流 as a data gap "
            "while holding 348,213,466. The value is derived from operating "
            "cash flow and capex, both present in every filing."
        ),
        query="自由現金流是多少？",
        stock_code="2330",
        period="2026Q1",
        mode="quick",
        must_state_fields=("free_cash_flow",),
        must_not_report_gap=("free_cash_flow",),
        expect_field_states={"free_cash_flow": "present"},
        forbid_invented_numbers=True,
    ),
    Scenario(
        id="real-gaps-stay-reported",
        why=(
            "The counterweight to the case above. These four have zero rows "
            "across all 70 filings -- FinMind never supplies them -- so a fix "
            "that made gaps disappear rather than resolving them would pass "
            "the FCF case and fail here."
        ),
        query="整體表現幫我分析",
        stock_code="2330",
        period="2026Q1",
        must_report_gap=(
            "eps_diluted",
            "rd_expenses",
            "equity_attributable_to_parent",
            "net_income_attributable_to_parent",
        ),
        must_not_report_gap=("free_cash_flow",),
        min_tools=5,
    ),
    Scenario(
        id="broad-analysis-plans-broadly",
        why=(
            "'整體表現幫我分析' matched no entry in a ten-word keyword allowlist, "
            "so it planned one tool and published the investment thesis "
            "'Financial snapshot loaded' -- a status string -- twice in the "
            "same answer."
        ),
        query="整體表現幫我分析",
        stock_code="2330",
        period="2026Q1",
        min_tools=5,
        must_state_fields=("net_revenue",),
        must_not_contain=(
            "snapshot loaded",
            "財務快照已載入",
            "Financial snapshot",
        ),
    ),
    Scenario(
        id="money-is-readable",
        why=(
            "Values are TWD thousands, so a raw figure prints as thirteen "
            "digits: 8660949685.0 新台幣千元 is 8.66 兆元. A reader cannot parse "
            "the first form and will misjudge the scale."
        ),
        query="總資產有多少？",
        stock_code="2330",
        period="2026Q1",
        mode="quick",
        must_state_fields=("total_assets",),
        must_not_contain=("8660949685", "8,660,949,685"),
        forbid_invented_numbers=True,
    ),
    Scenario(
        id="arithmetic-is-not-the-models-job",
        why=(
            "A question phrased as a calculation invites the model to compute. "
            "It must still only report figures the backend produced: asked to "
            "rescale one, it answered '348,213.47 萬元' for 348,213,466 "
            "thousands -- the right digits under the wrong power of ten."
        ),
        query="營業現金流和資本支出各是多少？兩者相減是多少？",
        stock_code="2330",
        period="2026Q1",
        mode="quick",
        forbid_invented_numbers=True,
    ),
    Scenario(
        id="narrative-cites-the-filing",
        why=(
            "Retrieval is for what the filing says. Passages were being "
            "discarded whenever the question missed a topic allowlist, so 6 of "
            "8 narrative questions lost their evidence before the model saw it."
        ),
        query="公司的信用減損損失如何認定？",
        stock_code="3661",
        period="2025Q1",
        min_filing_citations=1,
    ),
    Scenario(
        id="no-internal-leakage",
        why=(
            "A filing with no source documents answered 409, and the unhandled "
            "error reached the user's data-gap list carrying the internal "
            "service URL and a link to MDN's 409 page."
        ),
        query="這一期的營運狀況如何？",
        stock_code="7418",
        period="2026Q1",
        must_not_contain=(
            "127.0.0.1",
            "localhost",
            "8010",
            "developer.mozilla.org",
            "Traceback",
            "httpx",
        ),
    ),
    Scenario(
        id="bank-fields-are-not-applicable",
        why=(
            "net_interest_income and loan_loss_provisions do not apply to a "
            "semiconductor company. Reporting them as 'missing' would imply "
            "the filing failed to supply something it owed."
        ),
        query="整體表現幫我分析",
        stock_code="2330",
        period="2026Q1",
        expect_field_states={
            "net_interest_income": "not_applicable",
            "loan_loss_provisions": "not_applicable",
        },
        must_not_report_gap=("net_interest_income", "loan_loss_provisions"),
    ),
)
