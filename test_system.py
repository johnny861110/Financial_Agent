"""Test script to verify project setup."""

import sys
from pathlib import Path

def test_imports():
    """Test all critical imports."""
    print("Testing imports...")
    
    try:
        # Core imports
        from app.models import (
            FinancialSnapshot, ManagementScore, EarningsQualityScore,
            ROICWACCAnalysis, FactorExposures, EarlyWarningSystem
        )
        print("  ✓ Models imported successfully")
        
        # Services
        from app.services import (
            SnapshotService, TrendService, PeerService,
            ManagementService, EarningsQualityService, ROICWACCService,
            FactorService, CapitalAllocationService, EarlyWarningService
        )
        print("  ✓ Services imported successfully")
        
        # API
        from app.api import financials, agent
        print("  ✓ API modules imported successfully")
        
        # Agents
        from app.agents.workflow import FinancialAgent
        from app.agents.tools import ALL_TOOLS
        print("  ✓ Agent modules imported successfully")
        
        # UI
        from ui.pages import (
            snapshot, trend, peer, management, 
            earnings_quality, roic_wacc, factor, ews, agent as agent_page
        )
        print("  ✓ UI pages imported successfully")
        
        return True
    except Exception as e:
        print(f"  ✗ Import error: {e}")
        return False


def test_data_structure():
    """Test data directory structure."""
    print("\nTesting data structure...")
    
    data_dir = Path("data/financial_reports")
    if data_dir.exists():
        files = list(data_dir.glob("*.json"))
        print(f"  ✓ Data directory exists with {len(files)} JSON files")
        return True
    else:
        print("  ⚠ Data directory not found")
        return False


def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        print(f"  ✓ Settings loaded")
        print(f"    - Data dir: {settings.data_dir}")
        print(f"    - API host: {settings.api_host}:{settings.api_port}")
        return True
    except Exception as e:
        print(f"  ✗ Config error: {e}")
        return False


def test_models():
    """Test model creation."""
    print("\nTesting models...")
    
    try:
        from app.models import FinancialSnapshot
        
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
        
        print(f"  ✓ FinancialSnapshot created")
        print(f"    - Gross margin: {snapshot.gross_margin:.2%}")
        print(f"    - Operating margin: {snapshot.operating_margin:.2%}")
        print(f"    - ROE: {snapshot.roe:.2%}")
        return True
    except Exception as e:
        print(f"  ✗ Model error: {e}")
        return False


def test_services():
    """Test services."""
    print("\nTesting services...")
    
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
        
        print(f"  ✓ ManagementService working")
        print(f"    - Total score: {score.total:.1f}")
        return True
    except Exception as e:
        print(f"  ✗ Service error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Financial Agent - System Test")
    print("="*60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Data Structure", test_data_structure()))
    results.append(("Configuration", test_config()))
    results.append(("Models", test_models()))
    results.append(("Services", test_services()))
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! System is ready.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
