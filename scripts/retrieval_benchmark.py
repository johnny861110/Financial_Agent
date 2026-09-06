"""Measure filing-text retrieval on the questions RAG is actually for.

An earlier benchmark scored retrieval on 應收帳款, 營業收入 and 所得稅. All three
are canonical fields the producer publishes as structured data, so it was
measuring a path that should never be taken: those numbers come from
`facts`/`snapshot`, where they carry a unit, a period and an availability
state. Retrieval exists for what a filing *says* -- accounting judgement,
impairment criteria, valuation method, subsidiaries, contingencies -- and of
the note titles in the corpus only about 1% have a canonical counterpart.

So probes are derived from the corpus rather than written by hand, and any
title that names a canonical field is excluded. That keeps the benchmark
honest as the corpus changes, and stops it drifting back onto structured
ground.

Usage:
    FINANCIAL_REPORTS_BASE_URL=http://127.0.0.1:8010 \
        .venv/bin/python scripts/retrieval_benchmark.py [--top-k 10] [--limit 40]

Requires a running producer; this is deliberately not part of `python -m
evaluation`, which is fixture-only and must stay deterministic.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.retrieval import retrieve  # noqa: E402
from app.data.factory import get_data_provider  # noqa: E402


def canonical_labels(provider: Any) -> set[str]:
    """Chinese labels the producer publishes as structured fields."""
    try:
        capabilities = provider.get_capabilities()
    except Exception as exc:  # pragma: no cover - operational tool
        print(f"could not read capabilities ({exc}); no titles will be excluded")
        return set()
    fields = capabilities.get("fields") or []
    return {str(f.get("label_zh", "")).replace(" ", "") for f in fields if f.get("label_zh")}


def probes(provider: Any, limit: int) -> list[tuple[str, str, str]]:
    """(stock, period, note title) for notes with no structured counterpart."""
    excluded = canonical_labels(provider)
    found: list[tuple[str, str, str]] = []
    for stock in provider.list_all_stocks():
        for period in provider.list_available_periods(stock):
            payload = provider.get_context(stock, period, None, evidence_limit=50)
            if not payload:
                continue
            titles = {
                str(c.get("section_title") or "").strip()
                for c in payload.get("evidence_chunks") or []
                if c.get("section_type") == "note"
            }
            for title in sorted(t for t in titles if t):
                if title.replace(" ", "") in excluded or len(title) < 3:
                    continue
                found.append((stock, period, title))
                break  # one probe per filing keeps the run bounded
            if len(found) >= limit:
                return found
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    provider = get_data_provider()
    cases = probes(provider, args.limit)
    if not cases:
        print("no narrative probes found -- is the producer reachable and the corpus extracted?")
        return 1

    hits = 0
    ranks: list[int] = []
    degraded: dict[str, int] = defaultdict(int)
    reached_the_model = 0

    for stock, period, title in cases:
        # Measure through the same predicate the workflow uses, not just the
        # producer call. Scoring the producer alone reports an upper bound: a
        # passage that is retrieved and then dropped before the prompt is not
        # a passage the user got.
        context = retrieve(provider, stock, period, title)
        if context.used or context.error:
            reached_the_model += 1

        payload = provider.get_context(stock, period, title, evidence_limit=args.top_k)
        if not payload:
            continue
        state = (payload.get("retrieval") or {}).get("state", "unknown")
        if state != "present":
            degraded[state] += 1
        chunks = payload.get("evidence_chunks") or []
        rank = next(
            (
                i
                for i, c in enumerate(chunks, 1)
                if str(c.get("section_title") or "").strip() == title
            ),
            None,
        )
        if rank:
            hits += 1
            ranks.append(rank)

    total = len(cases)
    mean_rank = sum(ranks) / len(ranks) if ranks else float("nan")
    print(f"narrative probes:      {total}")
    print(f"hit@{args.top_k}:               {hits} ({100 * hits / total:.0f}%)")
    print(f"mean rank when hit:    {mean_rank:.1f}")
    print(
        f"reached the model:     {reached_the_model} "
        f"({100 * reached_the_model / total:.0f}%) -- survived the workflow, not just retrieved"
    )
    if degraded:
        # A degraded run measures fallback ordering, not retrieval quality.
        print(f"NOT question-ranked:   {dict(degraded)} -- these results are not comparable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
