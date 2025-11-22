"""Test configuration and fixtures."""

import pytest
import os
from pathlib import Path


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_financial_snapshot():
    """Provide sample financial snapshot data."""
    return {
        "stock_code": "2330",
        "company_name": "TSMC",
        "report_year": 2023,
        "report_season": 3,
        "report_period": "2023Q3",
        "currency": "TWD",
        "unit": "thousand",
        "cash_and_equivalents": 1000000,
        "accounts_receivable": 200000,
        "inventory": 150000,
        "total_assets": 5000000,
        "total_liabilities": 2000000,
        "equity": 3000000,
        "net_revenue": 800000,
        "gross_profit": 400000,
        "operating_income": 300000,
        "net_income": 250000,
        "eps": 9.65,
        "current_assets": 1500000,
        "current_liabilities": 500000,
        "operating_cash_flow": 280000,
    }


@pytest.fixture
def sample_snapshots_multi_period():
    """Provide sample multi-period snapshot data."""
    base = {
        "stock_code": "2330",
        "company_name": "TSMC",
        "currency": "TWD",
        "unit": "thousand",
        "cash_and_equivalents": 1000000,
        "accounts_receivable": 200000,
        "inventory": 150000,
        "total_assets": 5000000,
        "total_liabilities": 2000000,
        "equity": 3000000,
    }
    
    q1 = {**base, "report_year": 2023, "report_season": 1, "report_period": "2023Q1",
          "net_revenue": 700000, "gross_profit": 350000, "operating_income": 250000,
          "net_income": 200000, "eps": 7.73}
    
    q2 = {**base, "report_year": 2023, "report_season": 2, "report_period": "2023Q2",
          "net_revenue": 750000, "gross_profit": 375000, "operating_income": 275000,
          "net_income": 225000, "eps": 8.69}
    
    q3 = {**base, "report_year": 2023, "report_season": 3, "report_period": "2023Q3",
          "net_revenue": 800000, "gross_profit": 400000, "operating_income": 300000,
          "net_income": 250000, "eps": 9.65}
    
    return [q1, q2, q3]
