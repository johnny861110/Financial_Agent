# Next Session Handoff

**Last updated:** 2026-10-22

Read this first. It states what exists, what to do next, and the traps that
have already cost time. It is deliberately not a history of how things got
here — merged PRs carry that.

---

## 1. Where things stand

| | Financial_Agent | FinancialReports |
| --- | --- | --- |
| repo | `johnny861110/Financial_Agent` | `johnny861110/FinancialReports` |
| local | `/mnt/c/Users/johnn/GITHUB_REPO/Financial_Agent` | `/mnt/c/Users/johnn/GITHUB_REPO/FinancialReports` |
| latest merged PR | #23 | #14 |
| open work | none | none |
| tests | 238 | 200 |
| CI | gates + cross-repo smoke | gates on 3.10/3.11/3.12 |

**GitHub is back** (the suspension noted in earlier versions of this file is
over). Everything is pushed; there is no `gh` CLI here by choice — push with
git and open PRs from the `pull/new/<branch>` link. PR numbers are used rather
than commit SHAs because any SHA written here is stale the moment the file is
committed. Confirm the real state at session start:

```bash
git rev-parse HEAD origin/main && git status --short
```

**Do not delete or commit `.claude/` in either repo** (it is ignored; it holds
local tool settings). `AGENTS.md` and `CLAUDE.md` are now tracked in both
repos; `gitnexus analyze` rewrites their index stats, and those changes go in
their own `chore: refresh GitNexus index stats` commit, never a feature commit.

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
| React research workbench (Streamlit `ui/` is gone) | `frontend/` |
| Ticker validation; company name → code resolution | `app/agents/workflow.py` (`_TICKER_PATTERN`, `_codes_named_in`) |
| Company names / industry / market from TWSE+TPEx open data | `FinancialReports/src/sources/mops_client.py`, `fr backfill-companies` |
| One identity builder for snapshot, refresh, job and batch | `FinancialReports/src/api/service.py` (`build_identity`) |
| `stale` = held copy predates the quarter's filing deadline + grace | `FinancialReports/src/api/freshness.py` |
| Peer comparison as per-company evidence rows | `app/agents/tools.py` (`tool_peer_compare`) |
| Citation / empty-section rules enforced on every answer | `app/agents/workflow.py` (`_enforce_answer_rules`) |
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

### 3.0 FinMind durations carry a year-to-date label on single-quarter values

Found 2026-10-22 while checking 7418. FR labels every duration fact with
`quarter_to_dates` (`src/normalize/period_normalizer.py`), which assumes
Taiwan's cumulative convention: Q2 = Jan–Jun, Q3 = Jan–Sep, Q4 = Jan–Dec. But
FinMind's `TaiwanStockFinancialStatements` gives **single-quarter** values for
quarterly filers. 2330 2026Q2 `eps_basic` is 27.25 with period 2026-01-01 →
2026-06-30, while its PDF (p.33) shows 27.25 for 115年4月1日至6月30日 and 49.33
for 1月1日至6月30日. Every `finmind` duration fact on a Q2/Q3/Q4 filing has this
mislabel (~600 rows); Q1 is correct.

The exception is an emerging-board (興櫃) company. It files no Q1 report, so
its Q2 values really are Jan–Jun: 7418 2026Q2 `eps_basic` 2.6 matches 2.60 for
115年1月至6月 (PDF p.22). Today both cases share the same label, so nothing
downstream can tell a 3-month figure from a 6-month one.

Impact so far is small. Financial_Agent only passes `period_start` through
(`app/data/models.py`). 7418 (觀光餐旅) shares no industry with the rest of the
corpus, so no peer comparison yet mixes it with a quarterly filer. Fix it in FR
before adding more emerging-board companies or any metric that sums or
annualises durations: label FinMind values as the single quarter, and the
half-year when the filer has no previous-quarter report.

Closed on 2026-10-22 (FR #14 and the data steps after it): the 7418 Q1 shell
is gone and its 2026Q2 report is ingested. FR reads the 興櫃 company directory.
`stale_after_seconds` defaults to the 14-day grace period.

### 3.1 Unsupported-claim rate — the missing evaluation

`evaluation/` measures tool gating, citation coverage and contradiction recall,
all exactly, because all are deterministic. **Unsupported-claim rate is
absent**, deliberately: it is a property of generated prose, so measuring it
without a model means inventing a proxy and then trusting the proxy.

It needs a harness running with `LLM_ENABLED=true` that compares each claim in
the answer against the report and the retrieved passages. **This is the measure
that would catch the agent asserting something no evidence supports** — the
single most valuable thing still missing.

### 3.2 Section labels — fixed upstream 2026-09-06, and the conclusion changed

The guess recorded here was that detection ran sections to the document end.
Measurement refuted it: detection is page-granular, and `風險管理` was matching
mid-sentence prose, so `risk` swallowed 26.9% of the corpus across 418 separate
sections. The producer now requires headings to look like headings and segments
notes by their numbering; `risk` fell to 1.4% and 885 distinct note titles
appeared.

Section filtering nonetheless **stays off by default**, for a different reason
than before. Everything in the notes now resolves to the single type `note`
(63.3% of chunks), so filtering by type is a weak instrument regardless of
label quality. `section_title` is the usable topic signal — 885 titles against
a dozen types. If a future consumer wants topical narrowing, build it on titles.

Two consumer-side consequences were fixed the same day: the `NARRATIVE_SECTIONS`
mapping still named `notes`, which is down to 0.8%, and the workflow was
discarding successfully retrieved passages for any question outside a
hand-written topic allowlist — 6 of 8 narrative questions lost their evidence
before the model saw it.

### 3.3 Phase F production controls

None of these exist: authentication, rate limits, request IDs, durable jobs,
shared cache. The service should not be called production-ready without them.

### 3.4 Deferred with reasons — do not "finish" these blindly

- **Supported company sectors** in `ToolRequirements`.
  `FilingIdentityRecord.industry` exists in the model but nothing populates or
  reads it, and the JSON provider builds no identity at all. Needs a real
  producer for sector data first, or it is a gate with no input.
- ~~**`get_context` raises on a producer 409**~~ — resolved 2026-09-06, and the
  reasoning above turned out to be wrong. Leaving it to raise meant the raw
  httpx error reached the user's data-gap list carrying the internal service
  URL, the percent-encoded question and a link to MDN's 409 page, presented as
  though it were a finding about the filing. The producer now distinguishes
  `filing_has_no_source_documents` (permanent, retryable false) from a real
  outage, and both paths treat it as absent data. End-to-end testing found
  this; unit tests on either side could not, because each side was correct
  about its own half.
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
# Port 5433 on this machine: FinancialReports/.env sets POSTGRES_PORT=5433 to
# avoid colliding with the local Postgres already on 5432.
export FR_DATABASE_URL="postgresql+psycopg://financial:financial@localhost:5433/financial"
uv run uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8010
```

The `financialreports_pgdata` volume holds the corpus (2026-10-22): **70
filings, all `insight_ready`**; **24,152 chunks, all embedded** with
`BAAI/bge-base-zh-v1.5`; 14 of 15 companies named (the 15th, 9999, is a test
row with no filings). 7418 香繼光 is emerging-board (興櫃): it files only
half-year and annual reports, so it has no Q1/Q3 filings, and its 2026Q2
figures are Jan–Jun (§3.0). It is local only — not committed, not deployed.

Re-ingesting a filing is
`fr run <stock> <year> <Qn> --stages extract,validate,insights --force`, about
40 s each. Re-extraction deletes a document's chunks and cascades to
`chunk_embeddings`, so **always finish with `fr embed`** (`--stock <code>` to
limit it; already-embedded chunks are skipped) or the filing silently drops to
importance-order retrieval.

To fetch a filing that never got a source document, refresh it through the
API, which runs ingest → extract → validate → insights but **not** embed:

```bash
curl -s -X POST localhost:8010/v1/filings/<stock>/<period>/refresh   # -> job_id
curl -s localhost:8010/v1/jobs/<job_id>                               # until succeeded
FR_DATABASE_URL=... HF_HUB_OFFLINE=1 .venv/bin/fr embed --stock <stock>
```

Claude Code's auto mode refuses that POST as a shared-resource change; the
user runs it with `! curl ...`. Refreshing a settled quarter changes nothing.

### Gates

```bash
# Financial_Agent
.venv/bin/pytest -q
FINANCIAL_DATA_PATH=/tmp/nonexistent .venv/bin/pytest -q   # must also pass
.venv/bin/mypy app/data app/agents app/api app/services app/models/agent_models.py app/models/api_models.py evaluation
.venv/bin/black --check app tests evaluation
.venv/bin/python -m compileall -q app tests evaluation
git -c core.whitespace=cr-at-eol diff --check
npx gitnexus analyze --force

# FinancialReports (needs a running db). Tests default to 5432, the CI port;
# locally the db is on 5433, so point the disposable test database there --
# without it, 67 tests error with ConnectionTimeout and look like a regression.
export FR_TEST_DATABASE_URL=postgresql+psycopg://financial:financial@localhost:5433/financial
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/ scripts/
uv run mypy src/ --ignore-missing-imports
uv run pytest tests/
```

```bash
# Financial_Agent, against the built image rather than the source tree
./scripts/container_smoke.sh

# The release gate: 8 scenarios, each one a bug that reached a user
uv run python scripts/golden_check.py
```

```bash
# Base compose now starts the API and the React workbench. Streamlit is gone.
docker compose up -d          # -> workbench http://localhost:8080, API :8000
```

**On this machine the API runs the working tree, not the image.** A local,
gitignored `docker-compose.override.yaml` (a copy of `docker-compose.dev.yaml`)
mounts `./app` and runs uvicorn with `--reload`, so edits apply without a
rebuild. Delete it and `docker compose up -d api` to go back to the image.

```bash
# FinancialReports image: build on the host network. Its compose has no
# `network: host`, and docker0's MTU (1500) exceeds eth0's (1280), so
# `docker compose build` stalls mid-download.
docker build --network host -t financialreports-api:latest .
docker compose up -d --no-build api
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

**Port 8000 serves whatever branch is checked out.** Because of the compose
override in §4, `git switch` changes live behaviour within seconds — switching
to a main that lacks an unmerged fix silently reverts it in the running
service. "It works in the container" no longer proves the image works either;
`./scripts/container_smoke.sh` still tests the image.

**The embedding model lives only in the host's HF cache, and the producer
cannot fetch it.** `financialreports-api` mounts `~/.cache/huggingface` with
`HF_HUB_OFFLINE=1`. On 2026-09-18 that directory was deleted; docker recreated
the bind-mount source as an **empty, root-owned** directory, and every question
silently fell back to importance ordering (`retrieval.mode` is not `semantic`,
`retrieval_score` null, and the agent's `data_gaps` says "embedding model is
unavailable"). Fix: give the directory back to uid 1000
(`docker exec -u root financialreports-api-1 chown 1000:1000 /home/appuser/.cache/huggingface`)
and `.venv/bin/huggingface-cli download BAAI/bge-base-zh-v1.5`. No restart needed.
Clearing `~/.cache` breaks RAG again.

**A placeholder written as data is never corrected.** When MOPS refused the
company-info lookup, the producer stored the stock code as the company name;
the next lookup found the row and stopped, so all 15 companies were named by
their codes for weeks. MOPS's `ajax_t05st03` and `ajax_t164sb03` now answer
"FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED" with HTTP 200 — check the
body, not the status. The pipeline does not depend on either: PDFs come from
doc.twse and facts from FinMind. XBRL URLs are all 404 and always were.

**Fixing data can surface a latent bug downstream.** Backfilling real names
broke the peer summary, which had matched stock codes against company names as
text and only worked while names *were* codes. After any producer data change,
re-run a peer comparison and a named-company research query live.

**`_TICKER_PATTERN` accepts only `\d{4,6}[A-Z]?`.** That is what stops an LLM's
"台積電" overwriting `2330`, but it would also reject an alphabetic code such as
`TSLA` (see the filing-key note below). `/v1/stocks` holds only numeric codes
today; if a non-numeric ticker is added, validate against the provider's stock
list instead of widening the regex — widening it lets "TSMC" through.

**A flag nobody can clear stops carrying information, and the agent acted on
it anyway.** Until 2026-10-21 the producer's `stale` meant "fetched more than
24 hours ago", so all 70 filings were stale. This agent turned that into a
"latest data is stale" risk and a confidence penalty on quarters final for
months. It now means the held copy predates the quarter's filing deadline
plus 14 days (`FR_STALE_GRACE_DAYS`); 0 filings are stale. If stale ever
reads true for a settled quarter again, suspect the definition first.

**A rule in the prompt is a request, not a guarantee.** The composer prompt
forbids attaching a passage citation to a figure and writing "矛盾：無"; the
model did both, and also shortened `[市場風險 · p.39 · chunk 123]` to
`【市場風險 · p.39】`, which a check keyed on chunk ids would miss.
`_enforce_answer_rules` now removes these after the answer exists and logs
each removal (`Composer broke an answer rule`). A rule that decides whether an
answer can be trusted belongs in code; check the logs after changing the
prompt.

**A tool that returns no evidence silently borrows the primary company's.**
The research executor fills a tool's empty `evidence` with the state's
evidence. The peer tool returned none, so the composer saw only 2454's figures
and answered "比較聯發科和台積電" about 聯發科 alone. Any new multi-company
tool must emit its own rows.

**`detect_changes` on a stale index reports symbols you never touched.** An
insertion shifts every later line, and the stale index maps those lines to the
wrong symbols (47 "changed" for a two-hunk diff). Run `gitnexus analyze` after
merging, and read `git diff -U0 | grep ^@@` when the count looks wrong.

**A suite that skips its integration tests still exits 0 -- both repos had
this, and both now fail loudly instead.** FinancialReports without
`FR_DATABASE_URL` reported "94 passed, 56 skipped", hiding every storage,
contract and pipeline-chain test. Financial_Agent reported "217 passed, 5
skipped", and those 5 were the cross-repo smoke test -- the *only* coverage of
the consumer/producer seam, skipped all day while the producer was running.

Both are easy to hit while doing everything right: the producer's default URL
points at 5432 but compose publishes 5433 (langfuse holds 5432), and this
repo's `.env` points at the compose hostname `http://financial-reports:8010`,
which resolves only inside the compose network -- and pytest does not read
`.env` regardless.

Unreachable dependencies are now errors on both sides, with an explicit
opt-out: `FA_ALLOW_SMOKE_SKIP=1` here, `FR_ALLOW_DB_SKIP=1` there. Configured
runs are 238 and 200 (2026-10-22).

**Two config files disagree with the code about sampling temperature.**
`docker-compose.yaml` defaulted `LLM_TEMPERATURE` to 1.0 against `config.py`
and `.env.example`'s 0.0, so every containerised run composed financial figures
at full sampling temperature; a run under it reported revenue as 10,485,855
against a filed 10,484,855. The compose default is fixed, but compose also
substitutes from `.env`, and the local `.env` still pins `LLM_TEMPERATURE=1.0`
and `LLM_MODEL=gpt-3.5-turbo` -- whose 16,385-token window is what the composer
overflowed. Check the value **inside** the container
(`docker exec financial-agent-api printenv LLM_TEMPERATURE`), not in the
compose file.

**The full test suite passing says nothing about research mode.** No test
exercises the LLM, so `POST /api/agent/research` returned 500 for every query
while 211 tests were green. The composer serialised the whole research report
into the prompt, and because each tool's evidence appears both inline under
`findings` and again under `supporting_evidence`, a real run reached ~43k
characters and blew a 16k context window -- failing *after* every tool had
already succeeded. Fixed 2026-09-06 by `_composer_report_view` (43k -> 3.7k).
Curl the research endpoint against live data before believing the agent works.

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
it. Both should be on main and clean.

Do not rebuild what section 2 lists as already working -- in particular the
provider protocol, CanonicalFinancialContext, the eight migrated services, the
tool-eligibility gate, the retrieval path, or the chunk-legibility work just
landed in FinancialReports/src/parsers/.

Remember that port 8000 runs the checked-out branch. Section 3.0 describes a
period-label bug in FinancialReports' FinMind facts; it does not block, but
fix it before summing or annualising durations. Start with section 3.1: unsupported-claim
rate is the one evaluation still missing, and it is the measure that would catch the agent asserting something
no evidence supports. It needs a harness running with LLM_ENABLED=true that
checks each claim in an answer against the report and the retrieved passages.
Note that this spends the user's API credits -- say so before running it.

Read section 5 before writing tests or CI: data/ is gitignored, skipped tests
look like passing ones, a handoff's stated cause is only a hypothesis, an exact
metric can still be measuring the wrong thing, and deterministic tests cannot
tell you a design decision was wrong. Verify against
the real corpus, not just the suite.

Use small commits with exact-path staging, run the gates in section 4, keep CI
green, update this handoff, and return both repos to synchronized main.
Confirm before any push, PR, or merge.
```
