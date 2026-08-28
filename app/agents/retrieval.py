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

# Producer section types worth retrieving, keyed by the narrative topic a
# question is about. Sections outside this map (income_statement, balance_sheet,
# eps_note...) restate numbers that the structured-fact path already answers
# better, so they are never requested.
NARRATIVE_SECTIONS: dict[str, tuple[str, ...]] = {
    "accounting_policy": ("accounting_policy", "notes"),
    "risk": ("risk",),
    "auditor": ("auditor",),
    "notes": ("notes",),
}

# Terms that mark a question as being about narrative content rather than a
# number. Traditional Chinese first, since that is what filings are written in.
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

    @property
    def used(self) -> bool:
        return bool(self.chunks)

    def as_state(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "topics": self.topics,
            "sections": self.sections,
            "chunks": self.chunks,
            "chunk_count": len(self.chunks),
            "error": self.error,
        }


def narrative_topics(query: str) -> list[str]:
    """Return the narrative topics a question touches, if any."""
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
) -> RetrievedContext:
    """Retrieve narrative text for a question, or nothing if it is numeric.

    Never raises: retrieval failure degrades to a structured data-gap note
    rather than failing the whole research run.
    """
    topics = narrative_topics(query)
    if not topics:
        return RetrievedContext(question=query)

    sections = sections_for(topics)
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
            sections=sections,
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

    chunks = payload.get("evidence_chunks") or []
    if not isinstance(chunks, list):
        context.error = "The provider returned an unexpected context payload"
        return context

    context.chunks = bound_chunks([c for c in chunks if isinstance(c, dict) and c.get("content")])
    if not context.chunks:
        context.error = "No filing text matched this question"
    return context
