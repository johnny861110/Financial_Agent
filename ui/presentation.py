"""Display-ready views over agent and filing payloads.

Pure functions, deliberately free of Streamlit imports: the interesting logic
here -- which citation is safe to show, how a field's absence should read, what
counts as a blocking validation rather than a warning -- is worth testing, and
Streamlit rendering is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# How each canonical absence state should read to a person. "missing" and
# "not_applicable" mean very different things -- one is a data gap to chase,
# the other is correct for this filer -- and collapsing them loses that.
FIELD_STATE_DISPLAY: dict[str, tuple[str, str]] = {
    "present": ("✅", "Present"),
    "missing": ("⚠️", "Missing from the filing"),
    "null": ("➖", "Reported as null"),
    "not_applicable": ("🚫", "Not applicable to this filer"),
    "provider_failure": ("❌", "Provider failed to supply"),
    "unknown": ("❓", "State could not be determined"),
}

_UNKNOWN_STATE = ("❓", "State could not be determined")


@dataclass
class Citation:
    """A reference a reader can actually follow."""

    label: str
    url: str | None = None
    excerpt: str | None = None
    score: float | None = None
    # Database identifiers, kept for traceability but never the headline
    # reference: a chunk id means nothing to a reader and a stable document
    # URL is the real citation whenever one exists.
    detail: str | None = None

    @property
    def is_linkable(self) -> bool:
        return bool(self.url)


def _page_label(chunk: dict[str, Any]) -> str:
    parts: list[str] = []
    section = chunk.get("section_title") or chunk.get("section_type")
    if section:
        parts.append(str(section))
    page = chunk.get("page_number")
    if page is not None:
        parts.append(f"p.{page}")
    return " · ".join(parts) if parts else "Filing text"


def citation_for(chunk: dict[str, Any]) -> Citation:
    """Build a reader-facing citation from a retrieved filing chunk.

    Internal filesystem paths are never surfaced, and database identifiers are
    demoted to a detail line rather than shown as the reference itself.
    """
    identifiers = []
    if chunk.get("chunk_id") is not None:
        identifiers.append(f"chunk {chunk['chunk_id']}")
    if chunk.get("doc_id") is not None:
        identifiers.append(f"doc {chunk['doc_id']}")
    checksum = chunk.get("checksum")
    if checksum:
        identifiers.append(f"checksum {str(checksum)[:12]}")

    return Citation(
        label=_page_label(chunk),
        url=chunk.get("source_url") or None,
        excerpt=chunk.get("excerpt") or chunk.get("content") or None,
        score=chunk.get("retrieval_score"),
        detail=" · ".join(identifiers) or None,
    )


def split_evidence(evidence: list[dict[str, Any]]) -> tuple[list[Citation], list[dict[str, Any]]]:
    """Separate citable filing passages from structured fact evidence."""
    citations: list[Citation] = []
    structured: list[dict[str, Any]] = []
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        if item.get("source_type") == "filing_text" or item.get("chunk_id") is not None:
            citations.append(citation_for(item))
        else:
            structured.append(item)
    return citations, structured


@dataclass
class FieldStateGroup:
    state: str
    icon: str
    description: str
    fields: list[str] = field(default_factory=list)


def group_field_states(states: dict[str, str]) -> list[FieldStateGroup]:
    """Group fields by availability state, most actionable first.

    Present fields sort last: a reader scanning this wants to see what is
    absent, not confirmation of what is there.
    """
    order = ["provider_failure", "missing", "null", "not_applicable", "unknown", "present"]
    grouped: dict[str, FieldStateGroup] = {}
    for name, state in sorted((states or {}).items()):
        # A state this UI does not recognise still has to appear. Folding it
        # into the unknown bucket surfaces it as undetermined rather than
        # dropping the field from the display entirely.
        key = state if state in FIELD_STATE_DISPLAY else "unknown"
        icon, description = FIELD_STATE_DISPLAY[key]
        group = grouped.setdefault(key, FieldStateGroup(key, icon, description))
        group.fields.append(name)
    return [grouped[state] for state in order if state in grouped]


@dataclass
class BlockedTool:
    """A tool the planner refused to run, and the reason it gave."""

    tool: str
    finding: str
    blocked_fields: dict[str, str] = field(default_factory=dict)
    failed_rules: list[str] = field(default_factory=list)

    def reasons(self) -> list[str]:
        """One human-readable line per blocking cause."""
        lines = [
            f"{name}: {FIELD_STATE_DISPLAY.get(state, _UNKNOWN_STATE)[1].lower()}"
            for name, state in sorted(self.blocked_fields.items())
        ]
        lines.extend(f"validation failed: {rule}" for rule in self.failed_rules)
        return lines


def blocked_tools(tool_results: dict[str, Any]) -> list[BlockedTool]:
    """Tools that were gated before execution, with their per-field reasons."""
    blocked: list[BlockedTool] = []
    for name, result in (tool_results or {}).items():
        if not isinstance(result, dict):
            continue
        fields = result.get("blocked_fields") or {}
        rules = result.get("failed_rules") or []
        if not fields and not rules:
            continue
        blocked.append(
            BlockedTool(
                tool=name,
                finding=result.get("finding") or "",
                blocked_fields=dict(fields),
                failed_rules=list(rules),
            )
        )
    return sorted(blocked, key=lambda item: item.tool)


def split_data_gaps(gaps: list[str]) -> tuple[list[str], list[str]]:
    """Separate validation failures from ordinary data gaps.

    A failed validation rule means the producer believes a number is wrong,
    which is a different kind of problem from a field simply being absent, and
    the two should not sit in one undifferentiated list.
    """
    validation: list[str] = []
    ordinary: list[str] = []
    for gap in gaps or []:
        text = str(gap)
        if "validation" in text.lower():
            validation.append(text)
        else:
            ordinary.append(text)
    return validation, ordinary


@dataclass
class PipelineView:
    status: str
    stage_states: list[tuple[str, str]] = field(default_factory=list)
    failed_stage: str | None = None

    @property
    def has_failure(self) -> bool:
        return self.failed_stage is not None


def pipeline_view(readiness: dict[str, Any], record: dict[str, Any] | None = None) -> PipelineView:
    """Summarise processing state, naming the stage that failed if any."""
    view = PipelineView(status=str((readiness or {}).get("status") or "unknown"))
    for entry in (record or {}).get("pipeline_state") or []:
        if not isinstance(entry, dict):
            continue
        stage = str(entry.get("stage") or "")
        state = str(entry.get("status") or "")
        if not stage:
            continue
        view.stage_states.append((stage, state))
        if state == "failed":
            view.failed_stage = stage
    return view
