# Project Structure

This file maps repository paths to their current runtime responsibilities. See
`ARCHITECTURE.md` for the three architecture diagrams and component flows.

```text
Financial_Agent/
|-- app/
|   |-- main.py                 FastAPI application and health endpoints
|   |-- api/
|   |   |-- financials.py       Deterministic financial-analysis endpoints
|   |   |-- agent.py            Query and evidence-backed research endpoints
|   |   `-- data.py             Readiness, refresh, and ingestion-job endpoints
|   |-- agents/
|   |   |-- contracts.py        ToolResult and ResearchReport contracts
|   |   |-- retrieval.py        Filing-text passages, retrieval state, corpus version
|   |   |-- tools.py            LangChain tools over deterministic services
|   |   `-- workflow.py         LangGraph planning and report workflow
|   |-- core/
|   |   |-- config.py           Environment-backed application settings
|   |   |-- data_loader.py      Backward-compatible provider facade
|   |   `-- utils.py            Validation and financial math helpers
|   |-- data/
|   |   |-- context.py          Canonical facts, units, absence, validation accessors
|   |   |-- models.py           Quality, freshness, evidence, snapshot record
|   |   |-- providers.py        JSON, HTTP, fallback, retry, and stale cache
|   |   |-- readiness.py        Data-state classification and refresh access
|   |   `-- factory.py          Configured provider lifecycle
|   |-- models/                 Pydantic financial and API models
|   `-- services/
|       |-- factory.py          Shared service registry and dependency injection
|       `-- *_service.py        Deterministic analysis implementations
|-- ui/
|   `-- pages/                  Analyst dashboards and Agent research UI
|-- frontend/
|   |-- src/api.generated.ts    Types generated from the committed OpenAPI schema
|   |-- src/api.ts              Typed fetch client over the FastAPI boundary
|   |-- src/App.tsx             React research workbench
|   `-- package.json            Vite, TypeScript, and Vitest configuration
|-- scripts/
|   |-- export_openapi.py       Regenerate the committed OpenAPI schema
|   `-- retrieval_benchmark.py  Score narrative retrieval against the live corpus
|-- evaluation/                 Scenario-based agent evaluation harness
|-- deploy/workbench.nginx.conf Static-asset and API proxy config for the workbench
|-- data/financial_reports/     Local enhanced JSON data (runtime, ignored)
|-- tests/
|   |-- fixtures/               Versioned provider contract fixtures
|   `-- test_*.py               Unit, API, provider, workflow, and precedence tests
|-- convert_financial_report.py Legacy JSON conversion utility
|-- ARCHITECTURE.md             Implemented architecture and boundaries
|-- MODIFICATION_PLAN.md        Completed integration plan and acceptance checks
|-- SPEC.md                     Current specification and future roadmap
|-- WORKBENCH.md                React workbench setup and API boundary
|-- Dockerfile                  API image
|-- Dockerfile.frontend         Workbench build and nginx runtime
|-- docker-compose.yaml         Default stack
|-- docker-compose.dev.yaml     Local development overrides
`-- docker-compose.react.yaml   Stack including the React workbench
```

## Layering Rules

1. UI pages call FastAPI through `ui/api_client.py`; they do not instantiate
   analysis services.
2. API routes obtain services from `app/services/factory.py` and move blocking
   work to FastAPI's thread pool.
3. Services depend on the `DataLoader` facade, not a concrete source.
4. Data providers normalize source responses into `SnapshotRecord`.
5. Agent tools wrap services and return `ToolResult`; the graph consumes that
   contract and returns `ResearchReport`/`AgentResponse`.
6. FinancialReports owns ingestion and source evidence. This repository owns
   analytics and research orchestration.
7. Financial values come from the canonical fields on `SnapshotRecord`; filing
   passages are narrative evidence only. Never read a number out of retrieved
   text -- see `ARCHITECTURE.md` §Structured Facts and Filing Text.

## Public API Groups

| Group | Routes |
| --- | --- |
| Health | `GET /health`, `GET /health/live`, `GET /health/ready` |
| Financial facts | `GET /api/financials/{stock}/{period}`, `GET /api/trend/{stock}` |
| Analytics | Peer, management, earnings quality, ROIC/WACC, factors, capital allocation, EWS under `/api` |
| Agent | `POST /api/agent/query`, `POST /api/agent/research` |
| Data operations | Status, refresh, and jobs under `/api/data` |

Swagger at `/docs` is the authoritative request/response schema for individual
financial endpoints.

## Change Workflow

1. Update provider/domain contracts before implementations and callers.
2. Add deterministic service behavior before exposing an Agent tool.
3. Add or update API and UI callers after service contracts are stable.
4. Cover provider failures, missing fields, evidence, and Agent behavior in
   tests.
5. Run Black, compileall, mypy, pytest, and GitNexus impact checks.
6. Update `ARCHITECTURE.md`, API examples, and implementation status when a
   public boundary changes.
