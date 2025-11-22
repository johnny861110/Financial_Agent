"""Tests for services."""

import pytest
from app.services import ManagementService, EarningsQualityService, ROICWACCService


def test_management_service_tenure_scoring():
    """Test management service tenure scoring."""
    service = ManagementService()
    
    # Test with good tenure
    score = service.calculate_score(
        ceo_tenure_years=5,
        cfo_tenure_years=4,
        board_independence_ratio=0.4,
        insider_buys=3,
        insider_sells=1,
        governance_incidents=0,
    )
    
    assert score.total > 60  # Should be good overall
    assert score.tenure_stability > 70  # Good tenure
    assert score.governance_red_flags == 100  # No incidents


def test_management_service_poor_governance():
    """Test management service with governance issues."""
    service = ManagementService()
    
    score = service.calculate_score(
        ceo_tenure_years=1,
        cfo_tenure_years=1,
        board_independence_ratio=0.2,
        insider_buys=0,
        insider_sells=5,
        governance_incidents=3,
    )
    
    assert score.total < 50  # Should be poor overall
    assert score.governance_red_flags < 50  # Multiple incidents


def test_roic_wacc_service_calculation():
    """Test ROIC/WACC service calculations."""
    # This would require mock data or test fixtures
    # Placeholder for now
    service = ROICWACCService()
    assert service is not None


def test_earnings_quality_service():
    """Test earnings quality service."""
    # This would require mock data or test fixtures
    # Placeholder for now
    service = EarningsQualityService()
    assert service is not None
