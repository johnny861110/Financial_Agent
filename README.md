# Financial Report Agent

**Version:** 2.0  
**Audience:** Professional Fund Managers & Investment Teams  
**Tech Stack:** Python, FastAPI, Streamlit, LangGraph/LangChain, LLM API, JSON Financial Data

## Overview

The Financial Report Agent is a comprehensive AI-powered system designed to analyze financial reports and provide professional-grade investment insights. It combines structured analytics with textual intelligence through both a modern web UI (Streamlit) and REST API to answer natural language queries about company financials.

## Features

### Core Analytics
- **Snapshot Analysis**: Single-quarter financial metrics with derived calculations
- **Trend Analysis**: Multi-quarter trend identification
- **Peer Comparison**: Cross-sectional company comparisons

### Fund Manager Analytics
- **Management Quality Score**: Governance, tenure stability, insider alignment
- **Earnings Quality Score**: Accrual analysis, working capital behavior
- **ROIC vs WACC**: Value creation analysis
- **Factor Exposures**: Quality, value, momentum, size, volatility
- **Capital Allocation**: Dividend, buyback, capex analysis
- **Early Warning System**: Risk detection and red flags

### NLP Capabilities
- Sentiment analysis
- Guidance extraction
- Earnings call summarization

## Architecture

```
financial-agent/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── core/                # Configuration and utilities
│   ├── models/              # Pydantic data models
│   ├── services/            # Business logic services
│   ├── api/                 # REST API endpoints
│   └── agents/              # LangGraph agent workflows
├── ui/
│   ├── pages/               # Streamlit page modules
│   │   ├── snapshot.py      # Financial snapshot page
│   │   ├── trend.py         # Trend analysis page
│   │   ├── peer.py          # Peer comparison page
│   │   ├── management.py    # Management quality page
│   │   ├── earnings_quality.py  # Earnings quality page
│   │   ├── roic_wacc.py     # ROIC vs WACC page
│   │   ├── factor.py        # Factor exposure page
│   │   ├── ews.py           # Early warning system page
│   │   └── agent.py         # AI agent chat page
│   └── __init__.py
├── streamlit_app.py         # Streamlit application entry
├── tests/                   # Test suite
└── pyproject.toml           # Project configuration (uv)
```

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Using uv (Recommended)

1. Install uv:
```bash
pip install uv
```

2. Install dependencies:
```bash
uv sync
```

### Alternative: Using pip

```bash
pip install -e .
```

## Configuration

Create a `.env` file in the project root:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.0

# Data Configuration
DATA_DIR=./data
FINANCIAL_DATA_PATH=./data/financial_reports

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
```

## Usage

### Starting the Streamlit UI (Recommended for Users)

```bash
streamlit run streamlit_app.py
```

The web interface will be available at `http://localhost:8501`

**Features:**
- 📊 Interactive financial dashboards
- 📈 Trend visualization with charts
- 🔄 Peer comparison tables
- ⭐ Management quality scoring
- 💎 Earnings quality analysis
- 💰 ROIC vs WACC calculator
- 📐 Factor exposure radar charts
- 🚨 Early warning system
- 🤖 AI agent chat interface

### Starting the API Server (For Developers)

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Streamlit UI Pages

The Streamlit interface provides 9 interactive pages:

1. **📊 Snapshot**: Single-period financial metrics with KPIs and charts
2. **📈 Trend Analysis**: Multi-period trend visualization with indicators
3. **🔄 Peer Comparison**: Cross-sectional company benchmarking with radar charts
4. **⭐ Management Quality**: Governance scoring with component breakdown
5. **💎 Earnings Quality**: Accrual analysis and red flag detection
6. **💰 ROIC vs WACC**: Value creation analysis with sensitivity
7. **📐 Factor Exposure**: Investment factor z-scores and positioning
8. **🚨 Early Warning System**: Real-time risk monitoring and alerts
9. **🤖 AI Agent**: Natural language chat interface for queries

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

- `GET /api/financials/{stock}/{period}` - Get financial snapshot
- `GET /api/trend/{stock}` - Get trend analysis
- `POST /api/peers/compare` - Compare peer companies
- `GET /api/scores/management/{stock}/{period}` - Management quality score
- `GET /api/scores/earnings_quality/{stock}/{period}` - Earnings quality score
- `GET /api/roic_wacc/{stock}/{period}` - ROIC vs WACC analysis
- `POST /api/agent/query` - Natural language query to agent

### Example: Natural Language Query

```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the management quality of company 2330 in Q3 2023?",
    "stock_code": "2330",
    "period": "2023Q3"
  }'
```

## Data Format

The system expects financial data in the following JSON format:

```json
{
  "stock_code": "2330",
  "company_name": "TSMC",
  "report_year": 2023,
  "report_season": 3,
  "report_period": "2023Q3",
  "currency": "TWD",
  "unit": "thousand",
  "cash_and_equivalents": 1500000,
  "accounts_receivable": 300000,
  "inventory": 200000,
  "total_assets": 5000000,
  "total_liabilities": 2000000,
  "equity": 3000000,
  "net_revenue": 800000,
  "gross_profit": 400000,
  "operating_income": 300000,
  "net_income": 250000,
  "eps": 9.65
}
```

Place your financial data JSON files in the configured `FINANCIAL_DATA_PATH` directory with the naming convention:
`<ticker>_<period>_enhanced.json`

## Testing

Run the test suite:

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=app tests/
```

Or using pytest directly:

```bash
pytest
pytest --cov=app tests/
```

## Development

### Code Formatting

```bash
uv run black app/ tests/ ui/
```

### Linting

```bash
uv run flake8 app/ tests/ ui/
```

### Type Checking

```bash
uv run mypy app/
```

### Running Development Server

```bash
# API server with auto-reload
uv run uvicorn app.main:app --reload

# Streamlit UI with auto-reload (default behavior)
streamlit run streamlit_app.py
```

## Scoring Formulas

### Management Quality Score

$$M = 0.25T + 0.25B + 0.25I + 0.25G$$

Where:
- T = Tenure stability
- B = Board independence
- I = Insider alignment
- G = Governance (inverted red flags)

### Earnings Quality Score

$$E = 0.25AQ + 0.25WCB + 0.25OD + 0.25ES$$

Where:
- AQ = Accrual quality
- WCB = Working capital behavior
- OD = One-off dependency (inverted)
- ES = Earnings stability

## Roadmap

### Phase 1 – Core Agent ✓
- Snapshot, trend, peers analysis
- Basic API endpoints
- Basic agent workflow

### Phase 2 – Fund Manager Core Analytics (Current)
- Management score
- Earnings quality score
- ROIC/WACC analysis
- Early warning system

### Phase 3 – Advanced Insights (Planned)
- Factor exposures
- Sentiment analysis
- Guidance tracker
- Earnings call intelligence

## License

MIT License

## Support

For issues and questions, please open an issue on the GitHub repository.
