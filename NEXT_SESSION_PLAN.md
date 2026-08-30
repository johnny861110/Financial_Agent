# Next Session Handoff

**Last updated:** 2026-08-30

Read this first. It states what exists, what to do next, and the traps that
have already cost time. It is deliberately not a history of how things got
here — merged PRs carry that.

---

## 1. Where things stand

| | Financial_Agent | FinancialReports |
| --- | --- | --- |
| repo | `johnny861110/Financial_Agent` | `johnny861110/FinancialReports` |
| local | `/mnt/c/Users/johnn/GITHUB_REPO/Financial_Agent` | `/mnt/c/Users/johnn/GITHUB_REPO/FinancialReports` |
| latest merged PR | #16 | #8 |
| open PR | — | **#9, CI green, unmerged** |
| tests | 138 | 122 |
| CI | gates + cross-repo smoke, green | gates on 3.10/3.11/3.12, green |

**FinancialReports PR #9 is open and awaiting merge**: schedule detection plus
the chunk page-attribution fix (see §3.2 and §5). Its CI is green on all three
Pythons. Everything else in both repos is pushed.

PR numbers are used rather than commit SHAs because any SHA written here is
stale the moment the file is committed. Confirm the real state at session
start:

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
| Upright-flag repair in PDF text extraction | `FinancialReports/src/parsers/pdf_text_parser.py` |
| Legibility-scaled chunk importance | `FinancialReports/src/parsers/pdf_section_parser.py` |

Phases A–E and the evaluation half of F are done. Eight of the nine services
read filings through `load_context()` and never treat missing, null or
not-applicable as zero — `ManagementService` is the exception because it scores
caller-supplied assumptions, not filing data. Tool eligibility is decided
before execution; narrative questions retrieve cited filing text.

**The chunk-ranking defect that used to lead §3 is fixed**, and the whole
corpus has been re-ingested through it. Measured over all 19,177 chunks:

| | before | after |
| --- | --- | --- |
| mean importance, debris (<30% letters) | 0.703 | 0.343 |
| mean importance, real prose | 0.652 | 0.459 |
| which wins the fallback ranking | **debris, by 0.052** | **prose, by 0.116** |
| chunks that are one-character-token soup | 3,046 (15.9%) | 2,257 (11.8%) |
| `contains_table` / `contains_numbers` | 1,030 / 1,866 | 12,078 / 14,960 |

Two things the old write-up of it would get wrong, both found by measuring:

- **"25% of the corpus is debris" conflates two different things.** The
  letter-ratio test counts any number-dense chunk, and most of those are
  *correctly extracted* financial statement tables — statements are number-dense.
  That share barely moved (24.96% → 23.89%) and should not be driven to zero.
  Only the character soup was an extraction defect, and the ranking was the
  actual harm. Both are addressed; the letter ratio is a bad health metric.
- **The residual 11.8% soup is not broken extraction.** It is CJK table headers
  the PDF genuinely letter-spaces to justify them across a column
  (`總 帳 面 金 額` for `總帳面金額`). The characters are correct and in order.
  They now score 0.26–0.37 and no longer win anything. Collapsing that spacing
  looks like an easy follow-up and is not — see §3.4.

---

## 3. Next, in priority order

### 3.1 Unsupported-claim rate — the missing evaluation

`evaluation/` measures tool gating, citation coverage and contradiction recall,
all exactly, because all are deterministic. **Unsupported-claim rate is
absent**, deliberately: it is a property of generated prose, so measuring it
without a model means inventing a proxy and then trusting the proxy.

It needs a harness running with `LLM_ENABLED=true` that compares each claim in
the answer against the report and the retrieved passages. **This is the measure
that would catch the agent asserting something no evidence supports** — the
single most valuable thing still missing.

### 3.2 Section labels are still unreliable — partly improved

`split_sections` gives every page to the last detected heading, and it
recognises about ten headings. The largest section therefore swallows most of a
filing, so an auditor's report can be labelled `income_statement`. Section
filtering is **off by default** in `app/agents/retrieval.py`
(`use_sections=True` opts in) for this reason.

FinancialReports PR #9 fixed one trigger of this: 附表 schedules are now their
own section, which moved `accounting_policy` from 2,826 chunks averaging 18.4
pages (max 92) down to 832 averaging 8.0. **It did not fix the general
problem** — the largest section's share of a filing went from 0.651 only to
0.570, and `risk` still holds 26.9% of all chunks across spans reaching 80
pages, because `risk` opens on the single term `風險管理` and then runs until
the next recognised heading.

The next trigger to attack is the numbered note headings Taiwan filings
actually use (`十二、金融工具`, `關係人交易`, `分部資訊`). Measure before
implementing, as PR #9 did: a page-head scan found only 54 of 418 `risk` page
heads carrying a numbered heading, so the naive rule will not be enough on its
own and the measurement should say what is.

**Do not turn `use_sections=True` on** until the largest-share number is
genuinely low. It was measured at 0.570 and that is still one section holding
most of a filing.

### 3.3 Phase F production controls

None of these exist: authentication, rate limits, request IDs, durable jobs,
shared cache. The service should not be called production-ready without them.

### 3.4 Deferred with reasons — do not "finish" these blindly

- **Supported company sectors** in `ToolRequirements`.
  `FilingIdentityRecord.industry` exists in the model but nothing populates or
  reads it, and the JSON provider builds no identity at all. Needs a real
  producer for sector data first, or it is a gate with no input.
- **`get_context` raises on a producer 409** while `load_record` returns a
  typed state. That is consistent with the guardrail against silently
  absorbing producer contract errors, so it was left alone — but callers must
  know it.
- **Un-spacing letter-spaced CJK table headers.** 11.8% of chunks read
  `總 帳 面 金 額` for `總帳面金額`, because the PDF spaces characters out to
  justify a column header. Tempting to fix by joining CJK characters whose gap
  is under some cut. **That was measured and no such cut exists.** The rule
  assumes intra-word spacing is tighter than the gap between two adjacent
  column headers; across 1,639 justified header lines in 15 filings, **38.7%
  invert it**. On `202401_2882_AI1.pdf` p241, `信用損失` is letter-spaced at
  **7.92pt** while the boundary to the next column is only **6.48pt**, and
  `用減損金融資產` in the same row is set at **0.24pt** — any cut that joins the
  first welds it to the second. An equity-statement header on p9 of
  `202401_2317_AI1.pdf` spaces at 27.0pt across boundaries of 9.0pt.

  The column geometry that would resolve it is not available either: these
  pages carry no ruling lines, `find_tables()` returns nothing, and the text
  strategy degenerates to a single 58-row block spanning the page. A correct
  fix must infer column boundaries from the x-positions of the numeric rows
  beneath the header — per-table layout inference, not a text tweak. Weigh that
  against the benefit: row labels and figures are already legible, these
  headers are short and repetitive, and the scoring change already stopped them
  polluting the ranking, which was the actual harm.

---

## 4. Running things

### Producer database and API

```bash
cd /mnt/c/Users/johnn/GITHUB_REPO/FinancialReports
docker compose up -d db          # pgvector/pgvector:pg16
export FR_DATABASE_URL="postgresql+psycopg://financial:financial@localhost:5432/financial"
uv run uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8010
```

The `financialreports_pgdata` volume holds the corpus: **19,177 chunks, all
embedded** with `BAAI/bge-base-zh-v1.5`, zero duplicates, 71 filings
`insight_ready`. It is local only — not committed, not deployed.

All 71 filings were re-ingested through
`fr run <stock> <year> <Qn> --stages extract,validate,insights --force`
followed by `fr embed`, so the corpus reflects the §2 parser fixes. Re-running
that is ~40 s per filing plus one embedding pass. Re-extraction deletes a
document's chunks and cascades to `chunk_embeddings`, so **always finish with
`fr embed`** or the filing silently drops to importance-order retrieval.

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

**`fr run` takes `<stock> <year> <Qn>`, not a filing key.** A re-ingest loop
that passed `2308_2024Q1` as one argument failed every filing while the shell
reported nothing unusual; an earlier loop iterated a store method that does not
exist and printed `0 ok, 0 failed` with exit code 0. Any batch script over the
corpus should assert its input count up front and assert `ok == total` at the
end, so "nothing happened" cannot pass for success. Filing keys come from
`select filing_key from filings`; note that not every code is four digits
(`TSLA_2026Q1` is in the corpus), so do not validate them as numeric.

**A metric can be perfect and still measure nothing.** `citation_coverage`
counts a citation as usable when it carries a page or a URL. It read 100% for
the entire time the producer was stamping every chunk in a section with that
section's first page, so citations across the corpus pointed at the wrong page
of spans up to ninety pages. Well-formedness is not correctness; when a measure
is exact, check what it would fail on.

**A skipped test looks exactly like a passing one.** The cross-repo smoke job
seeds a filing and sets `SMOKE_REQUIRE_DATA=1` so "no data" fails instead of
skipping; the conftest raises instead of skipping when `CI` is set. Preserve
both — without them a broken setup step reports green while testing nothing.

**Background processes outlive their CI step.** uvicorn started with a bare `&`
kept the runner blocked and failed the job five minutes *after* the tests
passed. Start it under `setsid` with stdin closed and reap it in an `always()`
step.

**A handoff's stated cause is a hypothesis, not a finding.** This file used to
blame the garbled-chunk ranking on `_score_chunk` rewarding digit density.
Measured against the corpus before changing anything, that bonus fired on 1.0%
of debris chunks and 3.2% of prose — Taiwan filings group digits with commas,
so `2,394,804,250` has no run of six digits and the `\d{6,}` test almost never
matched. Removing it alone would have *widened* the gap it was blamed for. The
real driver was that debris concentrates in the sections with the highest base
score. Re-measure the mechanism before you fix it; the same comma blindness had
silently reduced `contains_numbers` and the table heuristic to firing on 5% of
a corpus that is a quarter numeric table text.

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
it. FinancialReports PR #9 was open and green when this was written -- check
whether it merged, and merge it if not.

Do not rebuild what section 2 lists as already working -- in particular the
provider protocol, CanonicalFinancialContext, the eight migrated services, the
tool-eligibility gate, the retrieval path, or the parser work in
FinancialReports/src/parsers/ (chunk legibility, schedule detection, chunk
page attribution).

Start with section 3.1: unsupported-claim rate is the one evaluation still
missing, and it is the measure that would catch the agent asserting something
no evidence supports. It needs a harness running with LLM_ENABLED=true that
checks each claim in an answer against the report and the retrieved passages.
Note that this spends the user's API credits -- say so before running it.

Read section 5 before writing tests or CI: data/ is gitignored, skipped tests
look like passing ones, a handoff's stated cause is only a hypothesis, an exact
metric can still be measuring the wrong thing, and deterministic tests cannot
tell you a design decision was wrong. Verify against the real corpus, not just
the suite. If you re-ingest, remember that re-extraction cascades embeddings
away and `fr embed` must follow.

Use small commits with exact-path staging, run the gates in section 4, keep CI
green, update this handoff, and return both repos to synchronized main.
Confirm before any push, PR, or merge.
```
