# Financial Agent Architecture

This document describes the implemented architecture of Financial Agent 2.0.
It is the source of truth for system boundaries, data access, and Agent
orchestration. Planned capabilities are listed separately in `SPEC.md`.

## System Architecture

```mermaid
flowchart LR
    User[Analyst / API client]
    UI[Streamlit UI]

    subgraph FA[Financial Agent]
        API[FastAPI]
        FinancialRoutes[Financial analysis routes]
        DataRoutes[Data status / refresh routes]
        AgentRoutes[Agent query / research routes]
        Services[Deterministic analysis services]
        Graph[LangGraph research workflow]
        Provider[FinancialDataProvider]
    end

    subgraph Sources[Data sources]
        FR[FinancialReports API v1]
        JSON[(Local enhanced JSON)]
    end

    LLM[OpenAI-compatible LLM]
    LF[Langfuse]

    User --> UI
    User --> API
    UI -->|HTTP| API
    API --> FinancialRoutes
    API --> DataRoutes
    API --> AgentRoutes
    FinancialRoutes --> Services
    AgentRoutes --> Graph
    Graph --> Services
    Services --> Provider
    DataRoutes --> Provider
    Provider -->|primary when configured| FR
    Provider -->|default or controlled fallback| JSON
    Graph -.->|optional classification / composition| LLM
    Graph -.->|optional traces| LF
```

### System Responsibilities

| Component | Owns | Does not own |
| --- | --- | --- |
| FinancialReports | Source acquisition, parsing, canonical facts, validation, quality, freshness, evidence | Investment conclusions and Agent orchestration |
| Financial Agent data layer | Provider selection, contract mapping, retry, cache, fallback, readiness | Parsing raw PDF/XBRL filings |
| Analysis services | Deterministic financial formulas and scores | Source acquisition or natural-language composition |
| LangGraph Agent | Intent, research planning, tool execution, contradiction checks, report composition | Recalculating financial facts inside the LLM |
| FastAPI | Stable HTTP boundary, status codes, thread-pool execution | Business formulas |
| Streamlit | Analyst interaction and visualization | Direct data/service access |

The UI always calls FastAPI. Financial Agent and FinancialReports communicate
through a versioned HTTP contract; they must not share a SQLite database file.
The LLM and Langfuse are optional. With no LLM key, deterministic routing and
report composition remain available.

## Data Layer Architecture

```mermaid
flowchart TD
    Caller[Service / Agent / Data API]
    Loader[DataLoader compatibility facade]
    Factory[get_data_provider]
    Choice{DATA_PROVIDER}
    Remote[FinancialReportsProvider]
    Cache[(In-memory TTL cache)]
    Fallback[FallbackFinancialDataProvider]
    Local[JsonFinancialDataProvider]
    RemoteAPI[FinancialReports HTTP API v1]
    Record[SnapshotRecord]
    Ready[DataReadinessService]

    Caller --> Loader
    Caller --> Ready
    Loader --> Factory
    Ready --> Factory
    Factory --> Choice
    Choice -->|json| Local
    Choice -->|financial_reports| Fallback
    Fallback --> Remote
    Fallback --> Local
    Remote --> RemoteAPI
    Remote <--> Cache
    Remote --> Record
    Local --> Record
    Record -->|snapshot + quality + freshness + evidence| Caller
```

### Provider Contract

Every provider implements these operations:

- `load_record(stock_code, period)`
- `list_available_periods(stock_code)`
- `list_all_stocks()`
- `get_context(stock_code, period)`
- `request_refresh(stock_code, period)`
- `get_job(job_id)`

`SnapshotRecord` carries a normalized `FinancialSnapshot` plus source,
schema version, quality, freshness, evidence, metrics, events, and status.
The legacy `DataLoader` remains as a facade so analysis services keep a stable
interface while the source changes.

### Fallback and Status Rules

| Condition | Behavior |
| --- | --- |
| Remote transport error or HTTP 5xx | Retry, then use stale cache or JSON fallback when enabled |
| Remote HTTP 404 | Return missing; never hide it with unrelated local data |
| Remote HTTP 422 or invalid contract | Return a contract error; do not fallback |
| Cached record past TTL during outage | Return it with `freshness.is_stale=true` |
| Quality score below threshold | Readiness becomes `low_quality` and Agent confidence is reduced |
| Remote refresh accepted | Return HTTP 202 and expose the job through `/api/data/jobs/{job_id}` |
| JSON provider refresh requested | Return HTTP 503 because local files cannot enqueue ingestion |

FinancialReports must expose the six v1 endpoints documented in
`MODIFICATION_PLAN.md`. Until that service is deployed, `DATA_PROVIDER=json`
is the supported default.

## Agent Layer Architecture

```mermaid
flowchart TD
    Request[AgentQuery]
    Intent[Intent router]
    Readiness[Data readiness]
    Planner[Research planner]
    Gate{Required data available?}
    Executor[Research executor]
    Tools[Typed financial tools]
    Services[Deterministic services]
    Results[ToolResult collection]
    Review[Evidence and contradiction review]
    Report[ResearchReport]
    Compose{LLM configured?}
    LLM[Constrained LLM composition]
    Deterministic[Deterministic Chinese composition]
    Response[AgentResponse]

    Request --> Intent --> Readiness --> Planner --> Gate
    Gate -->|yes| Executor
    Gate -->|no| Results
    Executor --> Tools --> Services --> Results
    Results --> Review --> Report --> Compose
    Compose -->|yes| LLM --> Response
    Compose -->|no| Deterministic --> Response
```

### Agent Execution Modes

| Mode | Planning behavior |
| --- | --- |
| `quick` | Run only the tool selected by intent |
| `auto` | Run one tool unless the query is a broad investment question |
| `research` | Run snapshot, trend, earnings quality, ROIC/WACC, and EWS; add peer and factor tools when peers are supplied |

Each tool returns the same `ToolResult` contract: status, finding, structured
data, evidence, warnings, missing fields, assumptions, confidence, and error.
Sentiment and guidance explicitly return `not_supported`; they never fabricate
a neutral result.

The final `ResearchReport` contains verdict, thesis, findings, evidence, risks,
contradictions, data gaps, watch items, and numeric confidence. The LLM may
phrase this report, but it receives the structured report and is not the source
of financial calculations.

## Runtime and Failure Boundaries

- FastAPI runs synchronous service and graph work in a thread pool.
- `/health/live` checks the process; `/health/ready` checks the configured data
  provider.
- Missing data uses structured 404/422 responses rather than generic 500s.
- Provider cache is process-local and is not shared across API workers.
- There is no authentication, durable job store, Redis, PostgreSQL, vector
  database, or multi-agent debate runtime in the current implementation.
- Financial analysis is decision support, not an autonomous trading system.

## Verification

The implemented boundary is covered by provider, readiness, tool-contract,
workflow, service, and API tests. GitNexus is used to re-index the repository,
check circular imports, and inspect cross-layer impact after structural changes.
