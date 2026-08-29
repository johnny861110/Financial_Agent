# Next Session Handoff Plan

**Prepared:** 2026-08-28 (updated same day: EarningsQuality/EWS, then
ROIC-WACC/CapitalAllocation migrations)

**Milestone:** Canonical financial context foundation and Snapshot/Trend migration complete

**Next milestone:** Complete schema-aware analysis and filing-text retrieval

**Session update (2026-08-28, same day):** `EarningsQualityService` and
`EarlyWarningService` are migrated onto `DataLoader.load_context()`. PR #5
(branch `refactor/earnings-quality-ews-canonical-context`, commits `83ac9a7`
quality, `57d989c` ews, `41fafb5` docs) was merged as `3420e9d`.

Same day, later: `ROICWACCService` and `CapitalAllocationService` are also
migrated onto `DataLoader.load_context()`. PR #6 (branch
`refactor/roic-wacc-capital-allocation-canonical-context`, commits `2ef7e0b`
roic, `194c1fe` capital, `3bdace0` docs) was merged as `c1e0293`.

Same day, later still: `PeerService` and `FactorService` are migrated too.
PR #7 (branch `refactor/peer-factor-canonical-context`, commits `bcd3865`
peers, `ac98562` factors, `6cbd744` docs) was merged as `46247ef`; local and
remote `main` are synchronized (`0/0` ahead/behind) and the feature branch
was deleted locally and remotely. Gates were green before merge (70 pytest
tests, mypy/black/compileall/whitespace/fsck clean, GitNexus re-indexed at
1,664 nodes / 2,869 edges / 0 import cycles). **This completes Phase B's
entire service migration order** (Snapshot, Trend, EarningsQuality/EWS,
ROIC-WACC/CapitalAllocation, Peer/Factor — all five items done).

CI was then added (`.github/workflows/ci.yml`, PR #8 merged as `b58d780`) —
the repository had none, so PRs #5–#7 all merged on locally-run gates alone.
Adding it surfaced two tests that silently depended on the gitignored `data/`
directory and could not pass on a fresh clone; both were made hermetic. See the
Phase A checklist and the hermeticity note below.

**Phase C (schema-aware tool contracts) is now complete** — PR #9, merged as
`458001e`: all 11 tools declare `ToolRequirements`,
eligibility is decided before invocation from canonical field states, and
`ToolResult` explains blocked fields and rules. Implementing it uncovered that
the previous gate both had drifted (ews missing `cash_and_equivalents`, factor
ungated) *and* was dead code under the default JSON provider. One dimension —
supported company sectors — was deliberately deferred; see Phase C below for
why.

**Phase D (filing text retrieval) is complete**, and it required work in the
producer first. FinancialReports moved from SQLite to **PostgreSQL + pgvector
in containers** (FinancialReports PR #4, merged as `96abffd`) and then gained
question-directed retrieval (PR #5, merged as `8d15993`). The consumer side is
this branch. Three findings shaped it:

1. The producer contract could not support Phase D as written: the context
   endpoint had no `question` parameter, and its internal `search_keyword` did
   `content LIKE '%<entire question>%'` — a whole natural-language question as
   one substring, which matches nothing.
2. `FinancialReportsProvider.get_context` accepted `question` and **silently
   dropped it**, so every context request was ranked by static importance.
3. **94% of chunks in the corpus are duplicates** (323,338 redundant of
   342,174). This predates the migration — content hashes proved the SQLite
   copy was faithful — but it defeats bounded retrieval, so results are now
   deduplicated by content. Fixing the ingestion duplication at its source is
   still open.

## 1. Handoff Objective

Continue from the completed cross-repository integration and canonical-context
foundation without rebuilding the provider, API boundary, or context accessors.
The next session should migrate the remaining analysis services and make Agent
tool eligibility use FinancialReports schema metadata.

Phase A merge and local deployment validation are complete. The immediate goals
are now:

1. Continue migrating services onto the implemented canonical financial context.
2. Make tool planning and execution respect units, availability, validation,
   freshness, and evidence coverage.
3. Add question-directed filing-text retrieval with traceable citations.
4. Prepare production deployment controls and environment-specific configuration.

## 2. Current Repository State

### Financial_Agent

- Repository: `johnny861110/Financial_Agent`
- Local path: `/mnt/c/Users/johnn/GITHUB_REPO/Financial_Agent`
- Canonical-context implementation merge: `fabb4ea4ed7bdf731896b419ed5bd1fdf6e90469`
- Integration PR: <https://github.com/johnny861110/Financial_Agent/pull/1>
- Closure-document PR: <https://github.com/johnny861110/Financial_Agent/pull/2>
- Canonical-context PR: <https://github.com/johnny861110/Financial_Agent/pull/3>
- All three PRs merged on 2026-08-28
- EarningsQuality/EWS migration PR: <https://github.com/johnny861110/Financial_Agent/pull/5>,
  merged as `3420e9d` on 2026-08-28
- ROIC-WACC/CapitalAllocation migration PR: <https://github.com/johnny861110/Financial_Agent/pull/6>,
  merged as `c1e0293` on 2026-08-28
- Peer/Factor migration PR (completes Phase B): <https://github.com/johnny861110/Financial_Agent/pull/7>,
  merged as `46247ef` on 2026-08-28
- CI and test-hermeticity PR: <https://github.com/johnny861110/Financial_Agent/pull/8>,
  merged as `b58d780` on 2026-08-28
- Schema-aware tool contracts PR (Phase C): <https://github.com/johnny861110/Financial_Agent/pull/9>,
  merged as `458001e` on 2026-08-29

The implementation SHA intentionally identifies the code milestone before this
handoff-only PR. At session start, use `git rev-parse HEAD origin/main` to read
the final handoff merge SHA.

Feature commits before this handoff:

```text
cddba2e feat(data): consume complete FinancialReports v1 schema
621dd17 feat(agent): expose rich financial evidence records
857f45f docs: document complete FinancialReports integration
e2be6d1 docs: add next-session handoff plan
7699d2f fix(ui): avoid eager page imports
b2c9dcc feat(data): add canonical financial context
823e8aa docs: document canonical context phase
```

### FinancialReports

- Repository: `johnny861110/FinancialReports`
- Local path: `/mnt/c/Users/johnn/GITHUB_REPO/FinancialReports`
- Current main: `e8678c5b419987237dcf4153ea5fa563542d87d2`
- Baseline PR: <https://github.com/johnny861110/FinancialReports/pull/1>
- API PR: <https://github.com/johnny861110/FinancialReports/pull/2>
- Documentation-sync PR: <https://github.com/johnny861110/FinancialReports/pull/3>
- All three PRs merged on 2026-08-28

PR #3 passed the Python 3.10, 3.11, and 3.12 matrix. All temporary producer
branches were deleted locally and remotely.

At implementation closure, both repositories were on `main`, local HEAD matched
`origin/main`, ahead/behind was `0/0`, and the remotes contained only `main`.
GitNexus was current on both merge commits: Financial Agent had 1,546 nodes,
2,497 edges, 37 clusters, and 107 flows; FinancialReports had 1,568 nodes,
2,745 edges, 37 clusters, and 83 flows.

Do not delete or commit these pre-existing untracked FinancialReports paths
without explicit user instruction:

```text
.claude/
AGENTS.md
CLAUDE.md
examples/batch_2025_missing.json
```

## 3. Phase A Closure Record

Completed on 2026-08-28:

1. FinancialReports PR #1 merged as `0b7f41c`.
2. FinancialReports PR #2 retargeted to `main`, synchronized, and passed CI.
3. FinancialReports PR #2 merged as `8ba3cfc`.
4. FinancialReports `main` started locally and reported schema `1.0.0` ready.
5. Financial Agent ran with `ALLOW_JSON_FALLBACK=false` against producer main.
6. Capabilities, rich record, stale readiness, and financial analysis passed for
   `2330/2025Q1` using the existing FinancialReports database.
7. Financial_Agent PR #1 merged as `58a4de1`.
8. Financial_Agent closure PR #2 merged as `82bf6f4`.
9. Financial Agent canonical-context PR #3 merged as `fabb4ea`.
10. FinancialReports documentation-sync PR #3 merged as `e8678c5`.

No production deployment target or credentials were provided. Keep
`DATA_PROVIDER=json` as the repository default until a target environment passes
the same readiness and filing-query checks.

After every merge, fetch and fast-forward local `main`; verify local and remote
SHA equality before deleting feature branches.

## 4. Completed Capability Boundary

Do not reimplement these capabilities:

- FinancialReports HTTP API v1, OpenAPI artifact, health and readiness.
- Filing snapshot and context endpoints.
- Stock and period pagination.
- Refresh and in-process job endpoints.
- Capabilities, schema discovery, and bounded batch query.
- Financial_Agent provider protocol, retry, stale cache, and controlled fallback.
- Typed processing behavior for `filing_not_ready`.
- Rich `SnapshotRecord` transport models.
- Data capabilities and rich-record Agent endpoints.
- Agent readiness, deterministic planning, typed tool execution, contradiction
  review, evidence verification, and structured report composition.
- Fact-level evidence transfer into Agent state.
- `CanonicalFinancialContext` accessors for facts, units, field states,
  producer metrics, validation failures, freshness, and evidence.
- Snapshot and Trend migration onto `DataLoader.load_context()`.
- Missing-safe ratio and trend behavior plus typed unit mismatch failures.

The cross-repository smoke test already proved this path:

```text
FinancialReports 1.0.0
    -> FinancialReportsProvider
    -> SnapshotRecord
    -> CanonicalFinancialContext
    -> Snapshot / Trend
    -> deterministic financial endpoint and Agent evidence
```

## 5. Current Data Utilization Gap

Transport coverage is high. Snapshot and Trend now consume the canonical
context, but analysis utilization remains incomplete elsewhere.

| FinancialReports data | Transported | Actively used |
| --- | --- | --- |
| Filing identity | Yes | Partially |
| Normalized snapshot | Yes | Yes |
| Canonical facts and units | Yes | All eight deterministic services use `load_context()`. CapitalAllocationService and PeerService only need it for existence/skip checks (no hard required-field gate for either); Snapshot/Trend/EarningsQuality/EWS/ROIC-WACC/FactorService also declare and enforce required fields |
| Fact evidence text | Yes | Yes, bounded fact-level excerpts |
| Quality, missing fields, freshness | Yes | Yes |
| Field availability states | Yes | Used by every service with a required-field gate, **and by tool planning** — `evaluate_eligibility()` blocks a tool before invocation on any non-`present` required field |
| Validation records | Yes | Surfaced as red flags (EarningsQuality) / signals (EWS) / commentary notes (ROIC-WACC); error-severity failures also feed the planner gate (`blocking_validation_rules`, no tool opts in yet) and lower report confidence |
| Metric records and formulas | Yes | Snapshot/Trend/EWS/ROIC-WACC use producer ratios when available |
| Producer YoY/QoQ comparisons | Yes | Not used by trend analysis |
| Insight cards | Yes | Not used by planner/composer |
| Source documents | Yes | Not exposed as navigable citations |
| Pipeline state | Yes | Not exposed as stage-level progress |
| Context endpoint | Client exists | Not called by the Agent workflow |
| Batch query | Producer only | Not consumed |
| Schema discovery | Producer only | No startup negotiation/drift check |

Snapshot and Trend call `DataLoader.load_context()` and no longer manufacture
zero for an unavailable derived input. The remaining deterministic services
still primarily call `load_snapshot()` and require incremental migration.

## 6. Next Milestone Design

### Implementation Entry Points

Read these files before editing:

| Responsibility | File |
| --- | --- |
| Context model and typed errors | `app/data/context.py` |
| Provider-to-service facade | `app/core/data_loader.py` |
| Rich transport models | `app/data/models.py` |
| First migrated services | `app/services/snapshot_service.py`, `app/services/trend_service.py` |
| Remaining service construction | `app/services/factory.py` |
| Agent tool contracts/execution | `app/agents/contracts.py`, `app/agents/tools.py` |
| Planner and report workflow | `app/agents/workflow.py` |
| Context behavior tests | `tests/test_financial_context.py` |
| Producer contract fixture | `tests/fixtures/financial_reports_snapshot_v1.json` |

Do not change `FinancialSnapshot` computed properties as the first step. The
safe migration pattern is to inject `DataLoader`, load a context, declare each
required field/unit, and retain the public response shape.

### Phase A: Merge, Deploy, and Pin the Contract (Completed Locally)

- [x] Execute the merge order in section 3.
- [x] Lock runtime OpenAPI to the committed producer artifact in tests.
- [x] Verify capabilities and a real filing across both merged codebases.
- [x] Expose the producer schema version through capabilities and readiness.
- [x] Add CI for Financial_Agent's own gates (`.github/workflows/ci.yml`:
      pytest, mypy, black, compileall across Python 3.10/3.11/3.12, plus a
      `uv lock --check` job for dependency drift).
- [x] Extend CI to a smoke job spanning **both** repositories
      (`.github/workflows/cross-repo-smoke.yml`): checks out FinancialReports
      alongside this repository, starts it against a pgvector service
      container, and runs `tests/test_producer_smoke.py` over HTTP. Also runs
      weekly, since the producer can break the contract without this
      repository changing.
- [ ] Deploy to a named production/staging target when one is provided.

Acceptance criteria:

- Both repositories have clean, synchronized `main` branches.
- Producer health reports schema `1.0.0`.
- Consumer starts with `ALLOW_JSON_FALLBACK=false` in the smoke environment.
- Contract drift fails CI with a useful message.

Note on test hermeticity (discovered while adding CI): `data/` is gitignored,
so **no data files are committed**. Any test that constructs a service with a
default `DataLoader()` silently reads the developer's local `data/` directory
and will not reproduce on a fresh clone or in CI. Two ROIC/WACC tests had this
problem and were fixed to inject a provider. When adding tests, inject a
`RecordProvider` from `tests/helpers.py` rather than relying on `data/`, and
sanity-check reproducibility with:

```bash
FINANCIAL_DATA_PATH=/tmp/nonexistent .venv/bin/pytest -q
```

### Phase B: Canonical Financial Context

The service-facing `CanonicalFinancialContext` is implemented with:

- filing identity and lifecycle state;
- canonical facts indexed by field;
- explicit unit and period type;
- `present`, `missing`, `null`, `not_applicable`, and `provider_failure`;
- validation results by rule and severity;
- quality, freshness, and structured-source coverage;
- evidence and source-document references;
- producer metrics and comparisons.

Implemented accessors include:

```text
required_fact(field, expected_unit)
optional_fact(field, expected_unit)
availability(field)
failed_validations(fields)
evidence_for(fields, limit)
optional_value(field, expected_unit)
required_value(field, expected_unit)
metric(name, expected_unit)
ratio_percent(metric_name, numerator_field, denominator_field)
field_states(fields)
```

Migrate services incrementally. Do not rewrite every service in one commit.
Recommended order:

1. Snapshot service - completed
2. Trend service - completed
3. Earnings quality and EWS - completed (PR #5, merged as `3420e9d`)
4. ROIC/WACC and capital allocation - completed (PR #6, merged as `c1e0293`)
5. Peer and factor services - completed (PR #7, merged as `46247ef`)

**Phase B's service migration order is now fully complete.** All eight
deterministic services (Snapshot, Trend, EarningsQuality, EWS, ROIC-WACC,
CapitalAllocation, Peer, Factor) go through `DataLoader.load_context()`.

Acceptance criteria (met by every migrated service):

- Missing values cannot silently become numeric zero.
- `not_applicable` is distinct from missing.
- Unit mismatch produces a typed error.
- Every newly migrated calculated finding records source fact IDs and assumptions.

Immediate next work (first task for the next session): start Phase C
(schema-aware tool contracts) below.

### Phase C: Schema-Aware Tool Contracts — completed

Each of the 11 tools in `TOOL_REGISTRY` declares a `ToolRequirements`
(`app/agents/contracts.py`), registered in `TOOL_REQUIREMENTS`
(`app/agents/tools.py`):

- [x] required fields — imported from the owning service's constant, never
      restated, so the planner and the service cannot disagree;
- [x] expected units (`expected_unit`, plus `extra_unit_fields` for mixed-unit
      tools such as factor's per-share `eps_basic`);
- [x] minimum quality (`min_quality`) and evidence coverage (folded into
      confidence, see below);
- [x] blocking validation rules (`blocking_validation_rules`);
- [x] whether stale data is allowed (`allows_stale`);
- [ ] **supported company sectors — deferred, deliberately.** There is no
      sector data in the pipeline: `FilingIdentityRecord.industry` appears only
      in the model definition and the `app/data/__init__.py` re-export, nothing
      populates or reads it, and `JsonFinancialDataProvider` does not construct
      an identity at all. Shipping the declaration field would be a gate with
      no producer and no consumer. Revisit when the producer actually supplies
      sector on the filing identity.

`evaluate_eligibility()` (`app/agents/tools.py`) decides eligibility, and
`_research_executor_node` calls it before invoking each planned tool.

Two problems this fixed, both found during implementation:

1. **The old gate was drifting.** `workflow.py` hardcoded required fields for 3
   of 11 tools; its `ews` entry omitted `cash_and_equivalents` (the service
   requires 6 fields, the gate checked 5) and `factor` had no entry at all.
2. **The old gate was dead code under the default provider.** It filtered on
   `readiness.missing_fields` = producer-reported `quality.missing_fields`, and
   `JsonFinancialDataProvider` builds `SnapshotRecord` with no `quality`, so
   that list was always empty and the gate could never block. Eligibility was
   effectively "always eligible, discover failure by exception". The gate now
   reads `CanonicalFinancialContext.field_states()`, whose `availability()`
   falls back to inspecting the snapshot, so it is live for both providers.

Acceptance criteria:

- [x] Tool eligibility is deterministic and testable
      (`tests/test_tool_eligibility.py`, 14 tests).
- [x] Tool results explain every blocked field or validation — `ToolResult`
      gained `blocked_fields` (field → state) and `failed_rules`.
- [x] Confidence reflects quality, freshness, validation, and evidence coverage
      (`FinancialAgent._confidence_multiplier`).

Note: no tool currently opts into the `min_quality`, `allows_stale`, or
`blocking_validation_rules` gates — choosing those thresholds is a product
decision, not an engineering one. The machinery is live and covered by tests
that override one tool's declaration, so opting a tool in is a one-line change
rather than new plumbing.

**Phase E (citation and pipeline UI) is complete.** `ui/presentation.py` holds
the display logic as pure functions with no Streamlit import, so it is testable
in CI; the pages render on top of it. Filing passages appear as followable
sources (document URL is the citation; database ids are a detail line; local
paths never surface), missing/null/not_applicable/provider_failure read
differently, validation failures are separated from ordinary gaps, blocked
tools explain themselves field by field, and a failed pipeline stage is named.

**Done since:** the ingestion duplication, the full re-ingest, the
cross-repository smoke CI, and corpus embedding. See "Corpus state" below.

Immediate next work (first task for the next session):

**Phase F: evaluation set and production controls.** Everything upstream of it
is now in place — canonical facts, deterministic tool gating, question-directed
retrieval with citations, and a UI that renders all three. What is missing is
the ability to say whether any of it is *good*: a fixed evaluation set over
complete, partial, stale, invalid, processing and narrative-heavy filings, and
measurement of citation coverage, unsupported-claim rate, tool-gating accuracy,
contradiction recall and verdict stability. Then the production controls
(authentication, rate limits, request IDs, durable jobs, shared cache).

Two smaller items worth knowing about:

- `get_context` raises on a producer 409 while `load_record` returns a typed
  state. That is consistent with the guardrail against silently absorbing
  producer contract errors, so it was left alone, but a caller has to know it.
- The embedding model and dimension are pinned together in
  `src/agent/embedding.py` (`BAAI/bge-base-zh-v1.5`, 768) and asserted at
  encode time against `VECTOR(768)` in `schema.sql`. Changing one without the
  other fails loudly rather than corrupting the index — but both must move
  together, and existing embeddings must be regenerated.

### Phase D: Filing Text Retrieval

The current Agent receives fact-linked evidence excerpts, not general filing
text chunks. Add a bounded, question-directed retrieval contract instead of
sending complete filings to the Agent.

Recommended producer contract:

```text
GET /v1/filings/{stock_code}/{period}/context
    ?question=...
    &sections=...
    &limit=...
```

Each returned chunk should include:

- stable chunk ID;
- document ID and checksum;
- page and section;
- raw text or bounded excerpt;
- source URL;
- retrieval score and extraction method;
- related fact IDs when available.

Financial Agent should request context only for intents that need narrative
evidence, such as accounting-policy changes, risk disclosures, management
discussion, contingencies, and significant events.

Acceptance criteria:

- Numeric questions remain on the structured-fact path.
- Narrative questions retrieve only bounded relevant chunks.
- Every material narrative claim includes a document/page/chunk citation.
- Prompt input has explicit size and chunk-count limits.
- Retrieval failure degrades to a structured data-gap response.

### Phase E: Citation and Pipeline UI

- Add source-document links and page/section labels to Agent findings.
- Display validation failures separately from ordinary warnings.
- Display processing stage and failed pipeline stage.
- Distinguish missing, null, and not-applicable fields visually.
- Do not expose raw internal filesystem paths or database IDs as user-facing
  citations when a stable document URL is available.

### Phase F: Evaluation and Production Controls

- Add a fixed evaluation set for complete, partial, stale, invalid, processing,
  and narrative-heavy filings.
- Measure citation coverage, unsupported-claim rate, tool-gating accuracy,
  contradiction recall, and verdict stability.
- Add authentication, rate limits, request IDs, durable jobs, and shared cache
  before treating the service as production-ready.

## 7. Recommended Commit Sequence

Keep future commits reviewable:

```text
test(contract): add deployed producer smoke matrix
refactor(quality): consume canonical facts and validation
refactor(ews): consume canonical facts and validation
refactor(capital): migrate roic and allocation context
refactor(peers): migrate peer and factor context
feat(agent): add schema-aware tool requirements
feat(data): retrieve bounded filing text context
feat(agent): cite filing text chunks
feat(ui): expose citations and pipeline states
test(eval): add evidence and gating evaluation set
docs: update rich-schema utilization architecture
```

Run GitNexus impact analysis before each shared-model or provider change. Update
the `financial-platform` group after either repository is re-indexed.

## 7b. Corpus state

The producer's corpus lives in the local `financialreports_pgdata` Docker
volume. It is not committed and not deployed anywhere, so these numbers
describe one machine.

| | before | after |
| --- | --- | --- |
| chunks | 342,174 | **19,152** |
| distinct content | 18,836 | **18,836** |
| filings with duplicates | 61 | **0** |
| filings `insight_ready` | 55 | **71** |

The distinct-content count is unchanged, which is the point: the 323,022 rows
removed were all redundant copies, not content. Two independent bugs produced
them and both are fixed at source (FinancialReports PR #6 and #7), so a
re-ingest no longer reintroduces them.

**A trap worth not repeating.** Re-ingesting with `fr extract --force` alone
resets a filing to `extracted`, which strips its validated and insight output
and makes the API answer 409 for it. Always re-ingest through the pipeline:

```bash
uv run fr run <stock> <year> <Qn> --stages extract,validate,insights --force
```

Embeddings are generated with `fr embed` (needs `uv sync --extra vector`), which
skips already-embedded chunks and so is resumable. **All 19,152 chunks are
embedded** with `BAAI/bge-base-zh-v1.5`. On an RTX 3060 laptop that took 26
minutes at roughly 770 chunks/minute -- GPU-bound at 100% utilisation, so a
smaller model is the lever if this needs to be faster. A filing with no
embeddings is not broken: retrieval falls back to importance ordering, so a
partial run degrades rather than fails.

Retrieval was spot-checked across the corpus with Traditional Chinese questions
and returns semantically correct passages -- "公司面臨哪些主要風險" lands on the
risk section's risk-management policy at 0.65, "會計政策有什麼變更" on the IFRS
adoption paragraphs. Note those accounting-policy hits come back tagged
`income_statement`/`cash_flow` rather than `accounting_policy`, because that is
genuinely where the text sits in these filings; vector search finds it
regardless of the section label, which is why `sections` is a filter and not the
ranking mechanism.

**5 of 71 filings have no source document at all** (XBRL figures only, no PDF),
so they have no chunks and no narrative to retrieve. Their numeric path works
normally. An empty `evidence_chunks` for those is the designed degradation, not
a fault.

## 8. Verification Commands

### Financial_Agent

```bash
.venv/bin/pytest -q
.venv/bin/mypy app/data app/agents app/api app/services app/models/agent_models.py ui/api_client.py
.venv/bin/black --check app tests ui streamlit_app.py
.venv/bin/python -m compileall -q app tests ui
git -c core.whitespace=cr-at-eol diff --check
git fsck --full --strict
npx gitnexus analyze --force

# Reproducibility check -- must stay green, CI has no data/ directory
FINANCIAL_DATA_PATH=/tmp/nonexistent .venv/bin/pytest -q
```

The first four commands now also run in CI (`.github/workflows/ci.yml`) on
every push and PR to `main`, across Python 3.10/3.11/3.12. Running them
locally before pushing is still faster than waiting for CI, but CI is now the
authority. Note CI installs with `uv sync --extra dev --frozen`, so a local
`.venv` that has drifted from `uv.lock` can disagree with it; `uv lock --check`
has its own CI job for exactly that reason.

Canonical-context phase baseline: 44 pytest tests passed, 27 source files passed
mypy, 56 files passed Black, and compileall/diff checks passed.

After the EarningsQuality/EWS migration (PR #5, merged as `3420e9d`): 54
pytest tests passed, 27 source files passed mypy, 59 files passed Black, and
compileall/whitespace-diff/`git fsck --full --strict` checks passed (fsck
reports only pre-existing harmless dangling objects, no corruption).

After the ROIC-WACC/CapitalAllocation migration (PR #6, merged as `c1e0293`):
62 pytest tests passed, 27 source files passed mypy, 61 files passed Black,
and compileall/whitespace-diff/fsck checks passed the same way.

After the Peer/Factor migration (PR #7, merged as `46247ef`, completing
Phase B): 70 pytest tests passed, 27 source files passed mypy, 63 files
passed Black, and compileall/whitespace-diff/fsck checks passed the same
way.

After Phase C (schema-aware tool contracts): 84 pytest tests passed — both
with and without a `data/` directory — 27 source files passed mypy, 64 files
passed Black, compileall/whitespace-diff passed, and GitNexus re-indexed at
1,726 nodes / 3,023 edges / 0 import cycles (`workflow.py` now imports
`tools.py` at module level; the cycle check confirms that introduced none).

### FinancialReports

Use the repository's Ruff, mypy, pytest, compile, OpenAPI drift, and Python
matrix checks. At the handoff milestone the producer baseline was:

```text
83 pytest tests passed
54 source files passed mypy
Ruff check and format passed
OpenAPI runtime/artifact drift test passed
Python 3.10/3.11/3.12 PR matrix passed on API and documentation PRs
```

### Cross-Repository

Start FinancialReports with a temporary fixture database, then start Financial
Agent with:

```text
DATA_PROVIDER=financial_reports
FINANCIAL_REPORTS_BASE_URL=http://127.0.0.1:<producer-port>
ALLOW_JSON_FALLBACK=false
LLM_ENABLED=false
LANGFUSE_ENABLED=false
```

Verify:

```text
GET /health/ready
GET /api/data/capabilities
GET /api/data/{stock_code}/{period}/record
GET /api/data/{stock_code}/{period}/status
GET /api/financials/{stock_code}/{period}
```

Stop all temporary servers before ending the session.

## 9. Engineering Guardrails

- Do not connect Financial Agent directly to the FinancialReports database.
  The producer now runs PostgreSQL + pgvector in containers; the contract
  between the repositories is HTTP only.
- Do not move raw PDF/XBRL parsing into Financial Agent.
- Do not let the LLM calculate canonical financial facts.
- Do not interpret missing, null, or not-applicable as zero.
- Do not silently fall back on producer 404, 409 contract errors, or 422.
- Do not send complete filings to the LLM without retrieval and size bounds.
- Preserve existing API compatibility while migrating services incrementally.
- Keep the four protected FinancialReports untracked paths untouched.
- Use exact-path staging and small commits; do not mix generated GitNexus files
  into feature commits.

## 10. Suggested Resume Prompt

Use this prompt at the start of the next session:

```text
Read NEXT_SESSION_PLAN.md first. Verify both repositories, all merged PRs, local
and remote SHAs, and GitNexus financial-platform status. Financial_Agent has
merged PR #5 (EarningsQuality/EWS, at commit 3420e9d), PR #6
(ROIC-WACC/CapitalAllocation, at commit c1e0293), and PR #7 (Peer/Factor, at
commit 46247ef), which completes Phase B's entire service migration order.
PR #8 added CI (at commit b58d780) and PR #9 completed Phase C, schema-aware
tool contracts (at commit 458001e). Do not reimplement the FinancialReports
provider, API, SnapshotRecord mapping, or CanonicalFinancialContext; do not
re-migrate any of the eight services already on DataLoader.load_context(); and
do not rebuild the tool-eligibility gate (TOOL_REQUIREMENTS +
evaluate_eligibility in app/agents/tools.py). Start Phase D (filing text
retrieval): add a bounded, question-directed retrieval contract so narrative
questions get cited filing chunks while numeric questions stay on the
structured-fact path. The producer already exposes
GET /v1/filings/{stock}/{period}/context and FinancialReportsProvider already
has a get_context() client method -- the Agent workflow does not call it yet.
Read Phase D below for the chunk contract and acceptance criteria. Note one
Phase C dimension was deliberately deferred (supported company sectors, no
sector data exists in the pipeline) -- do not "finish" it without first adding
a real producer for FilingIdentityRecord.industry. Preserve the FinancialReports
untracked paths listed in the handoff. Financial_Agent now has CI
(.github/workflows/ci.yml) -- check it is green on any PR before merging, and
note data/ is gitignored, so inject a RecordProvider from tests/helpers.py in
new tests rather than relying on local data files. Use small commits, run both
focused and full gates, refresh GitNexus, update this handoff, merge through
PR, and return both repos to synchronized main. Confirm with the user before
any push/PR/merge step.
```

## 11. Definition of the Next Milestone Done

The next milestone is complete when a narrative and numeric research request
can both be answered from FinancialReports with:

- explicit field states and units;
- deterministic tool eligibility;
- no missing-to-zero conversions;
- fact and filing-text citations;
- validation-aware confidence;
- bounded retrieval;
- reproducible cross-repository tests;
- synchronized, healthy local and remote repositories.
