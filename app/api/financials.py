"""API routers for financial endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import List, NoReturn, Optional
from pydantic import BaseModel, Field
from app.core import InsufficientDataError
from app.services.factory import get_service_registry


class PeerCompareRequest(BaseModel):
    """Request body for peer company comparison."""

    stock_codes: List[str] = Field(..., min_length=2)
    period: str
    metrics: Optional[List[str]] = None


class ManagementScoreRequest(BaseModel):
    """Request body for management quality scoring."""

    ceo_tenure_years: float = 0
    cfo_tenure_years: float = 0
    board_independence_ratio: float = 0.3
    independent_directors: int = 0
    total_directors: int = 0
    family_controlled: bool = False
    insider_buys: int = 0
    insider_sells: int = 0
    governance_incidents: int = 0
    audit_issues: int = 0
    related_party_transactions: int = 0


class ROICWACCRequest(BaseModel):
    """Optional assumptions for ROIC/WACC analysis."""

    beta: Optional[float] = None
    cost_of_debt: Optional[float] = None
    tax_rate: Optional[float] = None


class FactorExposureRequest(BaseModel):
    """Optional peer universe for factor exposure analysis."""

    peer_stocks: Optional[List[str]] = None


class CapitalAllocationRequest(BaseModel):
    """Request body for capital allocation analysis."""

    dividends: float = 0.0
    buybacks: float = 0.0
    capex: float = 0.0
    rd_expense: float = 0.0
    ma_spending: float = 0.0


router = APIRouter(prefix="/api", tags=["financials"])


def _not_found(message: str) -> NoReturn:
    raise HTTPException(status_code=404, detail={"error": "not_found", "message": message})


def _insufficient_data(exc: InsufficientDataError) -> NoReturn:
    raise HTTPException(
        status_code=422,
        detail={
            "error": "insufficient_data",
            "message": str(exc),
            "missing_fields": exc.missing_fields,
        },
    )


@router.get("/financials/{stock_code}/{period}")
async def get_financial_snapshot(stock_code: str, period: str):
    """Get financial snapshot for a specific stock and period."""
    result = await run_in_threadpool(
        get_service_registry().snapshot.get_summary, stock_code, period
    )
    if not result:
        _not_found("Financial data not found")
    return result


@router.get("/trend/{stock_code}")
async def get_trend_analysis(stock_code: str, periods: Optional[str] = None):
    """
    Get trend analysis for a stock.

    Args:
        stock_code: Stock ticker code
        periods: Optional comma-separated list of periods
    """
    period_list = [p.strip() for p in periods.split(",")] if periods else None

    result = await run_in_threadpool(
        get_service_registry().trend.analyze_trend, stock_code, period_list
    )
    if not result:
        _not_found("Insufficient data for trend analysis")

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
async def compare_peers(request: PeerCompareRequest):
    """
    Compare peer companies on key metrics.

    Args:
        stock_codes: List of stock codes to compare
        period: Period identifier
        metrics: Optional list of metrics to compare
    """
    result = await run_in_threadpool(
        get_service_registry().peer.compare_peers,
        request.stock_codes,
        request.period,
        request.metrics,
    )
    if not result:
        _not_found("Insufficient data for comparison")

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
async def calculate_management_score(request: ManagementScoreRequest):
    """Calculate management quality score."""
    result = await run_in_threadpool(
        get_service_registry().management.calculate_score,
        ceo_tenure_years=request.ceo_tenure_years,
        cfo_tenure_years=request.cfo_tenure_years,
        board_independence_ratio=request.board_independence_ratio,
        independent_directors=request.independent_directors,
        total_directors=request.total_directors,
        family_controlled=request.family_controlled,
        insider_buys=request.insider_buys,
        insider_sells=request.insider_sells,
        governance_incidents=request.governance_incidents,
        audit_issues=request.audit_issues,
        related_party_transactions=request.related_party_transactions,
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
    try:
        result = await run_in_threadpool(
            get_service_registry().earnings_quality.calculate_score, stock_code, period
        )
    except InsufficientDataError as exc:
        _insufficient_data(exc)
    if not result:
        _not_found("Data not found")

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


@router.post("/roic_wacc/{stock_code}/{period}")
async def analyze_roic_wacc(
    stock_code: str,
    period: str,
    request: ROICWACCRequest = ROICWACCRequest(),
):
    """Analyze ROIC vs WACC for value creation."""
    try:
        result = await run_in_threadpool(
            get_service_registry().roic_wacc.analyze,
            stock_code,
            period,
            request.beta,
            request.cost_of_debt,
            request.tax_rate,
        )
    except InsufficientDataError as exc:
        _insufficient_data(exc)
    if not result:
        _not_found("Data not found")

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


@router.post("/factors/{stock_code}/{period}")
async def calculate_factor_exposures(
    stock_code: str,
    period: str,
    request: FactorExposureRequest = FactorExposureRequest(),
):
    """
    Calculate factor exposures.

    Args:
        stock_code: Stock ticker code
        period: Period identifier
        peer_stocks: Optional comma-separated peer stock codes
    """
    try:
        result = await run_in_threadpool(
            get_service_registry().factor.calculate_exposures,
            stock_code,
            period,
            request.peer_stocks,
        )
    except InsufficientDataError as exc:
        _insufficient_data(exc)
    if not result:
        _not_found("Insufficient data")

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
    request: CapitalAllocationRequest,
):
    """Analyze capital allocation strategy."""
    result = await run_in_threadpool(
        get_service_registry().capital_allocation.analyze,
        stock_code,
        period,
        request.dividends,
        request.buybacks,
        request.capex,
        request.rd_expense,
        request.ma_spending,
    )
    if not result:
        _not_found("Data not found")

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
    try:
        result = await run_in_threadpool(
            get_service_registry().ews.detect_warnings, stock_code, period
        )
    except InsufficientDataError as exc:
        _insufficient_data(exc)
    if not result:
        _not_found("Data not found")

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
