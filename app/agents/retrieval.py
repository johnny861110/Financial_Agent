"""Bounded, question-directed retrieval of filing narrative text.

Numeric questions are answered from canonical facts and never need this. Only
questions that turn on what a filing *says* -- accounting policy changes, risk
disclosures, contingencies, significant events -- retrieve narrative text, and
even then the amount pulled into a prompt is capped.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Narrative topic -> producer section types.
#
# NOT applied as a retrieval filter by default, and that is a measured
# decision rather than a preference. Filtering was compared against plain
# vector search over 20 question/filing pairs on the real corpus: it was never
# better, was worse in half of them, and returned *nothing* three times --
# which the consumer would then report as "no filing text matched", a data gap
# that is not real.
#
# The cause was upstream, and it has since been diagnosed more precisely than
# the original note here guessed. Detection was never running sections to the
# document end: it is page-granular, and `風險管理` matched mid-sentence prose,
# so risk swallowed 26.9% of the corpus across 418 separate sections. The
# producer now requires headings to look like headings and segments notes by
# their numbering, which collapsed risk to 1.4%.
#
# What that leaves is a different shape of problem. `note` (singular, one per
# numbered note) now carries 63.3% of chunks while the legacy `notes` heading
# match is down to 0.8%, so a mapping naming only `notes` points at a nearly
# dead label. `risk` is deliberately not widened to include `note`: its
# remaining 309 chunks are genuine now, and adding `note` would select two
# thirds of the corpus, which is not a filter.
#
# So filtering by type is a weak instrument for anything living in the notes,
# because it all resolves to `note`. `section_title` is the usable topic signal
# -- 885 distinct titles against a dozen coarse types -- which is why this
# mapping stays opt-in via `use_sections=True`.
NARRATIVE_SECTIONS: dict[str, tuple[str, ...]] = {
    "accounting_policy": ("accounting_policy", "note", "notes"),
    "risk": ("risk",),
    "auditor": ("auditor",),
    "notes": ("note", "notes"),
}

# Deciding whether a question needs filing text.
#
# This was originally an allowlist of narrative topics, which failed badly:
# measured against realistic questions, 7 of 10 -- related-party transactions,
# inventory valuation, employee benefits, EPS computation, subsidiaries,
# segments, pledged assets -- were not recognised as narrative at all, so no
# text was retrieved and the answer was numbers only.
#
# The list was not too small; it was the wrong shape. Narrative subject matter
# is unbounded, but the questions answerable from structured facts are not:
# they are the canonical fields and the deterministic tools, which are
# enumerable. So the test is inverted -- retrieve unless the question is
# plainly numeric.
#
# The two failure modes are not symmetric. Over-retrieving costs some bounded,
# cited prompt space while the structured path still runs; under-retrieving
# loses the evidence entirely and silently. Failing toward retrieval is right.
NUMERIC_TERMS: tuple[str, ...] = (
    "營收",
    "收入",
    "毛利",
    "營業利益",
    "淨利",
    "每股盈餘",
    "eps",
    "總資產",
    "負債總額",
    "股東權益",
    "現金流量",
    "週轉",
    "比率",
    "利潤率",
    "margin",
    "roe",
    "roa",
    "roic",
    "wacc",
    "負債比",
    "趨勢",
    "成長",
    "比較",
    "同業",
    "因子",
    "預警",
    "資本配置",
    "估值",
    "trend",
    "growth",
    "compare",
    "peer",
    "factor",
    "valuation",
)

# Topic -> producer section types, used only when section filtering is opted
# into, and to document which sections carry narrative rather than restated
# figures.
NARRATIVE_TERMS: dict[str, tuple[str, ...]] = {
    "accounting_policy": (
        "會計政策",
        "會計估計",
        "認列",
        "重編",
        "適用準則",
        "ifrs",
        "accounting policy",
        "accounting estimate",
        "restat",
    ),
    "risk": (
        "風險",
        "曝險",
        "不確定",
        "訴訟",
        "或有",
        "承諾",
        "減損",
        "疑慮",
        "risk",
        "contingen",
        "litigation",
        "uncertain",
        "impairment",
    ),
    "auditor": (
        "會計師",
        "核閱",
        "查核",
        "保留意見",
        "關鍵查核",
        "auditor",
        "audit opinion",
        "qualified opinion",
    ),
    "notes": (
        "附註",
        "說明",
        "揭露",
        "重大事項",
        "事件",
        "disclosure",
        "note",
        "significant event",
        "subsequent event",
    ),
}

# Prompt bounds. The producer caps each chunk's characters; these cap how many
# chunks reach the model and the total characters across them.
MAX_CHUNKS = 6
MAX_TOTAL_CHARS = 6000


@dataclass
class RetrievedContext:
    """Filing text selected for one question, with its citations."""

    question: str
    topics: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    # How the producer actually ranked these chunks: {mode, state, detail}.
    # Chunks come back carrying section titles, pages and ids whether or not
    # the question influenced the ranking, so without this a fallback is
    # indistinguishable from a search result -- which is exactly how a
    # question-blind retrieval path went unnoticed for months.
    retrieval: dict[str, Any] = field(default_factory=dict)
    # Identifies the filing's chunk corpus at the time these citations were
    # made. A re-extract deletes and re-inserts every chunk, and the new id
    # range overlaps the old, so a stored chunk_id resolves to *different* text
    # rather than 404. Persist this next to any cached citation and compare it
    # before treating that citation as still pointing at what it quoted.
    corpus_version: str | None = None

    @property
    def used(self) -> bool:
        return bool(self.chunks)

    @property
    def degraded_detail(self) -> str | None:
        """Why these chunks were not ranked by the question, if they weren't."""
        state = self.retrieval.get("state")
        if not state or state == "present":
            return None
        detail = self.retrieval.get("detail") or f"retrieval state: {state}"
        return str(detail)

    def as_state(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "topics": self.topics,
            "sections": self.sections,
            "chunks": self.chunks,
            "chunk_count": len(self.chunks),
            "error": self.error,
            "retrieval": self.retrieval,
            "corpus_version": self.corpus_version,
        }


def is_numeric_question(query: str) -> bool:
    """True when a question is answerable from canonical facts alone."""
    lowered = query.lower()
    return any(term in lowered for term in NUMERIC_TERMS)


def narrative_topics(query: str) -> list[str]:
    """Narrative topics a question touches, for optional section filtering.

    This no longer decides *whether* to retrieve -- see NUMERIC_TERMS above.
    An empty result only means no section mapping applies.
    """
    lowered = query.lower()
    return [
        topic for topic, terms in NARRATIVE_TERMS.items() if any(term in lowered for term in terms)
    ]


def sections_for(topics: list[str]) -> list[str]:
    sections: list[str] = []
    for topic in topics:
        for section in NARRATIVE_SECTIONS.get(topic, ()):
            if section not in sections:
                sections.append(section)
    return sections


def bound_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cap chunk count and total characters before anything reaches a prompt."""
    bounded: list[dict[str, Any]] = []
    total = 0
    for chunk in chunks[:MAX_CHUNKS]:
        content = chunk.get("content") or ""
        if total + len(content) > MAX_TOTAL_CHARS:
            break
        bounded.append(chunk)
        total += len(content)
    return bounded


def citation(chunk: dict[str, Any]) -> str:
    """Human-readable source reference for one chunk."""
    parts = []
    if chunk.get("section_title") or chunk.get("section_type"):
        parts.append(str(chunk.get("section_title") or chunk.get("section_type")))
    if chunk.get("page_number") is not None:
        parts.append(f"p.{chunk['page_number']}")
    if chunk.get("chunk_id") is not None:
        parts.append(f"chunk {chunk['chunk_id']}")
    return " · ".join(parts) if parts else "filing"


def retrieve(
    provider: Any,
    stock_code: str,
    period: str,
    query: str,
    *,
    use_sections: bool = False,
) -> RetrievedContext:
    """Retrieve narrative text for a question, or nothing if it is numeric.

    Topic classification still decides *whether* to retrieve -- numeric
    questions never reach the producer. What it no longer does by default is
    narrow the search to those topics' sections; see NARRATIVE_SECTIONS for the
    measurement behind that.

    Never raises: retrieval failure degrades to a structured data-gap note
    rather than failing the whole research run.
    """
    if not query or is_numeric_question(query):
        return RetrievedContext(question=query)

    topics = narrative_topics(query)
    sections = sections_for(topics) if use_sections else []
    context = RetrievedContext(question=query, topics=topics, sections=sections)

    getter = getattr(provider, "get_context", None)
    if getter is None:
        context.error = "The configured data provider cannot retrieve filing text"
        return context

    try:
        payload = getter(
            stock_code,
            period,
            query,
            sections=sections or None,
            evidence_limit=MAX_CHUNKS * 2,
        )
    except TypeError:
        # A provider on the older signature: retrieval params are unsupported.
        context.error = "The configured data provider does not support question retrieval"
        return context
    except Exception as exc:
        logger.warning("Filing text retrieval failed: %s", exc)
        context.error = f"Filing text retrieval failed: {exc}"
        return context

    if not payload:
        context.error = "No filing context is available for this period"
        return context

    reported = payload.get("retrieval")
    if isinstance(reported, dict):
        context.retrieval = reported

    version = payload.get("corpus_version")
    if isinstance(version, str):
        context.corpus_version = version

    chunks = payload.get("evidence_chunks") or []
    if not isinstance(chunks, list):
        context.error = "The provider returned an unexpected context payload"
        return context

    context.chunks = bound_chunks([c for c in chunks if isinstance(c, dict) and c.get("content")])
    if not context.chunks:
        context.error = "No filing text matched this question"
    return context
