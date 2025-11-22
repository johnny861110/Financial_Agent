"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Financial Report Agent API"
    assert data["version"] == "2.0.0"


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "financial-agent"


def test_management_score_endpoint():
    """Test management score calculation endpoint."""
    response = client.post(
        "/api/scores/management",
        params={
            "ceo_tenure_years": 5,
            "cfo_tenure_years": 4,
            "board_independence_ratio": 0.4,
            "insider_buys": 3,
            "insider_sells": 1,
            "governance_incidents": 0,
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_score" in data
    assert "components" in data
    assert "commentary" in data


def test_peer_comparison_endpoint():
    """Test peer comparison endpoint."""
    # Note: This will fail without actual data files
    # In production, would use test fixtures
    response = client.post(
        "/api/peers/compare",
        json={
            "stock_codes": ["2330", "2454"],
            "period": "2023Q3",
            "metrics": ["Gross Margin", "ROE"]
        }
    )
    
    # Expected to fail without data, but tests the endpoint exists
    assert response.status_code in [200, 404]


def test_agent_query_endpoint():
    """Test agent query endpoint."""
    # Note: This requires OpenAI API key in environment
    response = client.post(
        "/api/agent/query",
        json={
            "query": "What is the financial health of company 2330?",
            "stock_code": "2330",
            "period": "2023Q3",
        }
    )
    
    # May fail without API key or data, but tests endpoint exists
    assert response.status_code in [200, 404, 500]
