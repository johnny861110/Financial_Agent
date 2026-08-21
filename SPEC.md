# Financial Agent Technical Specification

**Version:** 2.0

**Status:** Current implementation plus explicit roadmap

## Product Scope

Financial Agent provides auditable financial-statement analytics through
FastAPI and Streamlit. It combines deterministic financial services with a
LangGraph research workflow. Raw filing ingestion, parsing, validation, and
canonical evidence belong to FinancialReports.

## Implemented Functional Requirements

### Data Access

- Support local enhanced JSON and FinancialReports API v1 providers.
- Normalize both sources into one `SnapshotRecord` contract.
- Expose source, schema version, freshness, quality, status, metrics, events,
  and evidence.
- Retry transport/5xx failures and support controlled JSON fallback.
- Never fallback on remote 404 or 422 responses.
- Return stale cached remote data during an outage when available.
- Expose readiness, refresh, and ingestion-job status through FastAPI.

### Financial Analysis

- Single-period snapshot and derived margins/ratios.
- Multi-period trend analysis.
- Peer comparison and factor proxies.
- Management quality from caller-supplied governance inputs.
- Earnings quality, ROIC/WACC, capital allocation, and early warnings.
- Structured missing-field errors when a calculation lacks required facts.

Financial formulas are deterministic Python code. Assumptions such as beta,
tax rate, risk-free rate, or caller-supplied governance values must be returned
as assumptions rather than evidence.

### Agent Research

- Accept `auto`, `quick`, and `research` execution modes.
- Parse stock, period, intent, peer universe, and supported assumptions.
- Check data readiness before executing financial tools.
- Build a deterministic and inspectable tool plan.
- Gate tools when required fields are known to be missing.
- Normalize tool failures instead of terminating the entire research run.
- Detect contradictions across successful findings.
- Return verdict, thesis, findings, evidence, risks, data gaps, watch items,
  contradictions, and numeric confidence.
- Operate without an LLM; use an LLM only for optional classification and
  constrained report composition.

### API and UI

- Preserve `POST /api/agent/query` compatibility.
- Provide full research through `POST /api/agent/research`.
- Run blocking services and graph execution outside the async event loop.
- Make Streamlit consume FastAPI rather than import backend services.
- Provide process liveness and provider-aware readiness endpoints.

## Non-Functional Requirements

| Area | Requirement |
| --- | --- |
| Explainability | Material findings carry evidence or are identified as assumptions |
| Reliability | Provider failures have typed behavior and do not become opaque 500s |
| Compatibility | Existing snapshot and financial API shapes remain available |
| Testability | Unit tests do not require a live external service or telemetry |
| Security | Secrets come from environment variables and must never be committed |
| Observability | Langfuse is optional and may not prevent startup unless explicitly required |
| Performance | Remote timeouts/retries are bounded; sync work runs in a thread pool |

## FinancialReports API Dependency

Required remote endpoints:

```text
GET  /v1/filings/{stock_code}/{period}/snapshot
GET  /v1/filings/{stock_code}/{period}/context
GET  /v1/stocks/{stock_code}/periods
GET  /v1/stocks
POST /v1/filings/{stock_code}/{period}/refresh
GET  /v1/jobs/{job_id}
```

Periods use `YYYYQn`. The snapshot response contract and acceptance criteria
are detailed in `MODIFICATION_PLAN.md`; a fixture is maintained at
`tests/fixtures/financial_reports_snapshot_v1.json`.

## Explicit Non-Goals for Version 2.0

- Autonomous trading or order execution
- Raw PDF/XBRL parsing inside Financial Agent
- Fabricated sentiment or guidance output
- Durable Agent memory or long-running workflow persistence
- Multi-agent bull/bear/portfolio-manager debate
- Target-price generation or portfolio sizing
- PostgreSQL, Redis, pgvector, and PDF investment memo export

## Roadmap

### Priority 1: Source Integration

- Deploy FinancialReports API v1 and run consumer-driven contract tests.
- Add immutable filing/document/page references to every canonical fact.
- Add idempotent refresh jobs and durable job status.

### Priority 2: Production Controls

- Add authentication, authorization, rate limits, audit logs, and request IDs.
- Move cache and workflow/job state to shared durable infrastructure.
- Add metrics for source latency, fallback rate, stale reads, tool errors, and
  evidence coverage.

### Priority 3: Research Depth

- Add cash-flow statement details and audited market/macro inputs.
- Add transcript and guidance ingestion before enabling their Agent tools.
- Add report evaluation, citation checks, and analyst approval workflows.
- Consider additional Agent roles only after evidence quality and evaluation
  thresholds are measurable.

## Acceptance Criteria

The version is acceptable when provider, readiness, tool-contract, workflow,
service, and API tests pass; mypy and formatting checks pass; architecture and
API docs match runtime behavior; and GitNexus reports no circular imports.
