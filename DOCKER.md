# Docker Deployment

The Compose stack builds one application image and runs it as two services:
FastAPI (`api`) and Streamlit (`ui`). The UI waits for the API healthcheck and
calls it through `API_BASE_URL=http://api:8000`.

## Requirements

- Docker Engine 20.10+
- Docker Compose v2 (`docker compose`)
- A `.env` file
- Local `data` and `logs` directories
- The external `langfuse_default` Docker network used by the current Compose
  configuration

Create prerequisites:

```bash
cp .env.example .env
mkdir -p logs
docker network inspect langfuse_default >/dev/null 2>&1 || \
  docker network create langfuse_default
```

`OPENAI_API_KEY` and Langfuse credentials are optional. Leave
`LANGFUSE_ENABLED=false` when tracing is not configured.

## Start and Verify

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api ui
```

Endpoints:

- Streamlit: `http://localhost:8501`
- FastAPI: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/health/live`
- Provider readiness: `http://localhost:8000/health/ready`

The API mounts `./data` read-only and `./logs` read-write. The UI mounts data
for compatibility, but normal UI requests go through FastAPI.

## Data Provider Configuration

Default local mode:

```env
DATA_PROVIDER=json
FINANCIAL_DATA_PATH=/app/data/financial_reports
```

Remote mode:

```env
DATA_PROVIDER=financial_reports
FINANCIAL_REPORTS_BASE_URL=http://financial-reports:8010
FINANCIAL_REPORTS_TIMEOUT=10
FINANCIAL_REPORTS_MAX_RETRIES=2
DATA_CACHE_TTL_SECONDS=300
ALLOW_JSON_FALLBACK=true
MIN_DATA_QUALITY_SCORE=0.6
AUTO_REFRESH_MISSING_DATA=false
```

`financial-reports` must resolve from both application containers. Add that
service to a shared Docker network or replace the URL with a reachable host.
The current Compose file does not start FinancialReports itself.

## Image Layout

The Dockerfile uses two stages:

| Stage | Purpose |
| --- | --- |
| `builder` | Install `uv` and create `/app/.venv` from the lockfile |
| Runtime | Copy the virtual environment and application, then run as `appuser` |

The same image runs `uvicorn` for the API and `streamlit` for the UI. Runtime
`curl` supports container healthchecks.

## Operations

```bash
# Stop without deleting data
docker compose down

# Restart
docker compose restart

# Rebuild after dependency or source changes
docker compose up -d --build

# Run tests in the API image
docker compose run --rm api pytest

# Inspect effective configuration
docker compose config
```

Do not use `docker compose down --volumes` unless removal of attached volumes
is intentional.

## Troubleshooting

### Compose reports `langfuse_default` missing

Create the external network as shown in Requirements. This network is needed
by the current Compose topology even when tracing is disabled.

### API is healthy but not ready

```bash
curl -i http://localhost:8000/health/ready
docker compose logs api
```

For `DATA_PROVIDER=financial_reports`, verify DNS, port 8010, and the v1
contract. For local mode, verify files under `data/financial_reports`.

### UI cannot reach API

Confirm the UI environment contains `API_BASE_URL=http://api:8000` and that
the API container is healthy:

```bash
docker compose exec ui env | grep API_BASE_URL
docker compose ps api
```

### Refresh returns HTTP 503

The JSON provider is read-only and cannot enqueue ingestion. Configure the
FinancialReports provider for refresh/job operations.

### Port collision

Change only the host side of a port mapping, for example `8080:8000`; internal
service URLs continue to use port 8000.

## Production Gaps

The provided Compose file is a development deployment. Before production, add
TLS/reverse proxy, authentication, secret management, resource limits,
centralized logs, metrics, shared cache, durable jobs, backup policy, and a
non-root compatible writable log strategy.
