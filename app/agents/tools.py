"""Agent tools for LangGraph workflow."""

from typing import Optional, Dict, Any
from langchain.tools import tool
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


@tool
def tool_snapshot(stock_code: str, period: str) -> Dict[str, Any]:
    """
    Get financial snapshot for a specific stock and period.
    
    Args:
        stock_code: Stock ticker code (e.g., '2330')
        period: Period identifier (e.g., '2023Q3')
    
    Returns:
        Dictionary with financial snapshot data
    """
    result = snapshot_service.get_summary(stock_code, period)
    if result:
        return {"success": True, "data": result}
    return {"success": False, "error": "Data not found"}


@tool
def tool_trend(stock_code: str) -> Dict[str, Any]:
    """
    Analyze trends for a stock across multiple periods.
    
    Args:
        stock_code: Stock ticker code
    
    Returns:
        Dictionary with trend analysis
    """
    analysis = trend_service.analyze_trend(stock_code)
    if analysis:
        return {
            "success": True,
            "data": {
                "stock_code": analysis.stock_code,
                "company_name": analysis.company_name,
                "metrics": [
                    {
                        "name": m.metric_name,
                        "trend": m.trend_direction,
                        "latest": m.latest_value,
                        "yoy_change": m.yoy_change,
                    }
                    for m in analysis.metrics
                ],
                "summary": analysis.summary,
            }
        }
    return {"success": False, "error": "Insufficient data for trend analysis"}


@tool
def tool_peer_compare(stock_codes: str, period: str) -> Dict[str, Any]:
    """
    Compare multiple companies on key metrics.
    
    Args:
        stock_codes: Comma-separated stock codes (e.g., '2330,2454,3711')
        period: Period identifier (e.g., '2023Q3')
    
    Returns:
        Dictionary with peer comparison data
    """
    codes = [c.strip() for c in stock_codes.split(',')]
    analysis = peer_service.compare_peers(codes, period)
    if analysis:
        return {
            "success": True,
            "data": {
                "period": analysis.period,
                "comparisons": [
                    {
                        "metric": c.metric_name,
                        "companies": c.companies,
                        "values": c.values,
                        "best": c.best_performer,
                        "worst": c.worst_performer,
                    }
                    for c in analysis.comparisons
                ],
                "summary": analysis.summary,
            }
        }
    return {"success": False, "error": "Insufficient data for comparison"}


@tool
def tool_management_score(
    ceo_tenure: float = 0,
    cfo_tenure: float = 0,
    board_independence: float = 0.3,
    insider_buys: int = 0,
    insider_sells: int = 0,
    governance_incidents: int = 0,
) -> Dict[str, Any]:
    """
    Calculate management quality score.
    
    Args:
        ceo_tenure: CEO tenure in years
        cfo_tenure: CFO tenure in years
        board_independence: Board independence ratio (0-1)
        insider_buys: Number of insider buy transactions
        insider_sells: Number of insider sell transactions
        governance_incidents: Number of governance red flags
    
    Returns:
        Dictionary with management score
    """
    score = management_service.calculate_score(
        ceo_tenure_years=ceo_tenure,
        cfo_tenure_years=cfo_tenure,
        board_independence_ratio=board_independence,
        insider_buys=insider_buys,
        insider_sells=insider_sells,
        governance_incidents=governance_incidents,
    )
    return {
        "success": True,
        "data": {
            "total_score": score.total,
            "components": {
                "tenure_stability": score.tenure_stability,
                "board_independence": score.board_independence,
                "insider_alignment": score.insider_alignment,
                "governance": score.governance_red_flags,
            },
            "commentary": score.commentary,
        }
    }


@tool
def tool_earnings_quality_score(stock_code: str, period: str) -> Dict[str, Any]:
    """
    Calculate earnings quality score.
    
    Args:
        stock_code: Stock ticker code
        period: Period identifier
    
    Returns:
        Dictionary with earnings quality score
    """
    score = earnings_quality_service.calculate_score(stock_code, period)
    if score:
        return {
            "success": True,
            "data": {
                "total_score": score.total,
                "components": {
                    "accrual_quality": score.accrual_quality,
                    "working_capital": score.working_capital_behavior,
                    "one_off_dependency": score.one_off_dependency,
                    "earnings_stability": score.earnings_stability,
                },
                "red_flags": score.red_flags,
                "commentary": score.commentary,
            }
        }
    return {"success": False, "error": "Data not found"}


@tool
def tool_roic_wacc(stock_code: str, period: str, beta: float = 1.0) -> Dict[str, Any]:
    """
    Calculate ROIC vs WACC for value creation analysis.
    
    Args:
        stock_code: Stock ticker code
        period: Period identifier
        beta: Market beta (default 1.0)
    
    Returns:
        Dictionary with ROIC/WACC analysis
    """
    analysis = roic_wacc_service.analyze(stock_code, period, market_beta=beta)
    if analysis:
        return {
            "success": True,
            "data": {
                "roic": analysis.roic,
                "wacc": analysis.wacc,
                "spread": analysis.value_creation_gap,
                "creating_value": analysis.is_value_creating,
                "commentary": analysis.commentary,
            }
        }
    return {"success": False, "error": "Data not found"}


@tool
def tool_factor_exposure(stock_code: str, period: str, peers: str = "") -> Dict[str, Any]:
    """
    Calculate factor exposures.
    
    Args:
        stock_code: Stock ticker code
        period: Period identifier
        peers: Optional comma-separated peer stock codes
    
    Returns:
        Dictionary with factor exposures
    """
    peer_list = [p.strip() for p in peers.split(',')] if peers else None
    exposures = factor_service.calculate_exposures(stock_code, period, peer_list)
    if exposures:
        return {
            "success": True,
            "data": {
                "quality": exposures.quality,
                "value": exposures.value,
                "momentum": exposures.momentum,
                "size": exposures.size,
                "volatility": exposures.volatility,
                "commentary": exposures.commentary,
            }
        }
    return {"success": False, "error": "Insufficient data"}


@tool
def tool_capital_allocation(
    stock_code: str,
    period: str,
    dividends: float = 0,
    buybacks: float = 0,
    capex: float = 0,
) -> Dict[str, Any]:
    """
    Analyze capital allocation strategy.
    
    Args:
        stock_code: Stock ticker code
        period: Period identifier
        dividends: Dividends paid
        buybacks: Share buybacks
        capex: Capital expenditures
    
    Returns:
        Dictionary with capital allocation analysis
    """
    analysis = capital_allocation_service.analyze(
        stock_code, period, dividends, buybacks, capex
    )
    if analysis:
        return {
            "success": True,
            "data": {
                "total_shareholder_returns": analysis.total_shareholder_returns,
                "total_investment": analysis.total_investment,
                "allocation_mix": analysis.allocation_mix,
                "commentary": analysis.commentary,
            }
        }
    return {"success": False, "error": "Data not found"}


@tool
def tool_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment from earnings call or report text.
    (Placeholder implementation - would use NLP models)
    
    Args:
        text: Text to analyze
    
    Returns:
        Dictionary with sentiment analysis
    """
    # Placeholder implementation
    return {
        "success": True,
        "data": {
            "sentiment": "neutral",
            "confidence": 0.5,
            "note": "NLP sentiment analysis not yet implemented"
        }
    }


@tool
def tool_guidance_tracker(stock_code: str, period: str) -> Dict[str, Any]:
    """
    Track management guidance from earnings calls.
    (Placeholder implementation - would parse transcripts)
    
    Args:
        stock_code: Stock ticker code
        period: Period identifier
    
    Returns:
        Dictionary with guidance information
    """
    # Placeholder implementation
    return {
        "success": True,
        "data": {
            "guidance": "Not available",
            "note": "Guidance tracking not yet implemented"
        }
    }


@tool
def tool_ews(stock_code: str, period: str) -> Dict[str, Any]:
    """
    Run Early Warning System to detect financial red flags.
    
    Args:
        stock_code: Stock ticker code
        period: Period identifier
    
    Returns:
        Dictionary with early warning analysis
    """
    ews = ews_service.detect_warnings(stock_code, period)
    if ews:
        return {
            "success": True,
            "data": {
                "warning_level": ews.warning_level,
                "signal_count": ews.signal_count,
                "signals": [
                    {
                        "name": s.signal_name,
                        "severity": s.severity,
                        "description": s.description,
                    }
                    for s in ews.triggered_signals
                ],
                "recommendation": ews.recommendation,
                "commentary": ews.commentary,
            }
        }
    return {"success": False, "error": "Data not found"}


# Export all tools
ALL_TOOLS = [
    tool_snapshot,
    tool_trend,
    tool_peer_compare,
    tool_management_score,
    tool_earnings_quality_score,
    tool_roic_wacc,
    tool_factor_exposure,
    tool_capital_allocation,
    tool_sentiment,
    tool_guidance_tracker,
    tool_ews,
]
