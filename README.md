# Financial Report Agent

**Version:** 2.0  
**Audience:** Professional fund managers, investment analysts, and research teams  
**Stack:** Python, FastAPI, Streamlit, LangGraph/LangChain, OpenAI-compatible LLMs, Langfuse, local JSON financial data

## Overview

Financial Report Agent is a financial analysis application for structured company financial reports. It combines deterministic Python services for calculations with a LangGraph agent for natural-language routing and answer composition.

The current default UI examples use **世芯-KY (`3661`) / `2025Q1`**.

The project exposes:

- A **Streamlit UI** for dashboards and agent chat.
- A **FastAPI backend** for programmatic financial analysis.
- A **LangGraph agent** that classifies user intent and calls the relevant service.
- A local JSON data loader for `data/financial_reports/*_enhanced.json`.

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

- Routes natural-language questions to the right analytical tool.
- Uses an LLM when `OPENAI_API_KEY` is configured.
- Falls back to deterministic keyword routing when no API key is available.
- Reports missing required fields instead of returning opaque server errors.

### Placeholder / Roadmap Features

The following concepts exist in docs or tool stubs but are not complete production features yet:

- Sentiment analysis.
- Guidance tracking.
- Earnings call transcript intelligence.
- PostgreSQL, Redis, pgvector, and market-data ingestion.
- Investment memo PDF export.
- Multi-agent bull/bear/PM debate workflow.

## Architecture

```text
Financial_Agent/
├── app/
│   ├── main.py                  # FastAPI application entry
│   ├── api/
│   │   ├── financials.py        # Financial analysis endpoints
│   │   └── agent.py             # Agent query endpoint
│   ├── agents/
│   │   ├── workflow.py          # LangGraph FinancialAgent workflow
│   │   └── tools.py             # LangChain tools wrapping services
│   ├── core/
│   │   ├── config.py            # Settings and env vars
│   │   ├── data_loader.py       # JSON data loading
│   │   └── utils.py             # Math helpers and data validation helpers
│   ├── models/                  # Pydantic models
│   └── services/                # Deterministic financial calculation services
├── ui/
│   └── pages/                   # Streamlit pages
├── data/financial_reports/      # Local financial JSON files
├── tests/                       # Test suite
├── streamlit_app.py             # Streamlit entry point
├── convert_financial_report.py  # JSON format conversion utility
├── Dockerfile
├── docker-compose.yaml
└── pyproject.toml
```

High-level flow:

```text
User
  -> Streamlit UI or FastAPI
  -> API route / Agent route
  -> deterministic service or LangGraph workflow
  -> DataLoader
  -> local JSON financial reports
  -> structured result / agent answer
```

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

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
API_CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

# Logging
LOG_LEVEL=INFO
```

Langfuse is optional. If `LANGFUSE_ENABLED=true`, provide a valid public key, secret key, and base URL. If `LANGFUSE_REQUIRED=true`, startup fails when Langfuse is misconfigured.

## Running Locally

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

Open:

```text
http://localhost:8501
```

### FastAPI

```bash
uv run uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
http://localhost:8000/redoc
```

## Docker

Build and start both API and UI:

```bash
docker compose up -d --build
```

Services:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8501`

Check status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f api
docker compose logs -f ui
```

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
uv run mypy app/
```

Compile-check Python files:

```bash
python3 -m compileall app ui tests
```

Format code:

```bash
uv run black app tests ui streamlit_app.py
```

## Implementation Status

| Area | Status | Notes |
| --- | --- | --- |
| JSON financial data loading | Implemented | Local `*_enhanced.json` files. |
| Snapshot analysis | Implemented | Uses deterministic service logic. |
| Trend analysis | Implemented | Uses all available periods for a stock. |
| Peer comparison | Implemented | Requires at least two loaded companies. |
| Management score | Implemented | Input-driven governance scoring. |
| Earnings quality | Implemented with source-data constraints | Returns `422` when required fields are missing. |
| ROIC/WACC | Implemented with proxy assumptions | Uses CAPM-style defaults and book-value capital weights. |
| Factor exposure | Implemented with proxy assumptions | Needs enough complete peer records for z-scores. |
| Early warning system | Implemented | Rule-based red flag detection. |
| Capital allocation | Partial | Debt change is still a placeholder. |
| LangGraph agent | Implemented | LLM routing plus deterministic fallback. |
| Langfuse tracing | Optional | Controlled by env vars. |
| Sentiment / guidance tools | Placeholder | Stubs only. |
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
- Add or update Pydantic models in `app/models/`.
- Expose service functionality through `app/api/financials.py`.
- Add agent-accessible wrappers in `app/agents/tools.py`.
- Add route logic in `app/agents/workflow.py` when a new agent intent is needed.
- Add tests for service behavior and API response semantics.

## License

MIT License
