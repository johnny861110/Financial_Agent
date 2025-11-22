# Quick Start Guide

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Financial_Agent
```

2. Install uv (if not already installed):
```bash
pip install uv
```

3. Install dependencies:
```bash
uv sync
```

This will:
- Create a virtual environment automatically
- Install all required packages
- Generate a lockfile for reproducible builds

4. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Alternative: Traditional Method

If you prefer not to use uv:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Running the Application

### Option 1: Streamlit UI (Recommended for End Users)

Launch the interactive web interface:

```bash
streamlit run streamlit_app.py
```

The UI will open automatically at `http://localhost:8501`

**Available Pages:**
- 📊 **Snapshot**: View financial metrics with charts
- 📈 **Trend**: Analyze multi-period trends
- 🔄 **Peer**: Compare with competitors
- ⭐ **Management**: Score management quality
- 💎 **Earnings Quality**: Assess earnings reliability
- 💰 **ROIC vs WACC**: Calculate value creation
- 📐 **Factor**: Analyze factor exposures
- 🚨 **Early Warning**: Monitor risk signals
- 🤖 **Agent**: Chat with AI assistant

### Option 2: API Server (For Developers)

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Or with uv:

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Usage

### Using the Streamlit UI

1. **Financial Snapshot Analysis**
   - Navigate to "📊 Snapshot" page
   - Enter stock code and period
   - View key metrics, margins, and balance sheet
   - Download data as JSON

2. **Trend Analysis**
   - Go to "📈 Trend" page
   - Select stock and time range
   - View line charts for each metric
   - Compare multiple metrics
   - Export trends to CSV

3. **Peer Comparison**
   - Open "🔄 Peer" page
   - Input multiple stock codes
   - Select metrics to compare
   - View bar charts and radar chart
   - Download comparison matrix

4. **Management Quality Scoring**
   - Visit "⭐ Management" page
   - Input management metrics (tenure, board independence, etc.)
   - Get component scores and overall rating
   - Review recommendations

5. **AI Agent Chat**
   - Access "🤖 Agent" page
   - Type natural language questions
   - View AI analysis with transparency
   - Export conversation history

### Using the API

### 1. Get Financial Snapshot

```bash
curl http://localhost:8000/api/financials/2330/2023Q3
```

### 2. Analyze Trends

```bash
curl http://localhost:8000/api/trend/2330
```

### 3. Compare Peers

```bash
curl -X POST http://localhost:8000/api/peers/compare \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["2330", "2454", "3711"],
    "period": "2023Q3",
    "metrics": ["Gross Margin", "ROE", "Debt Ratio"]
  }'
```

### 4. Calculate Management Score

```bash
curl -X POST "http://localhost:8000/api/scores/management?ceo_tenure_years=5&cfo_tenure_years=4&board_independence_ratio=0.4&insider_buys=3&insider_sells=1&governance_incidents=0"
```

### 5. Agent Natural Language Query

```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the management quality of TSMC in Q3 2023?",
    "stock_code": "2330",
    "period": "2023Q3"
  }'
```

## Data Setup

Place your financial data JSON files in the configured data directory (default: `./data/financial_reports/`).

Files should follow the naming convention:
```
<stock_code>_<period>_enhanced.json
```

Example:
```
2330_2023Q3_enhanced.json
2454_2023Q3_enhanced.json
```

## Running Tests

With uv:
```bash
uv run pytest
```

With coverage:
```bash
uv run pytest --cov=app tests/
```

Or directly:
```bash
pytest
pytest --cov=app tests/
```

## Development

Format code:
```bash
uv run black app/ tests/ ui/
```

Run linter:
```bash
uv run flake8 app/ tests/ ui/
```

Type checking:
```bash
uv run mypy app/
```

### Hot Reload Development

Both Streamlit and FastAPI support hot reload:

```bash
# Streamlit (auto-reload on file changes)
streamlit run streamlit_app.py

# FastAPI (auto-reload with --reload flag)
uvicorn app.main:app --reload
```

## Troubleshooting

### Missing OpenAI API Key
If you see authentication errors, make sure your `.env` file contains:
```
OPENAI_API_KEY=your_key_here
```

### Data Not Found Errors
Ensure your financial data files are in the correct directory with the correct naming format.

### Import Errors
Make sure all dependencies are installed:
```bash
uv sync
```

Or with pip:
```bash
pip install -e .
```

### Streamlit Port Conflicts
If port 8501 is already in use:
```bash
streamlit run streamlit_app.py --server.port 8502
```

### uv Not Found
Install uv first:
```bash
pip install uv
```

### Module Not Found in Streamlit
Make sure you're running from the project root:
```bash
cd Financial_Agent
streamlit run streamlit_app.py
```

## Next Steps

1. **Data Setup**: Add your financial data JSON files to `./data/financial_reports/`
2. **Customize UI**: Modify Streamlit pages in `ui/pages/` for your needs
3. **Extend Analysis**: Add new service modules in `app/services/`
4. **Configure Thresholds**: Adjust settings in `.env` or `app/core/config.py`
5. **Add Features**: 
   - Implement NLP sentiment analysis
   - Add earnings call transcripts
   - Create custom factor models
6. **Security**: Add authentication for production use
7. **Deploy**:
   - Streamlit: Use Streamlit Cloud or Docker
   - API: Deploy to cloud providers (AWS, Azure, GCP)
8. **Monitoring**: Set up logging and error tracking

## Useful Commands

```bash
# Install/update dependencies
uv sync

# Add a new package
uv add package-name

# Remove a package
uv remove package-name

# Run Streamlit UI
streamlit run streamlit_app.py

# Run API server
uvicorn app.main:app --reload

# Run tests
uv run pytest

# Format code
uv run black .

# Check types
uv run mypy app/
```
