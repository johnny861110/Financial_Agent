# Quick Start

## Requirements

- Python 3.10+
- `uv`
- Local JSON reports for the default provider, or a compatible
  FinancialReports API v1 deployment

The LLM is optional. Without `OPENAI_API_KEY`, the Agent uses deterministic
routing and composition.

## Install

```bash
uv sync
cp .env.example .env
```

The repository includes sample files under `data/financial_reports`. Local
files use `<stock_code>_<YYYYQn>_enhanced.json`.

## Run Locally

Start the API first:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal, start the UI:

```bash
cd frontend && npm install && npm run dev
```

Open:

- Workbench: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Readiness: `http://127.0.0.1:8000/health/ready`

## Run a Research Query

```bash
curl -X POST http://127.0.0.1:8000/api/agent/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分析 3661 2025Q1 的財務品質、趨勢、資本報酬與風險",
    "stock_code": "3661",
    "period": "2025Q1",
    "mode": "research"
  }'
```

The response includes the research plan, findings, evidence, risks,
contradictions, data gaps, watch items, verdict, and confidence score.

The deterministic snapshot endpoint also returns `data_context` with schema
version, readiness status, quality, freshness, field states, and failed
validation records:

```bash
curl http://127.0.0.1:8000/api/financials/3661/2025Q1
```

## Choose a Data Provider

Local JSON, for working without the producer running:

```env
DATA_PROVIDER=json
FINANCIAL_DATA_PATH=./data/financial_reports
```

Use FinancialReports through HTTP:

```env
DATA_PROVIDER=financial_reports
FINANCIAL_REPORTS_BASE_URL=http://127.0.0.1:8010
# Leave this false while verifying the connection: true lets an outage answer
# silently from local files that may be older than what was asked for.
ALLOW_JSON_FALLBACK=false
DATA_CACHE_TTL_SECONDS=300
MIN_DATA_QUALITY_SCORE=0.6
```

Check a filing before analysis:

```bash
curl http://127.0.0.1:8000/api/data/3661/2025Q1/status
```

Refresh is only supported by the remote provider:

```bash
curl -X POST http://127.0.0.1:8000/api/data/3661/2025Q1/refresh
curl http://127.0.0.1:8000/api/data/jobs/JOB_ID
```

## Tests and Quality

```bash
uv run black --check app tests
uv run python -m compileall -q app tests ui
uv run mypy app/data app/agents app/api app/services app/models/agent_models.py ui/api_client.py
uv run pytest
git -c core.whitespace=cr-at-eol diff --check
```

## Common Failures

| Symptom | Check |
| --- | --- |
| UI reports API unavailable | Start FastAPI and verify `API_BASE_URL` |
| Filing returns missing | Check filename/provider and `YYYYQn` period format |
| Refresh returns 503 | JSON provider cannot ingest; use FinancialReports |
| Readiness returns 503 | Configured remote provider is unreachable |
| Agent has lower confidence | Inspect warnings, missing fields, assumptions, and stale/quality state |
| Sentiment/guidance says unsupported | Those tools are intentionally not implemented |

See `ARCHITECTURE.md` for system behavior and `DOCKER.md` for containers.
