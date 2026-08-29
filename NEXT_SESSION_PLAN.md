# Next Session Handoff

**Last updated:** 2026-08-29

Read this first. It states what exists, what to do next, and the traps that
have already cost time. It is deliberately not a history of how things got
here — merged PRs carry that.

---

## 1. Where things stand

| | Financial_Agent | FinancialReports |
| --- | --- | --- |
| repo | `johnny861110/Financial_Agent` | `johnny861110/FinancialReports` |
| local | `/mnt/c/Users/johnn/GITHUB_REPO/Financial_Agent` | `/mnt/c/Users/johnn/GITHUB_REPO/FinancialReports` |
| latest merged PR | #15 | #7 |
| tests | 138 | 99 |
| CI | gates + cross-repo smoke, green | gates on 3.10/3.11/3.12, green |

Both repos are clean, synchronized `0/0`, and carry only `main`. PR numbers are
used rather than commit SHAs because any SHA written here is stale the moment
the file is committed. Confirm the real state at session start:

```bash
git rev-parse HEAD origin/main && git status --short
```

**Do not delete or commit these pre-existing untracked paths.** They are not
this project's to manage:

```text
Financial_Agent:    .claude/  AGENTS.md  CLAUDE.md
FinancialReports:   .claude/  AGENTS.md  CLAUDE.md  examples/batch_2025_missing.json
```

---

## 2. What already works — do not rebuild it

FinancialReports owns source acquisition, parsing, canonical facts, quality,
validation and evidence. Financial_Agent owns analytics, research planning,
tool orchestration and the final answer. **The boundary is HTTP only.**

| Capability | Where |
| --- | --- |
| Producer API v1, OpenAPI artifact + drift test | `FinancialReports/src/api/` |
| PostgreSQL + pgvector, containerized | `FinancialReports/docker-compose.yml` |
| Question-directed chunk retrieval | `FinancialReports/src/api/repository.py` |
| Provider protocol, retry, stale cache, controlled fallback | `app/data/providers.py` |
| `CanonicalFinancialContext` — field states, units, validation | `app/data/context.py` |
| All eight deterministic services on `load_context()` | `app/services/` |
| Tool requirements + pre-execution eligibility gate | `app/agents/tools.py` |
| Intent-gated bounded retrieval with citations | `app/agents/retrieval.py` |
| Display logic for citations and field states | `ui/presentation.py` |
| Fixed evaluation set and metrics | `evaluation/` |

Phases A–E and the evaluation half of F are done. Eight of the nine services
read filings through `load_context()` and never treat missing, null or
not-applicable as zero — `ManagementService` is the exception because it scores
caller-supplied assumptions, not filing data. Tool eligibility is decided
before execution; narrative questions retrieve cited filing text.

---

## 3. Next, in priority order

### 3.1 Garbled corpus chunks — highest value, blocks retrieval quality

**25% of the corpus is table-extraction debris.** 4,780 of 19,152 chunks are
under 30% letters/CJK — text like
`4 1 . 年 2 2 2 1 4 1 2 1 0 1 1 , , , , %`. Their mean `importance_score` is
**0.70 against 0.65 for real prose**, so the fallback ranking actively prefers
them, and one scored 0.702 on a genuine question.

Two angles, both in FinancialReports:

- table handling in `src/parsers/` — tables become character soup
- `_score_chunk` in `src/parsers/pdf_section_parser.py` — stop rewarding digit
  density

A read-time legibility filter would be the same kind of stopgap the content
dedupe already is; prefer fixing generation, since re-ingest is now safe.

### 3.2 Unsupported-claim rate — the missing evaluation

`evaluation/` measures tool gating, citation coverage and contradiction recall,
all exactly, because all are deterministic. **Unsupported-claim rate is
absent**, deliberately: it is a property of generated prose, so measuring it
without a model means inventing a proxy and then trusting the proxy.

It needs a harness running with `LLM_ENABLED=true` that compares each claim in
the answer against the report and the retrieved passages. **This is the measure
that would catch the agent asserting something no evidence supports** — the
single most valuable thing still missing.

### 3.3 Section labels are unreliable

Producer section detection puts ~65% of a filing's chunks into one section
type, so an auditor's report can be labelled `income_statement`. Section
filtering is therefore **off by default** in `app/agents/retrieval.py`
(`use_sections=True` opts in). Fixing `split_sections` would make the filter
usable and improve `sections=` for all consumers.

### 3.4 Phase F production controls

None of these exist: authentication, rate limits, request IDs, durable jobs,
shared cache. The service should not be called production-ready without them.

### 3.5 Deferred with reasons — do not "finish" these blindly

- **Supported company sectors** in `ToolRequirements`.
  `FilingIdentityRecord.industry` exists in the model but nothing populates or
  reads it, and the JSON provider builds no identity at all. Needs a real
  producer for sector data first, or it is a gate with no input.
- **`get_context` raises on a producer 409** while `load_record` returns a
  typed state. That is consistent with the guardrail against silently
  absorbing producer contract errors, so it was left alone — but callers must
  know it.

---

## 4. Running things

### Producer database and API

```bash
cd /mnt/c/Users/johnn/GITHUB_REPO/FinancialReports
docker compose up -d db          # pgvector/pgvector:pg16
export FR_DATABASE_URL="postgresql+psycopg://financial:financial@localhost:5432/financial"
uv run uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8010
```

The `financialreports_pgdata` volume holds the corpus: **19,152 chunks, all
embedded** with `BAAI/bge-base-zh-v1.5`, zero duplicates, 71 filings
`insight_ready`. It is local only — not committed, not deployed.

### Gates

```bash
# Financial_Agent
.venv/bin/pytest -q
FINANCIAL_DATA_PATH=/tmp/nonexistent .venv/bin/pytest -q   # must also pass
.venv/bin/mypy app/data app/agents app/api app/services app/models/agent_models.py ui/api_client.py ui/presentation.py evaluation
.venv/bin/black --check app tests ui evaluation streamlit_app.py
.venv/bin/python -m compileall -q app tests ui evaluation
git -c core.whitespace=cr-at-eol diff --check
npx gitnexus analyze --force

# FinancialReports (needs FR_DATABASE_URL and a running db)
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy src/ --ignore-missing-imports
uv run pytest tests/
```

CI runs these on every PR and is the authority. It installs with
`uv sync --frozen`, so a local `.venv` that has drifted from `uv.lock` can
disagree with it — `uv lock --check` has its own CI job for that.

### Evaluation report

```bash
python -m evaluation      # exits non-zero if any measure is not exact
```

---

## 5. Traps that have already cost time

Every one of these was found by running something, not by reading code.

**`data/` is gitignored — nothing in it is committed.** A test that builds a
service with a default `DataLoader()` silently reads the developer's local
files and cannot reproduce on a fresh clone. Inject a `RecordProvider` from
`tests/helpers.py`. The `FINANCIAL_DATA_PATH=/tmp/nonexistent` run above exists
to catch this.

**Re-ingesting with `fr extract --force` alone corrupts filing state.** It
resets the filing to `extracted`, stripping validated and insight output, and
the API then answers 409 for it. Always go through the pipeline:

```bash
uv run fr run <stock> <year> <Qn> --stages extract,validate,insights --force
```

**A skipped test looks exactly like a passing one.** The cross-repo smoke job
seeds a filing and sets `SMOKE_REQUIRE_DATA=1` so "no data" fails instead of
skipping; the conftest raises instead of skipping when `CI` is set. Preserve
both — without them a broken setup step reports green while testing nothing.

**Background processes outlive their CI step.** uvicorn started with a bare `&`
kept the runner blocked and failed the job five minutes *after* the tests
passed. Start it under `setsid` with stdin closed and reap it in an `always()`
step.

**Deterministic tests prove the code does what you wrote, not that you wrote
the right thing.** Two Phase D design decisions — section filtering and the
narrative allowlist — passed every test and were both wrong; only querying the
real corpus showed it. Before believing a metric, look at what produced it: two
scenarios in the evaluation set scored perfectly for the wrong reasons until
inspected.

---

## 6. Engineering guardrails

- Financial Agent never connects to the producer database. HTTP only.
- Do not move raw PDF/XBRL parsing into Financial Agent.
- Do not let the LLM calculate canonical financial facts.
- Do not interpret missing, null, or not-applicable as zero.
- Do not silently fall back on producer 404, 409, or 422.
- Do not send filing text to the LLM without retrieval and size bounds.
- Preserve API compatibility while changing services.
- Keep the protected untracked paths in §1 untouched.
- Exact-path staging, small commits; never mix generated GitNexus files into a
  feature commit.
- Confirm before any push, PR, or merge.

---

## 7. Resume prompt

```text
Read NEXT_SESSION_PLAN.md first, then verify both repositories with
`git rev-parse HEAD origin/main` and `git status` before trusting anything in
it. Both should be on main, clean, and 0/0 with origin.

Do not rebuild what section 2 lists as already working -- in particular the
provider protocol, CanonicalFinancialContext, the eight migrated services, the
tool-eligibility gate, or the retrieval path.

Start with section 3.1: 25% of the producer's chunk corpus is table-extraction
debris that scores higher on importance than real prose, so it wins the
fallback ranking. Fix it in FinancialReports at generation time (PDF table
handling, and _score_chunk rewarding digit density) rather than filtering at
read time. Re-ingest is safe now -- extraction is idempotent -- but must go
through `fr run --stages extract,validate,insights --force`, never
`fr extract` alone.

Read section 5 before writing tests or CI: data/ is gitignored, skipped tests
look like passing ones, and deterministic tests cannot tell you a design
decision was wrong. Verify against the real corpus, not just the suite.

Use small commits with exact-path staging, run the gates in section 4, keep CI
green, update this handoff, and return both repos to synchronized main.
Confirm before any push, PR, or merge.
```
