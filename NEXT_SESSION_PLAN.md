# Next Session Handoff Plan

**Prepared:** 2026-08-28

**Milestone:** FinancialReports v1 producer-consumer integration complete

**Next milestone:** Complete schema-aware analysis and filing-text retrieval

## 1. Handoff Objective

Continue from the completed cross-repository integration without rebuilding the
provider or API boundary. The next session should make Financial Agent actively
use FinancialReports rich schema and filing evidence, instead of only preserving
most rich fields in `SnapshotRecord`.

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
- Phase A closure main: `82bf6f4a7b2c69fce6dabadbaa6fa1f488f451c0`
- Integration PR: <https://github.com/johnny861110/Financial_Agent/pull/1>
- Closure-document PR: <https://github.com/johnny861110/Financial_Agent/pull/2>
- Both PRs merged on 2026-08-28

Feature commits before this handoff:

```text
cddba2e feat(data): consume complete FinancialReports v1 schema
621dd17 feat(agent): expose rich financial evidence records
857f45f docs: document complete FinancialReports integration
e2be6d1 docs: add next-session handoff plan
7699d2f fix(ui): avoid eager page imports
```

### FinancialReports

- Repository: `johnny861110/FinancialReports`
- Local path: `/mnt/c/Users/johnn/GITHUB_REPO/FinancialReports`
- Main: `8ba3cfcbae30f38786661d110b0dc8e1ed9c831d`
- Baseline branch: `fix/finmind-bank-support`
- Baseline HEAD: `6db6a84163f61d5faa74fc5a2dd37a8023ad0290`
- API branch: `feat/versioned-schema-api`
- API HEAD: `c61d8ff62610b7c3a493108fc138c983c17d399b`
- Baseline PR: <https://github.com/johnny861110/FinancialReports/pull/1>
- API PR: <https://github.com/johnny861110/FinancialReports/pull/2>
- PR state at handoff: both merged on 2026-08-28

PR #2 was retargeted to `main`, synchronized with the PR #1 merge commit, and
passed the Python 3.10, 3.11, and 3.12 matrix before merge.

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

The cross-repository smoke test already proved this path:

```text
FinancialReports 1.0.0
    -> FinancialReportsProvider
    -> SnapshotRecord
    -> readiness and Agent evidence
    -> deterministic financial endpoint
```

## 5. Current Data Utilization Gap

Transport coverage is high. Snapshot and Trend now consume the canonical
context, but analysis utilization remains incomplete elsewhere.

| FinancialReports data | Transported | Actively used |
| --- | --- | --- |
| Filing identity | Yes | Partially |
| Normalized snapshot | Yes | Yes |
| Canonical facts and units | Yes | Facts mainly become evidence |
| Fact evidence text | Yes | Yes, bounded fact-level excerpts |
| Quality, missing fields, freshness | Yes | Yes |
| Field availability states | Yes | Used by Snapshot/Trend; not yet by tool planning |
| Validation records | Yes | Not used as rule-specific gates |
| Metric records and formulas | Yes | Not used by analysis services |
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

### Phase A: Merge, Deploy, and Pin the Contract (Completed Locally)

- [x] Execute the merge order in section 3.
- [x] Lock runtime OpenAPI to the committed producer artifact in tests.
- [x] Verify capabilities and a real filing across both merged codebases.
- [x] Expose the producer schema version through capabilities and readiness.
- [ ] Add a CI smoke job spanning both repositories.
- [ ] Deploy to a named production/staging target when one is provided.

Acceptance criteria:

- Both repositories have clean, synchronized `main` branches.
- Producer health reports schema `1.0.0`.
- Consumer starts with `ALLOW_JSON_FALLBACK=false` in the smoke environment.
- Contract drift fails CI with a useful message.

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

Add accessors such as:

```text
required_fact(field, expected_unit)
optional_fact(field, expected_unit)
availability(field)
failed_validations(fields)
evidence_for(fields, limit)
```

Migrate services incrementally. Do not rewrite every service in one commit.
Recommended order:

1. Snapshot service - completed
2. Trend service - completed
3. Earnings quality and EWS
4. ROIC/WACC and capital allocation
5. Peer and factor services

Acceptance criteria:

- Missing values cannot silently become numeric zero.
- `not_applicable` is distinct from missing.
- Unit mismatch produces a typed error.
- Every calculated finding records source fact IDs and assumptions.

### Phase C: Schema-Aware Tool Contracts

Extend each Agent tool definition with:

- required and optional fields;
- expected units;
- minimum quality and evidence coverage;
- blocking validation rules;
- whether stale data is allowed;
- supported company sectors.

Use these declarations in the planner and executor. The LLM must not decide
whether source data is structurally valid.

Acceptance criteria:

- Tool eligibility is deterministic and testable.
- Tool results explain every blocked field or validation.
- Confidence reflects quality, freshness, validation, and evidence coverage.

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
feat(data): add canonical financial context
refactor(snapshot): consume canonical facts and availability
refactor(trend): use producer comparisons with local fallback
feat(agent): add schema-aware tool requirements
feat(data): retrieve bounded filing text context
feat(agent): cite filing text chunks
feat(ui): expose citations and pipeline states
test(eval): add evidence and gating evaluation set
docs: update rich-schema utilization architecture
```

Run GitNexus impact analysis before each shared-model or provider change. Update
the `financial-platform` group after either repository is re-indexed.

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
```

Canonical-context phase baseline: 44 pytest tests passed.

### FinancialReports

Use the repository's Ruff, mypy, pytest, compile, OpenAPI drift, and Python
matrix checks. At the handoff milestone the producer baseline was:

```text
83 pytest tests passed
54 source files passed mypy
Ruff check and format passed
OpenAPI runtime/artifact drift test passed
Python 3.10/3.11/3.12 PR matrix passed on baseline PR
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

- Do not share the FinancialReports SQLite file with Financial Agent.
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
Read NEXT_SESSION_PLAN.md first. Verify both repositories, all four merged PRs, local
and remote SHAs, and GitNexus financial-platform status. Do not reimplement the
existing FinancialReports provider or API. Start with Phase A merge/deployment
readiness; if merges are not authorized, begin Phase B by designing and impact-
continuing the CanonicalFinancialContext service migrations. Preserve the FinancialReports untracked
paths listed in the handoff. Implement, test, commit, and update the handoff as
each phase is completed.
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
