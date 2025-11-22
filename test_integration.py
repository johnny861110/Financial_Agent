"""Integration test for Financial Agent."""

import sys
import time

def test_streamlit_app():
    """Test if Streamlit app is running."""
    print("\n" + "="*60)
    print("Testing Streamlit Application")
    print("="*60)
    
    try:
        import requests
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✓ Streamlit app is running on http://localhost:8501")
            return True
        else:
            print(f"⚠ Streamlit returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to Streamlit: {e}")
        print("  Please ensure: streamlit run streamlit_app.py")
        return False


def test_models():
    """Test data models."""
    print("\n" + "="*60)
    print("Testing Data Models")
    print("="*60)
    
    try:
        from app.models import FinancialSnapshot, ManagementScore, EarningsQualityScore
        
        # Test FinancialSnapshot
        snapshot = FinancialSnapshot(
            stock_code="2330",
            company_name="TSMC",
            report_year=2023,
            report_season=3,
            report_period="2023Q3",
            currency="TWD",
            unit="thousand",
            cash_and_equivalents=1500000,
            accounts_receivable=300000,
            inventory=200000,
            total_assets=5000000,
            total_liabilities=2000000,
            equity=3000000,
            net_revenue=800000,
            gross_profit=400000,
            operating_income=300000,
            net_income=250000,
            eps=9.65
        )
        print(f"✓ FinancialSnapshot: {snapshot.company_name}")
        print(f"  Revenue: {snapshot.net_revenue:,}")
        print(f"  Net Income: {snapshot.net_income:,}")
        
        # Test ManagementScore
        mgmt_score = ManagementScore(
            tenure_stability=90.0,
            board_independence=66.7,
            insider_alignment=80.0,
            governance_red_flags=100.0,
            commentary="Good management quality",
            details={}
        )
        print(f"✓ ManagementScore: {mgmt_score.total:.1f}")
        
        # Test EarningsQualityScore
        eq_score = EarningsQualityScore(
            accrual_quality=75.0,
            working_capital_behavior=70.0,
            one_off_dependency=80.0,
            earnings_stability=85.0,
            red_flags=[],
            commentary="Good earnings quality",
            details={}
        )
        print(f"✓ EarningsQualityScore: {eq_score.total:.1f}")
        
        return True
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_services():
    """Test service layer."""
    print("\n" + "="*60)
    print("Testing Service Layer")
    print("="*60)
    
    try:
        from app.services import ManagementService
        
        service = ManagementService()
        score = service.calculate_score(
            ceo_tenure_years=5,
            cfo_tenure_years=4,
            board_independence_ratio=0.4,
            independent_directors=3,
            total_directors=9,
            family_controlled=False,
            insider_buys=3,
            insider_sells=1,
            governance_incidents=0,
            audit_issues=0,
            related_party_transactions=0
        )
        
        print(f"✓ ManagementService: Total Score = {score.total:.1f}")
        print(f"  - Tenure Stability: {score.tenure_stability:.1f}")
        print(f"  - Board Independence: {score.board_independence:.1f}")
        print(f"  - Insider Alignment: {score.insider_alignment:.1f}")
        print(f"  - Governance: {score.governance_red_flags:.1f}")
        
        return True
    except Exception as e:
        print(f"✗ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_pages():
    """Test UI pages can be imported."""
    print("\n" + "="*60)
    print("Testing UI Pages")
    print("="*60)
    
    try:
        from ui.pages import (
            snapshot, trend, peer, management,
            earnings_quality, roic_wacc, factor, ews
        )
        
        pages = [
            "snapshot", "trend", "peer", "management",
            "earnings_quality", "roic_wacc", "factor", "ews"
        ]
        
        for page in pages:
            print(f"✓ {page}.py imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ UI page import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_health():
    """Test FastAPI health endpoint."""
    print("\n" + "="*60)
    print("Testing API (Optional)")
    print("="*60)
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API is healthy: {data}")
            return True
        else:
            print(f"⚠ API returned: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("ℹ API not running (optional - use: uvicorn app.main:app --reload)")
        return True  # Not critical


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Financial Agent - Integration Test Suite")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Models", test_models()))
    results.append(("Services", test_services()))
    results.append(("UI Pages", test_ui_pages()))
    results.append(("Streamlit App", test_streamlit_app()))
    results.append(("API Health", test_api_health()))
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nResults: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\n📍 Access Streamlit UI: http://localhost:8501")
        return 0
    else:
        print(f"\n⚠ {total_count - passed_count} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
