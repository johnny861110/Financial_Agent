#!/usr/bin/env python
"""Run the golden scenarios against the live stack and gate on the result.

Nothing ships unless every scenario passes. This exists because the unit suite
cannot see any of what it checks: no test exercises the LLM, so `POST
/api/agent/research` returned 500 for every live query while 211 tests were
green, and the agent later reported a data gap for a field whose value it was
holding. Both were found by a person reading an answer.

Usage:
    uv run python scripts/golden_check.py            # all scenarios
    uv run python scripts/golden_check.py --id numeric-revenue
    uv run python scripts/golden_check.py --json report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.golden.scenarios import SCENARIOS, Scenario  # noqa: E402

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


@dataclass
class Failure:
    scenario: str
    assertion: str
    detail: str


def renderings(value: float) -> list[str]:
    """Every acceptable way to write one TWD-thousands figure.

    Derived from the live value rather than typed in, so a re-ingest changes
    what is expected instead of breaking the gate. Both the raw thousands and
    the 萬/億/兆 scaling are accepted: they are the same number, and which one
    appears is a presentation choice the gate should not dictate.
    """
    forms = [f"{value:,.0f}", f"{value:,.2f}", f"{abs(value):,.0f}"]
    for scale, suffix in ((1e9, "兆"), (1e5, "億"), (1e1, "萬")):
        if abs(value) >= scale:
            scaled = value / scale
            forms += [f"{scaled:,.2f} {suffix}", f"{scaled:,.2f}{suffix}"]
            # A model may round 348.21 億 to 348.2 億; accept one less decimal.
            forms += [f"{scaled:,.1f} {suffix}", f"{scaled:,.1f}{suffix}"]
            break
    return forms


class Runner:
    def __init__(self, api: str) -> None:
        self.api = api.rstrip("/")
        import httpx

        self.client = httpx.Client(timeout=240.0)

    def canonical_value(self, stock: str, period: str, field: str) -> float | None:
        r = self.client.get(f"{self.api}/api/financials/{stock}/{period}")
        if r.status_code != 200:
            return None
        body = r.json()
        for group in ("income_statement", "balance_sheet", "cash_flow", "margins", "returns"):
            value = (body.get(group) or {}).get(field)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def field_states(self, stock: str, period: str) -> dict[str, str]:
        r = self.client.get(f"{self.api}/api/financials/{stock}/{period}")
        if r.status_code != 200:
            return {}
        return ((r.json().get("data_context") or {}).get("field_states")) or {}

    def ask(self, s: Scenario) -> dict:
        route = "research" if s.mode == "research" else "query"
        r = self.client.post(
            f"{self.api}/api/agent/{route}",
            json={
                "query": s.query,
                "stock_code": s.stock_code,
                "period": s.period,
                "mode": s.mode,
            },
        )
        if r.status_code != 200:
            return {"__http__": r.status_code, "__body__": r.text[:400]}
        return r.json()

    def check(self, s: Scenario) -> list[Failure]:
        fails: list[Failure] = []
        response = self.ask(s)

        if "__http__" in response:
            return [
                Failure(
                    s.id, "request succeeds", f"HTTP {response['__http__']}: {response['__body__']}"
                )
            ]

        answer = response.get("answer") or ""
        gaps = " | ".join(response.get("data_gaps") or [])
        plan = response.get("research_plan") or []
        evidence = response.get("evidence") or []

        if not answer.strip():
            fails.append(Failure(s.id, "answer is non-empty", "the answer was blank"))

        for fld in s.must_state_fields:
            value = self.canonical_value(s.stock_code, s.period, fld)
            if value is None:
                fails.append(
                    Failure(
                        s.id, f"{fld} is obtainable", "the API returned no value to compare against"
                    )
                )
                continue
            if not any(form in answer for form in renderings(value)):
                fails.append(
                    Failure(
                        s.id,
                        f"answer states {fld}",
                        f"expected one of {renderings(value)[:3]}, answer said: {answer[:180]}",
                    )
                )

        for text in s.must_contain:
            if text not in answer:
                fails.append(Failure(s.id, f"answer contains {text!r}", answer[:180]))

        for text in s.must_not_contain:
            if text in answer:
                fails.append(
                    Failure(s.id, f"answer avoids {text!r}", f"...{_around(answer, text)}...")
                )

        for fld in s.must_not_report_gap:
            # Match the field as a gap entry, not as a substring of the
            # contract-violation line that *reports* the producer's mistake --
            # that line is supposed to name the field.
            for entry in response.get("data_gaps") or []:
                if entry.strip() == fld:
                    fails.append(
                        Failure(s.id, f"{fld} is not reported as a gap", f"data_gaps: {gaps}")
                    )
                    break

        for fld in s.must_report_gap:
            if not any(entry.strip() == fld for entry in (response.get("data_gaps") or [])):
                fails.append(Failure(s.id, f"{fld} is reported as a gap", f"data_gaps: {gaps}"))

        if len(plan) < s.min_tools:
            fails.append(
                Failure(s.id, f"plan has >= {s.min_tools} tools", f"plan was {plan or '[]'}")
            )

        citations = [e for e in evidence if e.get("source_type") == "filing_text"]
        if len(citations) < s.min_filing_citations:
            fails.append(
                Failure(
                    s.id,
                    f"answer cites >= {s.min_filing_citations} filing passages",
                    f"got {len(citations)}",
                )
            )

        if s.expect_field_states:
            states = self.field_states(s.stock_code, s.period)
            for fld, expected in s.expect_field_states.items():
                actual = states.get(fld, "<absent>")
                if actual != expected:
                    fails.append(Failure(s.id, f"{fld} state is {expected!r}", f"was {actual!r}"))

        return fails


def _around(text: str, needle: str, span: int = 60) -> str:
    i = text.find(needle)
    return text[max(0, i - span) : i + len(needle) + span].replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default=os.getenv("GOLDEN_API", "http://localhost:8000"))
    ap.add_argument("--id", action="append", help="run only these scenario ids")
    ap.add_argument("--json", help="write a machine-readable report here")
    args = ap.parse_args()

    selected = [s for s in SCENARIOS if not args.id or s.id in args.id]
    if not selected:
        print(f"{RED}no scenario matched {args.id}{RESET}")
        return 2

    runner = Runner(args.api)
    print(f"Golden gate: {len(selected)} scenarios against {args.api}\n")

    all_failures: list[Failure] = []
    results = []
    for s in selected:
        failures = runner.check(s)
        all_failures += failures
        ok = not failures
        mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {mark}  {s.id}")
        if not ok:
            print(f"        {DIM}{s.why}{RESET}")
            for f in failures:
                print(f"        {YELLOW}·{RESET} {f.assertion}")
                print(f"          {DIM}{f.detail}{RESET}")
        results.append({"id": s.id, "passed": ok, "failures": [f.__dict__ for f in failures]})

    passed = sum(1 for r in results if r["passed"])
    print(f"\n{passed}/{len(selected)} scenarios passed", end="")
    print(f", {len(all_failures)} failed assertions" if all_failures else "")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"passed": passed, "total": len(selected), "results": results}, indent=2),
            encoding="utf-8",
        )
        print(f"report written to {args.json}")

    if all_failures:
        print(f"\n{RED}Gate closed.{RESET} A scenario fails only because a real answer was wrong.")
        return 1
    print(f"\n{GREEN}Gate open.{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
