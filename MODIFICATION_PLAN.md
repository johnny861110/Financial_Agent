# Financial Agent Modification Plan

## Objective

Turn the former single-tool routing agent into an evidence-backed financial
research workflow, while integrating FinancialReports through a stable data
contract and preserving the existing JSON-based behavior during migration.

## Architecture Decision

FinancialReports owns source acquisition, parsing, canonical facts, data
quality, validation, evidence, and basic period comparisons. Financial_Agent
owns higher-order analytics, research planning, tool orchestration, and final
investment-research responses.

**Implementation status:** Financial Agent 2.0 was completed on 2026-08-22.
The complete FinancialReports v1 producer and rich-schema consumer changes were
implemented and contract-tested on 2026-08-24; they remain staged as ordered
pull requests until review and deployment. The implemented system, data-layer,
and Agent-layer diagrams are maintained in `ARCHITECTURE.md`.

The two applications communicate over a versioned HTTP API. They must not
share a SQLite file directly.

```text
MOPS / XBRL / iXBRL / PDF / FinMind
                  |
                  v
           FinancialReports
       ingestion + validation + evidence
                  |
             HTTP API v1
                  |
                  v
       FinancialDataProvider interface
          |                  |
          v                  v
 FinancialReports       Legacy JSON
    provider             provider
          \                  /
           \                /
             DataLoader facade
                    |
             Analysis services
                    |
             Research workflow
```

## Delivery Phases

### Phase 0: Baseline and contracts

- [x] Re-index and inspect the project with GitNexus.
- [x] Record the current test baseline.
- [x] Define the ownership boundary between both projects.
- [x] Define a versioned snapshot response contract.

### Phase 1: Provider abstraction

- [x] Add provider domain models and errors.
- [x] Add a provider protocol.
- [x] Move legacy JSON loading behind `JsonFinancialDataProvider`.
- [x] Add `FinancialReportsProvider` using the HTTP v1 contract.
- [x] Add controlled remote-to-JSON fallback.
- [x] Keep `DataLoader` as a backward-compatible facade.
- [x] Add provider configuration and unit tests.

### Phase 2: Dependency injection and data readiness

- [x] Allow every analysis service to receive an injected data loader.
- [x] Add a shared `DataReadinessService`.
- [x] Propagate ready, processing, stale, low-quality, and failed states.
- [x] Add quality gates for tools with required fields.
- [x] Replace module-level service construction with application factories.

### Phase 3: Tool contracts

- [x] Define one typed result contract for every agent tool.
- [x] Include findings, evidence, warnings, missing fields, and confidence.
- [x] Return `not_supported` for unfinished sentiment and guidance tools.
- [x] Mark user inputs and defaults as assumptions, not source facts.
- [x] Centralize tool response shaping while preserving the public API contract.

### Phase 4: Research workflow

- [x] Add query parsing and explicit research modes.
- [x] Add data-readiness and research-planning graph nodes.
- [x] Execute the required analysis set for broad investment questions.
- [x] Detect contradictions across tool findings.
- [x] Verify that material claims have evidence.
- [x] Produce a structured research report and confidence score.

### Phase 5: API and UI

- [x] Preserve `POST /api/agent/query` compatibility.
- [x] Add `POST /api/agent/research`.
- [x] Add data-status, refresh, and job-status endpoints.
- [x] Run synchronous graph and service work outside the FastAPI event loop.
- [x] Migrate Streamlit pages from direct service calls to FastAPI.
- [x] Display evidence, confidence, risks, and data gaps.

### Phase 6: Operations and verification

- [x] Add liveness and dependency-aware readiness endpoints.
- [x] Disable external LLM and telemetry access in unit tests.
- [x] Add a FinancialReports v1 contract fixture for cross-project use.
- [x] Add timeout, retry, stale-cache, and degraded-mode tests.
- [x] Add end-to-end tests for complete, partial, and missing filings.
- [x] Re-index with GitNexus and review final blast radius.

### Phase 7: Documentation

- [x] Add system, data-layer, and Agent-layer architecture diagrams.
- [x] Document provider ownership, retry, fallback, cache, and readiness rules.
- [x] Update API, local-run, Docker, sample-data, and repository-structure docs.
- [x] Separate implemented behavior from roadmap capabilities.
- [x] Record test results, constraints, and the FinancialReports deployment dependency.

### Phase 8: Complete producer-consumer contract

- [x] Implement the FinancialReports HTTP API v1 and committed OpenAPI artifact.
- [x] Preserve identity, facts, field availability, provenance, validations,
  comparisons, insight cards, source documents, and pipeline state.
- [x] Add discovery endpoints and expose consumer capabilities and rich records.
- [x] Map `filing_not_ready` to a typed processing state instead of an HTTP 500.
- [x] Traverse paginated stock and period collections.
- [x] Lock the shared shape with producer and consumer contract tests.
- [ ] Merge producer baseline PR, producer API PR, then the consumer PR.
- [ ] Deploy FinancialReports and switch `DATA_PROVIDER` after health validation.

## FinancialReports API Contract

Required endpoints:

```text
GET  /v1/filings/{stock_code}/{period}/snapshot
GET  /v1/filings/{stock_code}/{period}/context
GET  /v1/stocks/{stock_code}/periods
GET  /v1/stocks
POST /v1/filings/{stock_code}/{period}/refresh
GET  /v1/jobs/{job_id}
GET  /v1/capabilities
GET  /v1/schema
POST /v1/batch/filings/query
```

The snapshot response contains `schema_version`, `identity`, `status`,
`pipeline_status`, `freshness`, `quality`, `snapshot`, `metrics`,
`metric_records`, `events`, `evidence`, canonical `facts`,
`field_availability`, `validation`, `comparisons`, `insight_cards`,
`source_documents`, and `pipeline_state`.
Periods use `YYYYQn`; monetary values use `TWD_thousands`; ratios use decimal
form unless the field name explicitly indicates percent.

## Compatibility and Fallback Rules

- JSON remains the default provider until the reviewed FinancialReports API is deployed.
- Remote fallback is allowed only for transport errors and server failures.
- A remote `404` or `422` must not silently fall back to unrelated local data.
- Existing `FinancialSnapshot` fields and existing financial endpoints remain
  backward compatible during Phases 1-3.
- Low-quality or stale data may be analyzed only when the response clearly
  carries the limitation and lowers confidence.

## Acceptance Criteria

- Existing tests continue to pass.
- Provider tests never require a live external service.
- Canonical mapping includes `eps_basic -> eps` and quarter normalization.
- Missing or processing data does not become an unstructured HTTP 500.
- Every material research conclusion can reference structured facts or document
  evidence.
- JSON fallback can be disabled completely through configuration.
- Unit tests do not attempt to export Langfuse traces.
