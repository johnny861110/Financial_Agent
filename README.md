# Financial Report Agent

**Version:** 2.0  
**Audience:** Professional fund managers, investment analysts, and research teams  
**Stack:** Python, FastAPI, React + TypeScript, LangGraph/LangChain, OpenAI-compatible LLMs, Langfuse, HTTP/JSON financial data providers

## Overview

Financial Report Agent is an evidence-backed research application for structured company financial reports. It combines deterministic Python services with a LangGraph workflow for readiness checks, research planning, tool execution, contradiction review, and answer composition.

The current default UI examples use **世芯-KY (`3661`) / `2025Q1`**.

The project exposes:

- A **React + TypeScript workbench** for dashboards and agent research.
- A **FastAPI backend** for programmatic financial analysis.
- A **LangGraph research agent** with `quick`, `auto`, and `research` modes.
- A provider layer supporting local JSON and the FinancialReports HTTP API v1.
- Structured evidence, assumptions, confidence, risks, contradictions, and data gaps.

Detailed documentation:

| Document | Purpose |
| --- | --- |
| [WORKBENCH.md](WORKBENCH.md) | React + TypeScript workbench setup, API boundary and local deployment |
| [REACT_MIGRATION_PLAN.md](REACT_MIGRATION_PLAN.md) | Migration scope, acceptance checklist and production gate |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System, data-layer, and Agent architecture diagrams and boundaries |
| [QUICKSTART.md](QUICKSTART.md) | Local setup, first research query, and common failures |
| [DOCKER.md](DOCKER.md) | Compose deployment and provider networking |
| [STRUCTURE.md](STRUCTURE.md) | Repository map, layering rules, and development workflow |
| [SPEC.md](SPEC.md) | Implemented technical requirements and explicit roadmap |
| [SAMPLE_DATA.md](SAMPLE_DATA.md) | JSON conventions, evidence, and missing-data behavior |
| [MODIFICATION_PLAN.md](MODIFICATION_PLAN.md) | Completed FinancialReports integration plan |
| [PROJECT_REPORT.md](PROJECT_REPORT.md) | Current capability, constraints, and priorities |
| [NEXT_SESSION_PLAN.md](NEXT_SESSION_PLAN.md) | Cross-repository handoff state and next implementation phases |

## What It Can Do

### Core Analytics

- Financial snapshot for a single period.
- Multi-period trend analysis.
- Peer comparison across selected metrics.

### Fund Manager Analytics

- Management quality score.
- Earnings quality score.
- ROIC vs WACC value creation analysis.
- Factor exposure analysis.
- Capital allocation analysis.
- Early warning signal detection.

### Agent Capabilities

- Routes narrow natural-language questions to the relevant analytical tool.
- Plans and executes a fixed multi-tool review for broad research questions.
- Checks source readiness and required fields before calculation.
- Preserves evidence and assumptions across tool and report boundaries.
- Detects selected contradictions between successful tool findings.
- Uses an LLM when `OPENAI_API_KEY` is configured.
- Uses deterministic routing and report composition when no API key is available.
- Reports unsupported tools and missing data explicitly.

### Placeholder / Roadmap Features

The following concepts exist in docs or tool stubs but are not complete production features yet:

- Sentiment analysis.
- Guidance tracking.
- Earnings call transcript intelligence.
- Redis and market-data ingestion. (PostgreSQL and pgvector are no longer
  roadmap items: FinancialReports runs on them today.)
- Investment memo PDF export.
- Multi-agent bull/bear/PM debate workflow.

## Architecture

The implemented system has three documented views:

1. **System layer:** the workbench and API clients enter through FastAPI; financial
   routes call deterministic services while Agent routes call LangGraph.
2. **Data layer:** services use the `DataLoader` facade over either local JSON
   or FinancialReports, with typed retry, cache, fallback, quality, freshness,
   and evidence behavior. `CanonicalFinancialContext` preserves facts, units,
   absence states, validation, metrics, and evidence for migrated services.
3. **Agent layer:** intent routing flows through data readiness, research
   planning, typed tool execution, evidence/contradiction review, and report
   composition.

See [ARCHITECTURE.md](ARCHITECTURE.md) for all three Mermaid diagrams,
responsibility tables, failure boundaries, and execution modes. See
[STRUCTURE.md](STRUCTURE.md) for the current source tree.

## Data

Financial data is loaded from:

```text
data/financial_reports/
```

Files should follow this convention:

```text
<stock_code>_<period>_enhanced.json
```

Example:

```text
3661_2025Q1_enhanced.json
```

Example JSON:

```json
{
  "stock_code": "3661",
  "company_name": "世芯-KY",
  "report_year": 2025,
  "report_season": 1,
  "report_period": "2025Q1",
  "currency": "TWD",
  "unit": "thousand",
  "cash_and_equivalents": 38262852.0,
  "accounts_receivable": 2794776.0,
  "inventory": 5754313.0,
  "total_assets": 52621348.0,
  "total_liabilities": 15818473.0,
  "equity": 41588114.0,
  "net_revenue": 318737.0,
  "gross_profit": 73833.0,
  "operating_income": 45431.0,
  "net_income": 44424.0,
  "eps": 0.55
}
```

## Data Quality Behavior

Several analytics require specific fields. For example:

- ROIC/WACC requires `operating_income`, `equity`, and `total_liabilities`.
- Earnings quality requires income, balance sheet, and working capital fields.
- Factor analysis requires complete target and peer financial records.
- EWS requires revenue, receivables, inventory, assets, liabilities, and cash fields.

If a calculation cannot run because required fields are `null` or missing, the API returns:

```json
{
  "detail": {
    "error": "insufficient_data",
    "message": "Insufficient data for ROIC/WACC analysis: missing operating_income",
    "missing_fields": ["operating_income"]
  }
}
```

The HTTP status for this case is `422`.

## Installation

### Requirements

- Python 3.10+
- `uv`

Install dependencies:

```bash
uv sync
```

Alternative:

```bash
pip install -e .
```

## Configuration

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Core variables:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.0

# Langfuse Observability
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=pk-lf-your_public_key
LANGFUSE_SECRET_KEY=sk-lf-your_secret_key
LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_REQUIRED=false

# Data Configuration
DATA_DIR=./data
FINANCIAL_DATA_PATH=./data/financial_reports
DATA_PROVIDER=financial_reports
FINANCIAL_REPORTS_BASE_URL=http://financial-reports:8010
FINANCIAL_REPORTS_TIMEOUT=10
FINANCIAL_REPORTS_MAX_RETRIES=2
DATA_CACHE_TTL_SECONDS=300
ALLOW_JSON_FALLBACK=false
MIN_DATA_QUALITY_SCORE=0.6
AUTO_REFRESH_MISSING_DATA=false

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_BASE_URL=http://localhost:8000
API_RELOAD=true
# Only the Vite dev server needs an origin: the containerised workbench is
# same-origin behind nginx.
API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Logging
LOG_LEVEL=INFO
```

Langfuse is optional. If `LANGFUSE_ENABLED=true`, provide a valid public key, secret key, and base URL. If `LANGFUSE_REQUIRED=true`, startup fails when Langfuse is misconfigured.

## Running Locally

Start FastAPI first:

```bash
uv run uvicorn app.main:app --reload
```

Then start the workbench in another terminal:

```bash
cd frontend && npm install && npm run dev
```

Open:

- Workbench (Vite dev server): `http://localhost:5173`
- FastAPI: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker

### Prerequisites

Create `.env` before starting (see [Configuration](#configuration)):

```bash
cp .env.example .env
```

Create the logs directory (bind-mounted into the API container):

```bash
mkdir -p logs
```

No Docker network has to be created first. Langfuse and FinancialReports run in
their own Compose projects and are reached over their published host ports.

### Build and Start

The image is built once and shared by both services:

```bash
docker compose up -d --build
```

Services:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Workbench: `http://localhost:8080`

The UI service waits for the API healthcheck to pass before starting.

### Common Commands

Check status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f api
docker compose logs -f ui
```

Stop services:

```bash
docker compose down
```

Rebuild after dependency changes (`pyproject.toml` / `uv.lock`):

```bash
docker compose up -d --build
```

### Image Structure

The Dockerfile uses a two-stage build:

| Stage | Purpose |
| --- | --- |
| `builder` | Installs `uv`, compiles dependencies into `/app/.venv` |
| Runtime (`python:3.10-slim`) | Copies only the venv and application code, runs as non-root `appuser` |

`curl` is installed in the runtime image to support the built-in healthchecks for both services.

See [DOCKER.md](DOCKER.md) for remote-provider networking, operations, and
production gaps.

## API Endpoints

### Discovery

Ask the configured provider what it can serve, rather than guessing:

```bash
curl http://localhost:8000/api/data/capabilities
curl http://localhost:8000/api/data/stocks
curl http://localhost:8000/api/data/3661/periods
```

`capabilities` also identifies which provider is answering: `api_version: "v1"`
is the FinancialReports API, `schema_version: "legacy-json"` is local files.

### Period format

Every endpoint taking a period requires the canonical `YYYYQn` form. Anything
else is rejected with `422 invalid_period` rather than being reported as
missing data:

```bash
curl -i http://localhost:8000/api/financials/3661/2026
# 422 {"detail":{"error":"invalid_period","message":"period must use YYYYQn, ..."}}
```

Unconventional but unambiguous spellings are normalized, so `2026Q1`, `26Q1`
and `2026年第一季` all resolve to `2026Q1`.

### Failure semantics

A data failure names its own cause instead of being reported as missing data:

| Status | Meaning |
|---|---|
| 404 | The filing does not exist for that stock and period |
| 422 | The period is not `YYYYQn`, or required fields are absent |
| 502 | The upstream provider answered with something unusable |
| 503 | The upstream provider is unreachable |

With `ALLOW_JSON_FALLBACK=false` a producer outage surfaces as 503 rather than
being answered quietly from local files that may be older than the request.

### Snapshot

```bash
curl http://localhost:8000/api/financials/3661/2025Q1
```

### Trend

```bash
curl http://localhost:8000/api/trend/3661
```

### Peer Comparison

```bash
curl -X POST http://localhost:8000/api/peers/compare \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["3661", "2330", "2454"],
    "period": "2025Q1",
    "metrics": ["Gross Margin", "Operating Margin", "ROE", "Debt Ratio"]
  }'
```

### Management Score

```bash
curl -X POST http://localhost:8000/api/scores/management \
  -H "Content-Type: application/json" \
  -d '{
    "ceo_tenure_years": 5,
    "cfo_tenure_years": 4,
    "board_independence_ratio": 0.4,
    "insider_buys": 3,
    "insider_sells": 1,
    "governance_incidents": 0
  }'
```

### Earnings Quality

```bash
curl http://localhost:8000/api/scores/earnings_quality/3661/2025Q1
```

### ROIC vs WACC

```bash
curl -X POST http://localhost:8000/api/roic_wacc/3661/2025Q1 \
  -H "Content-Type: application/json" \
  -d '{
    "beta": 1.2,
    "tax_rate": 0.2
  }'
```

### Factor Exposure

```bash
curl -X POST http://localhost:8000/api/factors/3661/2025Q1 \
  -H "Content-Type: application/json" \
  -d '{
    "peer_stocks": ["2330", "2454"]
  }'
```

### Capital Allocation

```bash
curl -X POST http://localhost:8000/api/capital_allocation/3661/2025Q1 \
  -H "Content-Type: application/json" \
  -d '{
    "dividends": 0,
    "buybacks": 0,
    "capex": 0,
    "rd_expense": 0,
    "ma_spending": 0
  }'
```

### Early Warning System

```bash
curl http://localhost:8000/api/ews/3661/2025Q1
```

### Agent Query

```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the financial snapshot for 世芯-KY 3661 in 2025Q1?",
    "stock_code": "3661",
    "period": "2025Q1",
    "context": {
      "company_name": "世芯-KY"
    }
  }'
```

### Evidence-Backed Research

Use the research endpoint for a multi-step review. It checks data readiness,
builds a deterministic tool plan, runs the required analyses, detects
contradictions, and returns evidence and a numeric confidence score.

```bash
curl -X POST http://localhost:8000/api/agent/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "請完整分析 3661 是否值得持有",
    "stock_code": "3661",
    "period": "2025Q1",
    "mode": "research"
  }'
```

The original `/api/agent/query` endpoint remains available and accepts
`mode: auto`, `quick`, or `research`.

**Numbers come from the structured tables; retrieval is for narrative only.**
The producer publishes 34 canonical fields and all of them are surfaced through
`/api/financials/{stock}/{period}`, each with a unit and an availability state.
Filing text is retrieved for what a statement *says* — accounting judgement,
impairment criteria, valuation method, subsidiaries, contingencies. Of the note
titles in the corpus only about 1% name a canonical field, so the two barely
overlap. This matters because a statement restates the same line item for prior
periods, for segments and for subsidiaries: a figure read out of a retrieved
passage is easily real and attached to the wrong period, so the answer prompt
treats the structured report as authoritative for values and passages as
evidence for claims.

Two fields on the producer's context response are consumed and worth knowing:

| Field | Why it matters |
|---|---|
| `retrieval.state` | Whether the question actually influenced the ranking. `present` is a real semantic match; `provider_failure` or `missing` means the chunks came back in importance order and the question was ignored. A degraded state becomes a visible data gap rather than citations that read as though they answered you. |
| `corpus_version` | Identifies the filing's chunk corpus. A re-extract renumbers every chunk into an overlapping id range, so a stored citation resolves to *different* text rather than failing. Compare it before treating a cached citation as still valid. |

### FinancialReports Data Provider

The v1 API is the shipped default. The settings it uses:

```bash
DATA_PROVIDER=financial_reports
FINANCIAL_REPORTS_BASE_URL=http://financial-reports:8010
ALLOW_JSON_FALLBACK=false
DATA_CACHE_TTL_SECONDS=300
MIN_DATA_QUALITY_SCORE=0.6
```

Remote `404` and `422` responses are never replaced with local data: a filing
that does not exist, and a request the producer rejects, are answers rather
than faults.

Transport and server failures are governed by `ALLOW_JSON_FALLBACK`, which now
ships as `false` — an unreachable producer surfaces as `503` instead of being
answered from local files that may be older than the request. Setting it to
`true` restores the fall back, at the cost of making an outage look like a
successful answer. Either way, a previously cached remote record is returned
as stale when one is available.

`DataLoader.load_context()` exposes the complete service-facing filing context.
Snapshot and trend analysis already use it, so missing and `not_applicable`
inputs do not become zero and producer ratio metrics retain their unit meaning.
Other deterministic services remain on the compatibility snapshot while their
field and validation requirements are migrated incrementally.

```bash
curl http://localhost:8000/api/data/3661/2025Q1/status
curl http://localhost:8000/api/data/3661/2025Q1/record
curl http://localhost:8000/api/data/capabilities
curl -X POST http://localhost:8000/api/data/3661/2025Q1/refresh
curl http://localhost:8000/api/data/jobs/JOB_ID
```

## Workbench Defaults

The UI defaults are set to the current sample company:

- Company: `世芯-KY`
- Stock code: `3661`
- Peer example: `3661,2330,2454`

The period is no longer fixed in the page. Each page lists the periods the
configured provider can actually serve, newest first, from
`GET /api/data/{stock_code}/periods`.

## Testing and Quality Checks

Run tests:

```bash
uv run pytest
```

Five of these are a cross-repository smoke test against a running
FinancialReports process -- the only coverage of the consumer/producer
boundary, since every other test mocks the producer. **An unreachable producer
is an error, not a skip**, so a green suite means that seam was actually
exercised:

```bash
docker start financialreports-db-1 financialreports-api-1   # producer on 8010
FA_ALLOW_SMOKE_SKIP=1 uv run pytest                         # or opt out
```

Note that `.env` sets `FINANCIAL_REPORTS_BASE_URL` to the compose hostname
`http://financial-reports:8010`, which resolves only inside the compose
network; on the host the tests fall back to `http://127.0.0.1:8010`.

Smoke-test the built image rather than the source tree:

```bash
./scripts/container_smoke.sh
```

Every pytest run imports from the working copy, so a dependency missing from
the *image* is invisible to all of them, and nothing in the suite reads compose
at all -- which is how a compose default of `LLM_TEMPERATURE=1.0` survived a
green suite. This asserts against a running container: the environment it
actually received, the imports it can actually resolve, and one numeric and one
narrative query answered end to end. The numeric check reads the expected
figure from the API rather than hardcoding it, so it does not rot when the
corpus is re-ingested.

Run type checks:

```bash
uv run mypy app/data app/agents app/api app/services app/models/agent_models.py ui/api_client.py
```

Compile-check Python files:

```bash
uv run python -m compileall -q app ui
```

Format code:

```bash
uv run black --check app tests
```

Measure filing-text retrieval. Unlike the checks above this needs a running
producer, which is why it is a script rather than part of `python -m
evaluation` — that stays fixture-only and deterministic:

```bash
FINANCIAL_REPORTS_BASE_URL=http://127.0.0.1:8010 \
  uv run python scripts/retrieval_benchmark.py --limit 20
```

Current reading against the live corpus (40 narrative probes): hit@10 88%,
mean rank 1.4 when hit, 100% reaching the model.

It derives its probes from the corpus and excludes any note title that names a
canonical field, because scoring retrieval on 應收帳款 or 營業收入 measures a
path that should never be taken — those come from the structured fields. It
also reports how many probes survived the workflow rather than only how many
the producer returned, since a passage that is retrieved and then dropped
before the prompt is not a passage anyone received.

## Implementation Status

| Area | Status | Notes |
| --- | --- | --- |
| JSON financial data loading | Implemented | Local `*_enhanced.json` files. |
| Canonical financial context | Phase 1 implemented | Indexed facts, units, field states, validation, metrics, freshness, and evidence with legacy JSON compatibility. |
| Snapshot analysis | Context-aware | Uses canonical facts/metrics and exposes field states plus failed validation. |
| Trend analysis | Context-aware | Uses available canonical observations without manufacturing zero for missing derived metrics. |
| Peer comparison | Implemented | Requires at least two loaded companies. |
| Management score | Implemented | Input-driven governance scoring. |
| Earnings quality | Implemented with source-data constraints | Returns `422` when required fields are missing. |
| ROIC/WACC | Implemented with proxy assumptions | Uses CAPM-style defaults and book-value capital weights. |
| Factor exposure | Implemented with proxy assumptions | Needs enough complete peer records for z-scores. |
| Early warning system | Implemented | Rule-based red flag detection. |
| Capital allocation | Partial | Debt change is still a placeholder. |
| FinancialReports producer API | Merged and locally validated | Versioned schema, discovery, filing/context, refresh/jobs, batch query, and committed OpenAPI; target deployment remains environment-specific. |
| FinancialReports provider | Implemented | Full v1 identity/fact/provenance schema, pagination, processing state, retry, cache, stale mode, and JSON fallback. |
| LangGraph agent | Implemented | Data readiness, deterministic planning, multi-tool research, contradiction checks, and LLM fallback. |
| Langfuse tracing | Optional | Controlled by env vars. |
| Sentiment / guidance tools | Not supported | Explicitly return `not_supported`; no fabricated neutral result. |
| Filing-text retrieval | Implemented | Narrative only; numbers come from the canonical fields. Reports `retrieval.state` so a fallback ranking is visible, and `corpus_version` so stale citations are detectable. |
| PostgreSQL / pgvector | Implemented, in the producer | FinancialReports runs `pgvector/pgvector:pg16`; chunk embeddings are a `VECTOR(768)` column queried by cosine distance. Exact search beats ANN at this corpus size, so no index is maintained — see that project's `schema.sql` for the restore statement if that changes. |
| Redis | Roadmap | Not part of current runtime. |
| PDF investment memo | Roadmap | Not implemented. |

## Formula Notes

### Management Quality

```text
M = 0.25T + 0.25B + 0.25I + 0.25G
```

Where:

- `T`: tenure stability.
- `B`: board independence.
- `I`: insider alignment.
- `G`: governance score, inverted from red flags.

### Earnings Quality

```text
E = 0.25AQ + 0.25WCB + 0.25OD + 0.25ES
```

Where:

- `AQ`: accrual quality.
- `WCB`: working capital behavior.
- `OD`: one-off dependency.
- `ES`: earnings stability.

## Security Notes

- Do not commit `.env`, private keys, proprietary raw data, or `.pem` files.
- Keep `API_CORS_ORIGINS` restricted in production.
- The API currently has no authentication. Add API keys, OAuth, or another auth layer before exposing it outside a trusted network.
- Treat LLM outputs as generated commentary; calculations should come from service output.

## Development Notes

- Prefer adding new financial logic under `app/services/`.
- Add source contracts/providers under `app/data/`; keep `DataLoader` compatible.
- Add or update Pydantic models in `app/models/` or `app/data/models.py`.
- Expose service functionality through `app/api/financials.py`.
- Make Agent wrappers return `ToolResult` from `app/agents/tools.py`.
- Update planning, evidence, and report behavior in `app/agents/workflow.py`.
- Keep the workbench behind `frontend/src/api.ts` rather than reaching past the API.
- Add provider failure, service, tool-contract, workflow, and API tests as relevant.

## License

MIT License
