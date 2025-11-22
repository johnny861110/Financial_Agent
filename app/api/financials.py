"""API routers for financial endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.models import (
    FinancialSnapshot,
    TrendAnalysis,
    PeerAnalysis,
    ManagementScore,
    EarningsQualityScore,
    ROICWACCAnalysis,
    FactorExposures,
    CapitalAllocationAnalysis,
    EarlyWarningSystem,
)
from app.services import (
    SnapshotService,
    TrendService,
    PeerService,
    ManagementService,
    EarningsQualityService,
    ROICWACCService,
    FactorService,
    CapitalAllocationService,
    EarlyWarningService,
)

router = APIRouter(prefix="/api", tags=["financials"])

# Initialize services
snapshot_service = SnapshotService()
trend_service = TrendService()
peer_service = PeerService()
management_service = ManagementService()
earnings_quality_service = EarningsQualityService()
roic_wacc_service = ROICWACCService()
factor_service = FactorService()
capital_allocation_service = CapitalAllocationService()
ews_service = EarlyWarningService()


@router.get("/financials/{stock_code}/{period}")
async def get_financial_snapshot(stock_code: str, period: str):
    """Get financial snapshot for a specific stock and period."""
    result = snapshot_service.get_summary(stock_code, period)
    if not result:
        raise HTTPException(status_code=404, detail="Financial data not found")
    return result


@router.get("/trend/{stock_code}")
async def get_trend_analysis(stock_code: str, periods: Optional[str] = None):
    """
    Get trend analysis for a stock.
    
    Args:
        stock_code: Stock ticker code
        periods: Optional comma-separated list of periods
    """
    period_list = [p.strip() for p in periods.split(',')] if periods else None
    
    result = trend_service.analyze_trend(stock_code, period_list)
    if not result:
        raise HTTPException(status_code=404, detail="Insufficient data for trend analysis")
    
    return {
        "stock_code": result.stock_code,
        "company_name": result.company_name,
        "metrics": [
            {
                "metric_name": m.metric_name,
                "periods": m.periods,
                "values": m.values,
                "trend_direction": m.trend_direction,
                "latest_value": m.latest_value,
                "yoy_change": m.yoy_change,
            }
            for m in result.metrics
        ],
        "summary": result.summary,
    }


@router.post("/peers/compare")
async def compare_peers(
    stock_codes: List[str],
    period: str,
    metrics: Optional[List[str]] = None
):
    """
    Compare peer companies on key metrics.
    
    Args:
        stock_codes: List of stock codes to compare
        period: Period identifier
        metrics: Optional list of metrics to compare
    """
    result = peer_service.compare_peers(stock_codes, period, metrics)
    if not result:
        raise HTTPException(status_code=404, detail="Insufficient data for comparison")
    
    return {
        "period": result.period,
        "comparisons": [
            {
                "metric_name": c.metric_name,
                "companies": c.companies,
                "values": c.values,
                "ranking": c.ranking,
                "best_performer": c.best_performer,
                "worst_performer": c.worst_performer,
            }
            for c in result.comparisons
        ],
        "summary": result.summary,
    }


@router.post("/scores/management")
async def calculate_management_score(
    ceo_tenure_years: float = 0,
    cfo_tenure_years: float = 0,
    board_independence_ratio: float = 0.3,
    independent_directors: int = 0,
    total_directors: int = 0,
    family_controlled: bool = False,
    insider_buys: int = 0,
    insider_sells: int = 0,
    governance_incidents: int = 0,
    audit_issues: int = 0,
    related_party_transactions: int = 0,
):
    """Calculate management quality score."""
    result = management_service.calculate_score(
        ceo_tenure_years=ceo_tenure_years,
        cfo_tenure_years=cfo_tenure_years,
        board_independence_ratio=board_independence_ratio,
        independent_directors=independent_directors,
        total_directors=total_directors,
        family_controlled=family_controlled,
        insider_buys=insider_buys,
        insider_sells=insider_sells,
        governance_incidents=governance_incidents,
        audit_issues=audit_issues,
        related_party_transactions=related_party_transactions,
    )
    
    return {
        "total_score": result.total,
        "components": {
            "tenure_stability": result.tenure_stability,
            "board_independence": result.board_independence,
            "insider_alignment": result.insider_alignment,
            "governance_red_flags": result.governance_red_flags,
        },
        "commentary": result.commentary,
        "details": result.details,
    }


@router.get("/scores/earnings_quality/{stock_code}/{period}")
async def calculate_earnings_quality_score(stock_code: str, period: str):
    """Calculate earnings quality score."""
    result = earnings_quality_service.calculate_score(stock_code, period)
    if not result:
        raise HTTPException(status_code=404, detail="Data not found")
    
    return {
        "total_score": result.total,
        "components": {
            "accrual_quality": result.accrual_quality,
            "working_capital_behavior": result.working_capital_behavior,
            "one_off_dependency": result.one_off_dependency,
            "earnings_stability": result.earnings_stability,
        },
        "red_flags": result.red_flags,
        "commentary": result.commentary,
        "details": result.details,
    }


@router.get("/roic_wacc/{stock_code}/{period}")
async def analyze_roic_wacc(
    stock_code: str,
    period: str,
    beta: Optional[float] = None,
    cost_of_debt: Optional[float] = None,
    tax_rate: Optional[float] = None,
):
    """Analyze ROIC vs WACC for value creation."""
    result = roic_wacc_service.analyze(
        stock_code, period, beta, cost_of_debt, tax_rate
    )
    if not result:
        raise HTTPException(status_code=404, detail="Data not found")
    
    return {
        "nopat": result.nopat,
        "invested_capital": result.invested_capital,
        "roic": result.roic,
        "cost_of_equity": result.cost_of_equity,
        "cost_of_debt": result.cost_of_debt,
        "wacc": result.wacc,
        "value_creation_gap": result.value_creation_gap,
        "is_value_creating": result.is_value_creating,
        "commentary": result.commentary,
        "assumptions": result.assumptions,
    }


@router.get("/factors/{stock_code}/{period}")
async def calculate_factor_exposures(
    stock_code: str,
    period: str,
    peer_stocks: Optional[str] = None
):
    """
    Calculate factor exposures.
    
    Args:
        stock_code: Stock ticker code
        period: Period identifier
        peer_stocks: Optional comma-separated peer stock codes
    """
    peer_list = [p.strip() for p in peer_stocks.split(',')] if peer_stocks else None
    
    result = factor_service.calculate_exposures(stock_code, period, peer_list)
    if not result:
        raise HTTPException(status_code=404, detail="Insufficient data")
    
    return {
        "quality": result.quality,
        "value": result.value,
        "momentum": result.momentum,
        "size": result.size,
        "volatility": result.volatility,
        "commentary": result.commentary,
        "details": result.details,
    }


@router.post("/capital_allocation/{stock_code}/{period}")
async def analyze_capital_allocation(
    stock_code: str,
    period: str,
    dividends: float = 0.0,
    buybacks: float = 0.0,
    capex: float = 0.0,
    rd_expense: float = 0.0,
    ma_spending: float = 0.0,
):
    """Analyze capital allocation strategy."""
    result = capital_allocation_service.analyze(
        stock_code, period, dividends, buybacks, capex, rd_expense, ma_spending
    )
    if not result:
        raise HTTPException(status_code=404, detail="Data not found")
    
    return {
        "period": result.period,
        "dividends": result.dividends,
        "buybacks": result.buybacks,
        "capex": result.capex,
        "rd_expense": result.rd_expense,
        "ma_spending": result.ma_spending,
        "debt_change": result.debt_change,
        "total_shareholder_returns": result.total_shareholder_returns,
        "total_investment": result.total_investment,
        "allocation_mix": result.allocation_mix,
        "commentary": result.commentary,
    }


@router.get("/ews/{stock_code}/{period}")
async def detect_early_warnings(stock_code: str, period: str):
    """Run Early Warning System to detect financial red flags."""
    result = ews_service.detect_warnings(stock_code, period)
    if not result:
        raise HTTPException(status_code=404, detail="Data not found")
    
    return {
        "warning_level": result.warning_level,
        "signal_count": result.signal_count,
        "triggered_signals": [
            {
                "signal_name": s.signal_name,
                "severity": s.severity,
                "current_value": s.current_value,
                "threshold_value": s.threshold_value,
                "description": s.description,
            }
            for s in result.triggered_signals
        ],
        "recommendation": result.recommendation,
        "commentary": result.commentary,
    }
