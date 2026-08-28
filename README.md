# Financial Report Agent

**Version:** 2.0  
**Audience:** Professional fund managers, investment analysts, and research teams  
**Stack:** Python, FastAPI, Streamlit, LangGraph/LangChain, OpenAI-compatible LLMs, Langfuse, HTTP/JSON financial data providers

## Overview

Financial Report Agent is an evidence-backed research application for structured company financial reports. It combines deterministic Python services with a LangGraph workflow for readiness checks, research planning, tool execution, contradiction review, and answer composition.

The current default UI examples use **世芯-KY (`3661`) / `2025Q1`**.

The project exposes:

- A **Streamlit UI** for dashboards and agent chat.
- A **FastAPI backend** for programmatic financial analysis.
- A **LangGraph research agent** with `quick`, `auto`, and `research` modes.
- A provider layer supporting local JSON and the FinancialReports HTTP API v1.
- Structured evidence, assumptions, confidence, risks, contradictions, and data gaps.

Detailed documentation:

| Document | Purpose |
| --- | --- |
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
- PostgreSQL, Redis, pgvector, and market-data ingestion.
- Investment memo PDF export.
- Multi-agent bull/bear/PM debate workflow.

## Architecture

The implemented system has three documented views:

1. **System layer:** Streamlit and API clients enter through FastAPI; financial
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
DATA_PROVIDER=json
FINANCIAL_REPORTS_BASE_URL=http://financial-reports:8010
FINANCIAL_REPORTS_TIMEOUT=10
FINANCIAL_REPORTS_MAX_RETRIES=2
DATA_CACHE_TTL_SECONDS=300
ALLOW_JSON_FALLBACK=true
MIN_DATA_QUALITY_SCORE=0.6
AUTO_REFRESH_MISSING_DATA=false

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_BASE_URL=http://localhost:8000
API_RELOAD=true
API_CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

# Logging
LOG_LEVEL=INFO
```

Langfuse is optional. If `LANGFUSE_ENABLED=true`, provide a valid public key, secret key, and base URL. If `LANGFUSE_REQUIRED=true`, startup fails when Langfuse is misconfigured.

## Running Locally

Start FastAPI first:

```bash
uv run uvicorn app.main:app --reload
```

Then start Streamlit in another terminal:

```bash
API_BASE_URL=http://localhost:8000 uv run streamlit run streamlit_app.py
```

Open:

- Streamlit: `http://localhost:8501`
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
docker network inspect langfuse_default >/dev/null 2>&1 || \
  docker network create langfuse_default
```

### Build and Start

The image is built once and shared by both services:

```bash
docker compose up -d --build
```

Services:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8501`

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

### FinancialReports Data Provider

JSON remains the default source. To consume the FinancialReports v1 API:

```bash
DATA_PROVIDER=financial_reports
FINANCIAL_REPORTS_BASE_URL=http://financial-reports:8010
ALLOW_JSON_FALLBACK=true
DATA_CACHE_TTL_SECONDS=300
MIN_DATA_QUALITY_SCORE=0.6
```

Remote `404` and `422` responses are not replaced with local data. Transport
and server failures may use local JSON fallback; a previously cached remote
record is returned as stale when available.

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

## Streamlit UI Defaults

The UI defaults are set to the current sample company:

- Company: `世芯-KY`
- Stock code: `3661`
- Period: `2025Q1`
- Peer example: `3661,2330,2454`

## Testing and Quality Checks

Run tests:

```bash
uv run pytest
```

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
uv run black --check app tests ui streamlit_app.py
```

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
| PostgreSQL / Redis / pgvector | Roadmap | Not part of current runtime. |
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
- Keep Streamlit behind `ui/api_client.py` rather than importing services.
- Add provider failure, service, tool-contract, workflow, and API tests as relevant.

## License

MIT License
