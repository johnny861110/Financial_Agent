# Project Structure

```
Financial_Agent/
├── README.md                          # Main documentation
├── SPEC.md                            # Full specification (from attachment)
├── QUICKSTART.md                      # Quick start guide
├── SAMPLE_DATA.md                     # Sample data format guide
├── pyproject.toml                     # Poetry configuration
├── requirements.txt                   # pip dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── example.py                         # Usage examples
│
├── app/                               # Main application
│   ├── __init__.py
│   ├── main.py                        # FastAPI application entry point
│   │
│   ├── core/                          # Core configuration and utilities
│   │   ├── __init__.py
│   │   ├── config.py                  # Settings and configuration
│   │   ├── data_loader.py             # Data loading utilities
│   │   └── utils.py                   # Helper functions
│   │
│   ├── models/                        # Pydantic data models
│   │   ├── __init__.py                # All financial models
│   │   └── agent_models.py            # Agent-specific models
│   │
│   ├── services/                      # Business logic services
│   │   ├── __init__.py
│   │   ├── snapshot_service.py        # Single-period analysis
│   │   ├── trend_service.py           # Multi-period trends
│   │   ├── peer_service.py            # Peer comparison
│   │   ├── management_service.py      # Management quality scoring
│   │   ├── earnings_quality_service.py # Earnings quality scoring
│   │   ├── roic_wacc_service.py       # ROIC vs WACC analysis
│   │   ├── factor_service.py          # Factor exposure analysis
│   │   ├── capital_allocation_service.py # Capital allocation
│   │   └── ews_service.py             # Early Warning System
│   │
│   ├── agents/                        # LangGraph agent workflow
│   │   ├── __init__.py
│   │   ├── tools.py                   # Agent tools (LangChain)
│   │   └── workflow.py                # LangGraph workflow
│   │
│   └── api/                           # FastAPI endpoints
│       ├── __init__.py
│       ├── financials.py              # Financial endpoints
│       └── agent.py                   # Agent query endpoint
│
└── tests/                             # Test suite
    ├── __init__.py
    ├── conftest.py                    # Test fixtures
    ├── test_models.py                 # Model tests
    ├── test_services.py               # Service tests
    └── test_api.py                    # API tests
```

## Key Components

### 1. Data Models (`app/models/`)
- **FinancialSnapshot**: Core financial data with computed metrics
- **ManagementScore**: Management quality scoring (4 components)
- **EarningsQualityScore**: Earnings quality scoring (4 components)
- **ROICWACCAnalysis**: Value creation analysis
- **FactorExposures**: Factor exposure z-scores
- **EarlyWarningSystem**: Risk detection and red flags
- **AgentQuery/AgentResponse**: Agent interface models

### 2. Service Layer (`app/services/`)
- **SnapshotService**: Load and analyze single-period financials
- **TrendService**: Multi-period trend analysis
- **PeerService**: Cross-sectional peer comparison
- **ManagementService**: Calculate management quality scores
- **EarningsQualityService**: Assess earnings quality
- **ROICWACCService**: Analyze value creation (ROIC vs WACC)
- **FactorService**: Calculate factor exposures
- **CapitalAllocationService**: Analyze capital allocation
- **EarlyWarningService**: Detect financial red flags

### 3. Agent Layer (`app/agents/`)
- **FinancialAgent**: LangGraph-based conversational agent
- **Tools**: LangChain tools wrapping each service
- **Workflow**: Intent routing and answer composition

### 4. API Layer (`app/api/`)
- **REST Endpoints**: FastAPI routes for all services
- **Agent Endpoint**: Natural language query interface
- **Documentation**: Automatic Swagger/ReDoc generation

### 5. Core Utilities (`app/core/`)
- **Settings**: Configuration management
- **DataLoader**: JSON file loading
- **Utils**: Mathematical and formatting helpers

## API Endpoints

### Financial Analysis
- `GET /api/financials/{stock}/{period}` - Financial snapshot
- `GET /api/trend/{stock}` - Trend analysis
- `POST /api/peers/compare` - Peer comparison

### Scoring & Analytics
- `POST /api/scores/management` - Management quality score
- `GET /api/scores/earnings_quality/{stock}/{period}` - Earnings quality
- `GET /api/roic_wacc/{stock}/{period}` - ROIC vs WACC
- `GET /api/factors/{stock}/{period}` - Factor exposures
- `POST /api/capital_allocation/{stock}/{period}` - Capital allocation
- `GET /api/ews/{stock}/{period}` - Early Warning System

### Agent
- `POST /api/agent/query` - Natural language query

## Technologies Used

- **FastAPI**: Modern web framework for APIs
- **Pydantic**: Data validation and settings management
- **LangChain**: LLM integration framework
- **LangGraph**: Agent workflow orchestration
- **OpenAI GPT**: Language model for agent reasoning
- **Pandas/NumPy**: Data processing
- **Pytest**: Testing framework

## Next Steps

1. **Data Integration**: Connect to real financial data sources
2. **Authentication**: Add user authentication and API keys
3. **Caching**: Implement Redis caching for performance
4. **Database**: Move from JSON files to database (PostgreSQL)
5. **NLP Features**: Implement sentiment analysis and guidance extraction
6. **Monitoring**: Add logging and monitoring (e.g., Prometheus)
7. **Deployment**: Containerize with Docker, deploy to cloud
8. **Documentation**: Expand API documentation and examples

## Development Workflow

1. Add new service in `app/services/`
2. Create corresponding tool in `app/agents/tools.py`
3. Add node to workflow in `app/agents/workflow.py`
4. Create API endpoint in `app/api/`
5. Write tests in `tests/`
6. Update documentation

## License

MIT License - See README.md for details
