"""Tests for financial models."""

import pytest
from app.models import (
    FinancialSnapshot,
    ManagementScore,
    EarningsQualityScore,
    ROICWACCAnalysis,
    FactorExposures,
    EarlyWarningSystem,
)


def test_financial_snapshot_computed_fields():
    """Test computed fields in FinancialSnapshot."""
    snapshot = FinancialSnapshot(
        stock_code="2330",
        company_name="TSMC",
        report_year=2023,
        report_season=3,
        report_period="2023Q3",
        currency="TWD",
        unit="thousand",
        cash_and_equivalents=1000000,
        accounts_receivable=200000,
        inventory=150000,
        total_assets=5000000,
        total_liabilities=2000000,
        equity=3000000,
        net_revenue=800000,
        gross_profit=400000,
        operating_income=300000,
        net_income=250000,
        eps=9.65,
    )
    
    # Test margin calculations
    assert snapshot.gross_margin == 50.0
    assert snapshot.operating_margin == 37.5
    assert snapshot.net_margin == 31.25
    
    # Test balance sheet ratios
    assert snapshot.debt_ratio == 40.0
    assert snapshot.equity_ratio == 60.0
    
    # Test return metrics
    assert snapshot.roa > 0
    assert snapshot.roe > 0


def test_management_score_calculation():
    """Test ManagementScore total calculation."""
    score = ManagementScore(
        tenure_stability=80.0,
        board_independence=70.0,
        insider_alignment=60.0,
        governance_red_flags=90.0,
        commentary="Test"
    )
    
    expected_total = (80 + 70 + 60 + 90) / 4
    assert score.total == expected_total


def test_earnings_quality_score_calculation():
    """Test EarningsQualityScore total calculation."""
    score = EarningsQualityScore(
        accrual_quality=75.0,
        working_capital_behavior=80.0,
        one_off_dependency=70.0,
        earnings_stability=85.0,
        commentary="Test"
    )
    
    expected_total = (75 + 80 + 70 + 85) / 4
    assert score.total == expected_total


def test_roic_wacc_value_creation():
    """Test ROIC/WACC value creation calculation."""
    analysis = ROICWACCAnalysis(
        nopat=100000,
        invested_capital=1000000,
        roic=15.0,
        cost_of_equity=8.0,
        cost_of_debt=3.0,
        wacc=10.0,
        commentary="Test"
    )
    
    assert analysis.value_creation_gap == 5.0
    assert analysis.is_value_creating is True


def test_roic_wacc_value_destruction():
    """Test ROIC/WACC when destroying value."""
    analysis = ROICWACCAnalysis(
        nopat=50000,
        invested_capital=1000000,
        roic=5.0,
        cost_of_equity=8.0,
        cost_of_debt=3.0,
        wacc=10.0,
        commentary="Test"
    )
    
    assert analysis.value_creation_gap == -5.0
    assert analysis.is_value_creating is False


def test_early_warning_system_signal_count():
    """Test EarlyWarningSystem signal count."""
    from app.models import EarlyWarningSignal
    
    signals = [
        EarlyWarningSignal(
            signal_name="Test Signal 1",
            severity="medium",
            current_value=100.0,
            threshold_value=80.0,
            description="Test"
        ),
        EarlyWarningSignal(
            signal_name="Test Signal 2",
            severity="high",
            current_value=200.0,
            threshold_value=150.0,
            description="Test"
        )
    ]
    
    ews = EarlyWarningSystem(
        warning_level="high",
        triggered_signals=signals,
        recommendation="Review immediately"
    )
    
    assert ews.signal_count == 2
