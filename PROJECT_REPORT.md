# Financial Agent Project Report

**Version:** 2.0

**Status date:** 2026-08-28

**Purpose:** Evidence-backed financial statement research and deterministic
financial analysis.

## Executive Summary

Financial Agent is no longer only a natural-language router over isolated
tools. It now implements a research workflow that verifies source readiness,
selects an auditable analysis plan, runs deterministic services, preserves
field-level evidence, checks cross-tool contradictions, and produces a
structured report with confidence and data gaps.

The project is still a decision-support service. It does not autonomously
trade, ingest raw filings, or provide a complete multi-agent investment
committee. Source ingestion belongs to the separate FinancialReports service.

## Implemented System

| Area | Current capability |
| --- | --- |
| Delivery | FastAPI API and React + TypeScript analyst workbench |
| Data | Local JSON provider and FinancialReports HTTP provider |
| Canonical context | Fact/unit/availability/validation accessors; Snapshot and Trend migrated |
| Resilience | Retry, controlled fallback, process-local TTL cache, stale mode |
| Readiness | Ready, processing, missing, low-quality, stale, and failed states |
| Analytics | Snapshot, trend, peers, management, earnings quality, ROIC/WACC, factors, capital allocation, EWS |
| Agent | Quick/auto/research modes with deterministic planning |
| Explainability | Evidence, warnings, assumptions, confidence, risks, contradictions, gaps |
| Optional AI | LLM classification/composition and Langfuse tracing |

The three implemented architecture views are maintained in
`ARCHITECTURE.md`: system, data layer, and Agent layer.

## Important Design Decisions

1. Financial calculations stay in Python services. The LLM may classify and
   phrase results but is not trusted to calculate source facts.
2. Every Agent tool returns the same typed result envelope.
3. A missing remote filing or invalid contract cannot silently fall back to a
   different local record.
4. Low-quality, stale, and assumption-based findings remain visible and reduce
   confidence.
5. The workbench uses the public API boundary, keeping UI and backend behavior
   consistent.
6. The FinancialReports integration is HTTP-based and versioned; no database
   file is shared between projects.

## Research Flow

For a broad `research` request, the planner runs snapshot, trend, earnings
quality, ROIC/WACC, and EWS. Peer and factor analysis are added when a peer
universe is supplied. The report composer then returns:

- verdict and thesis;
- tool findings with numeric confidence;
- source evidence and caller assumptions;
- material risks and contradiction notices;
- missing-data gaps and watch items.

For narrow questions, `quick` mode runs only the matching tool. `auto` chooses
between narrow and broad behavior from the request.

## Current Constraints

- FinancialReports v1 and its consumer are merged and contract-tested. A named
  production deployment target has not been configured.
- Canonical context migration is incremental: Snapshot and Trend actively use
  rich schema; the remaining deterministic services still use the legacy
  snapshot facade.
- The cache and Agent state are process-local and not durable.
- No authentication, authorization, rate limiting, or tenant isolation exists.
- ROIC/WACC and management analyses may rely on explicit defaults/caller input.
- Sentiment and management guidance tools return `not_supported`.
- There is no transcript ingestion, PDF memo export, market-data feed, Redis,
  or bull/bear/PM multi-agent debate.
- Semantic retrieval over filing text *is* available, but only for narrative
  questions: every financial value comes from the 34 canonical fields. The
  PostgreSQL and pgvector that back it belong to FinancialReports; this service
  reaches them only across the HTTP boundary.
- Outputs require analyst review and are not investment advice.

## Verification Status

The current consumer passes Black, Python compilation, mypy, and 194 pytest
tests. Coverage includes absence states, unit mismatch, validation filtering,
producer metrics, missing-safe trend behavior, provider resilience, Agent
workflow, services, and API behavior.

## Next Engineering Priorities

1. ~~Introduce canonical financial context and schema-aware tool gates.~~ Done.
2. ~~Add question-directed filing text retrieval and citations.~~ Done, and
   corrected 2026-09-06: numbers come from the 34 canonical fields, retrieval
   is for narrative only. See NEXT_SESSION_PLAN.md §3.2.
3. Add authentication, request limits, durable job state, and shared cache.
4. Replace proxy/default inputs with audited cash-flow and market data.
5. Add evaluation datasets for verdict stability, citation completeness, and
   contradiction recall before adding more Agent roles.
