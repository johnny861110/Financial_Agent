"""Agent tools for LangGraph workflow."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from langchain.tools import tool
from app.agents.contracts import ToolRequirements, ToolResult, ToolStatus
from app.core import DataLoader, InsufficientDataError
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

# Requirements are imported from the owning service, never restated here, so a
# service's required-field list and the planner's gate cannot drift apart.
from app.services.earnings_quality_service import (
    EARNINGS_QUALITY_REQUIRED_FIELDS,
    MONEY_UNIT,
)
from app.services.ews_service import EWS_REQUIRED_FIELDS
from app.services.factor_service import EPS_UNIT, FACTOR_MONEY_FIELDS
from app.services.roic_wacc_service import ROIC_WACC_REQUIRED_FIELDS


# Only "present" clears a required field. missing/null/not_applicable/
# provider_failure all block, and so does a field whose state could not be
# determined -- an undeterminable field must never read as eligible.
USABLE_FIELD_STATE = "present"
UNKNOWN_FIELD_STATE = "unknown"


TOOL_REQUIREMENTS: dict[str, ToolRequirements] = {
    # Best-effort tools: they degrade per-metric rather than failing outright,
    # so they declare no hard field gate. Declared explicitly (not omitted) so a
    # tool can never fall through the gate by simply being absent.
    "snapshot": ToolRequirements(),
    "trend": ToolRequirements(),
    "peer": ToolRequirements(),
    "capital_allocation": ToolRequirements(),
    # Scored entirely from caller-supplied assumptions.
    "management": ToolRequirements(uses_filing_data=False),
    "sentiment": ToolRequirements(uses_filing_data=False),
    "guidance": ToolRequirements(uses_filing_data=False),
    # Tools with a hard required-field contract enforced by their service.
    "earnings_quality": ToolRequirements(
        required_fields=EARNINGS_QUALITY_REQUIRED_FIELDS,
        expected_unit=MONEY_UNIT,
    ),
    "roic_wacc": ToolRequirements(
        required_fields=ROIC_WACC_REQUIRED_FIELDS,
        expected_unit=MONEY_UNIT,
    ),
    "ews": ToolRequirements(
        required_fields=EWS_REQUIRED_FIELDS,
        expected_unit=MONEY_UNIT,
    ),
    "factor": ToolRequirements(
        required_fields=FACTOR_MONEY_FIELDS,
        expected_unit=MONEY_UNIT,
        extra_unit_fields={"eps_basic": EPS_UNIT},
    ),
}


def required_fields_for_planning() -> list[str]:
    """Every field any tool may gate on, for one batched field-state lookup."""
    fields: list[str] = []
    for requirements in TOOL_REQUIREMENTS.values():
        for field in requirements.all_required_fields:
            if field not in fields:
                fields.append(field)
    return fields


def evaluate_eligibility(
    tool_name: str,
    field_states: dict[str, str],
    *,
    quality_score: float | None = None,
    is_stale: bool = False,
    failed_rules: Optional[list[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Decide whether a tool may run, before invoking it.

    Returns None when the tool is eligible, otherwise the blocked ToolResult
    payload explaining which fields and rules made it ineligible.
    """
    requirements = TOOL_REQUIREMENTS.get(tool_name)
    if requirements is None or not requirements.uses_filing_data:
        return None

    blocked = {
        field: field_states.get(field, UNKNOWN_FIELD_STATE)
        for field in requirements.all_required_fields
        if field_states.get(field, UNKNOWN_FIELD_STATE) != USABLE_FIELD_STATE
    }
    blocking_rules = sorted(set(failed_rules or []) & set(requirements.blocking_validation_rules))

    reasons: list[str] = []
    if blocked:
        reasons.append(
            "unavailable fields: "
            + ", ".join(f"{field} ({state})" for field, state in sorted(blocked.items()))
        )
    if blocking_rules:
        reasons.append("failed validations: " + ", ".join(blocking_rules))
    if not requirements.allows_stale and is_stale:
        reasons.append("the filing data is stale and this tool requires fresh data")
    if (
        requirements.min_quality is not None
        and quality_score is not None
        and quality_score < requirements.min_quality
    ):
        reasons.append(
            f"data quality {quality_score:.2f} is below the required "
            f"{requirements.min_quality:.2f}"
        )

    if not reasons:
        return None

    return _result(
        tool_name,
        "insufficient_data",
        finding=f"{tool_name} was not run because " + "; ".join(reasons),
        missing_fields=sorted(blocked),
        blocked_fields=blocked,
        failed_rules=blocking_rules,
        confidence=0.0,
        error="insufficient_data",
    )


@dataclass
class AgentToolServices:
    """Service registry sharing one configured data loader."""

    snapshot: SnapshotService
    trend: TrendService
    peer: PeerService
    management: ManagementService
    earnings_quality: EarningsQualityService
    roic_wacc: ROICWACCService
    factor: FactorService
    capital_allocation: CapitalAllocationService
    ews: EarlyWarningService

    @classmethod
    def build(cls, data_loader: DataLoader | None = None) -> "AgentToolServices":
        loader = data_loader or DataLoader()
        return cls(
            snapshot=SnapshotService(loader),
            trend=TrendService(loader),
            peer=PeerService(loader),
            management=ManagementService(),
            earnings_quality=EarningsQualityService(loader),
            roic_wacc=ROICWACCService(loader),
            factor=FactorService(loader),
            capital_allocation=CapitalAllocationService(loader),
            ews=EarlyWarningService(loader),
        )


_service_registry: AgentToolServices | None = None


def configure_tool_services(data_loader: DataLoader) -> None:
    """Bind agent tools to the agent's configured data source."""
    global _service_registry
    _service_registry = AgentToolServices.build(data_loader)


def get_tool_services() -> AgentToolServices:
    global _service_registry
    if _service_registry is None:
        _service_registry = AgentToolServices.build()
    return _service_registry


def _result(
    tool_name: str,
    status: ToolStatus,
    *,
    finding: str = "",
    data: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    missing_fields: list[str] | None = None,
    assumptions: dict[str, Any] | None = None,
    confidence: float = 0.0,
    error: str | None = None,
    blocked_fields: dict[str, str] | None = None,
    failed_rules: list[str] | None = None,
) -> Dict[str, Any]:
    return ToolResult(
        tool=tool_name,
        status=status,
        finding=finding,
        data=data or {},
        evidence=evidence or [],
        warnings=warnings or [],
        missing_fields=missing_fields or [],
        assumptions=assumptions or {},
        confidence=confidence,
        error=error,
        blocked_fields=blocked_fields or {},
        failed_rules=failed_rules or [],
    ).model_dump(mode="json")


def _insufficient_data_response(tool_name: str, exc: InsufficientDataError) -> Dict[str, Any]:
    """Return a tool-friendly structured insufficient data response."""
    return _result(
        tool_name,
        "insufficient_data",
        finding=str(exc),
        missing_fields=exc.missing_fields,
        confidence=0.0,
        error="insufficient_data",
    )


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
    result = get_tool_services().snapshot.get_summary(stock_code, period)
    if result:
        return _result(
            "snapshot",
            "success",
            finding="Financial snapshot loaded",
            data=result,
            confidence=0.85,
        )
    return _result("snapshot", "not_found", error="Data not found")


@tool
def tool_trend(stock_code: str) -> Dict[str, Any]:
    """
    Analyze trends for a stock across multiple periods.

    Args:
        stock_code: Stock ticker code

    Returns:
        Dictionary with trend analysis
    """
    analysis = get_tool_services().trend.analyze_trend(stock_code)
    if analysis:
        return _result(
            "trend",
            "success",
            finding=analysis.summary,
            data={
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
            },
            confidence=0.8,
        )
    return _result("trend", "insufficient_data", error="Insufficient data for trend analysis")


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
    codes = [c.strip() for c in stock_codes.split(",")]
    analysis = get_tool_services().peer.compare_peers(codes, period)
    if analysis:
        return _result(
            "peer",
            "success",
            finding=analysis.summary,
            data={
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
            },
            confidence=0.75,
        )
    return _result("peer", "insufficient_data", error="Insufficient data for comparison")


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
    score = get_tool_services().management.calculate_score(
        ceo_tenure_years=ceo_tenure,
        cfo_tenure_years=cfo_tenure,
        board_independence_ratio=board_independence,
        insider_buys=insider_buys,
        insider_sells=insider_sells,
        governance_incidents=governance_incidents,
    )
    assumptions = {
        "ceo_tenure": ceo_tenure,
        "cfo_tenure": cfo_tenure,
        "board_independence": board_independence,
        "insider_buys": insider_buys,
        "insider_sells": insider_sells,
        "governance_incidents": governance_incidents,
    }
    return _result(
        "management",
        "success",
        finding=score.commentary,
        data={
            "total_score": score.total,
            "components": {
                "tenure_stability": score.tenure_stability,
                "board_independence": score.board_independence,
                "insider_alignment": score.insider_alignment,
                "governance": score.governance_red_flags,
            },
            "commentary": score.commentary,
        },
        assumptions=assumptions,
        warnings=["Management score is based on supplied assumptions, not filing facts"],
        confidence=0.5,
    )


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
    try:
        score = get_tool_services().earnings_quality.calculate_score(stock_code, period)
    except InsufficientDataError as exc:
        return _insufficient_data_response("earnings_quality", exc)
    if score:
        return _result(
            "earnings_quality",
            "success",
            finding=score.commentary,
            data={
                "total_score": score.total,
                "components": {
                    "accrual_quality": score.accrual_quality,
                    "working_capital": score.working_capital_behavior,
                    "one_off_dependency": score.one_off_dependency,
                    "earnings_stability": score.earnings_stability,
                },
                "red_flags": score.red_flags,
                "commentary": score.commentary,
            },
            warnings=score.red_flags,
            confidence=0.8 if not score.red_flags else 0.7,
        )
    return _result("earnings_quality", "not_found", error="Data not found")


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
    try:
        analysis = get_tool_services().roic_wacc.analyze(stock_code, period, market_beta=beta)
    except InsufficientDataError as exc:
        return _insufficient_data_response("roic_wacc", exc)
    if analysis:
        return _result(
            "roic_wacc",
            "success",
            finding=analysis.commentary,
            data={
                "roic": analysis.roic,
                "wacc": analysis.wacc,
                "spread": analysis.value_creation_gap,
                "creating_value": analysis.is_value_creating,
                "commentary": analysis.commentary,
            },
            assumptions=analysis.assumptions,
            confidence=0.75,
        )
    return _result("roic_wacc", "not_found", error="Data not found")


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
    peer_list = [p.strip() for p in peers.split(",")] if peers else None
    try:
        exposures = get_tool_services().factor.calculate_exposures(stock_code, period, peer_list)
    except InsufficientDataError as exc:
        return _insufficient_data_response("factor", exc)
    if exposures:
        return _result(
            "factor",
            "success",
            finding=exposures.commentary,
            data={
                "quality": exposures.quality,
                "value": exposures.value,
                "momentum": exposures.momentum,
                "size": exposures.size,
                "volatility": exposures.volatility,
                "commentary": exposures.commentary,
            },
            confidence=0.65,
        )
    return _result("factor", "insufficient_data", error="Insufficient data")


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
    analysis = get_tool_services().capital_allocation.analyze(
        stock_code, period, dividends, buybacks, capex
    )
    if analysis:
        assumptions = {"dividends": dividends, "buybacks": buybacks, "capex": capex}
        return _result(
            "capital_allocation",
            "success",
            finding=analysis.commentary,
            data={
                "total_shareholder_returns": analysis.total_shareholder_returns,
                "total_investment": analysis.total_investment,
                "allocation_mix": analysis.allocation_mix,
                "commentary": analysis.commentary,
            },
            assumptions=assumptions,
            warnings=["Capital allocation inputs are caller-supplied assumptions"],
            confidence=0.5,
        )
    return _result("capital_allocation", "not_found", error="Data not found")


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
    return _result(
        "sentiment",
        "not_supported",
        error="Sentiment analysis is not implemented",
    )


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
    return _result(
        "guidance",
        "not_supported",
        error="Guidance tracking is not implemented",
    )


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
    try:
        ews = get_tool_services().ews.detect_warnings(stock_code, period)
    except InsufficientDataError as exc:
        return _insufficient_data_response("ews", exc)
    if ews:
        return _result(
            "ews",
            "success",
            finding=ews.commentary,
            data={
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
            },
            warnings=[signal.description for signal in ews.triggered_signals],
            confidence=0.8,
        )
    return _result("ews", "not_found", error="Data not found")


# Planner-facing name -> tool. The planner, the executor, and TOOL_REQUIREMENTS
# are all keyed by these names; test_tool_eligibility asserts the registries stay
# in step, so a new tool cannot reach the planner without declaring what it needs.
TOOL_REGISTRY = {
    "snapshot": tool_snapshot,
    "trend": tool_trend,
    "peer": tool_peer_compare,
    "management": tool_management_score,
    "earnings_quality": tool_earnings_quality_score,
    "roic_wacc": tool_roic_wacc,
    "factor": tool_factor_exposure,
    "capital_allocation": tool_capital_allocation,
    "sentiment": tool_sentiment,
    "guidance": tool_guidance_tracker,
    "ews": tool_ews,
}

# Export all tools
ALL_TOOLS = list(TOOL_REGISTRY.values())
