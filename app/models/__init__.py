"""Financial data models."""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, computed_field


class FinancialSnapshot(BaseModel):
    """Core financial snapshot model containing all normalized fields."""
    
    # Identification
    stock_code: str
    company_name: str
    report_year: int
    report_season: int
    report_period: str
    currency: str = "TWD"
    unit: str = "thousand"
    
    # Balance Sheet
    cash_and_equivalents: float
    accounts_receivable: float
    inventory: float
    total_assets: float
    total_liabilities: float
    equity: float
    
    # Income Statement
    net_revenue: float
    gross_profit: float
    operating_income: float
    net_income: float
    eps: float
    
    # Optional fields for deeper analysis
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    retained_earnings: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    
    @computed_field
    @property
    def gross_margin(self) -> float:
        """Gross profit margin percentage."""
        if self.net_revenue == 0:
            return 0.0
        return (self.gross_profit / self.net_revenue) * 100
    
    @computed_field
    @property
    def operating_margin(self) -> float:
        """Operating margin percentage."""
        if self.net_revenue == 0:
            return 0.0
        return (self.operating_income / self.net_revenue) * 100
    
    @computed_field
    @property
    def net_margin(self) -> float:
        """Net profit margin percentage."""
        if self.net_revenue == 0:
            return 0.0
        return (self.net_income / self.net_revenue) * 100
    
    @computed_field
    @property
    def debt_ratio(self) -> float:
        """Total liabilities to total assets ratio."""
        if self.total_assets == 0:
            return 0.0
        return (self.total_liabilities / self.total_assets) * 100
    
    @computed_field
    @property
    def equity_ratio(self) -> float:
        """Equity to total assets ratio."""
        if self.total_assets == 0:
            return 0.0
        return (self.equity / self.total_assets) * 100
    
    @computed_field
    @property
    def current_ratio(self) -> Optional[float]:
        """Current assets to current liabilities ratio."""
        if self.current_assets and self.current_liabilities and self.current_liabilities != 0:
            return self.current_assets / self.current_liabilities
        return None
    
    @computed_field
    @property
    def roa(self) -> float:
        """Return on Assets (ROA) - annualized."""
        if self.total_assets == 0:
            return 0.0
        quarterly_roa = (self.net_income / self.total_assets) * 100
        return quarterly_roa * 4  # Annualize
    
    @computed_field
    @property
    def roe(self) -> float:
        """Return on Equity (ROE) - annualized."""
        if self.equity == 0:
            return 0.0
        quarterly_roe = (self.net_income / self.equity) * 100
        return quarterly_roe * 4  # Annualize


class DerivedMetrics(BaseModel):
    """Additional derived metrics from financial data."""
    
    gross_margin: float
    operating_margin: float
    net_margin: float
    debt_ratio: float
    equity_ratio: float
    current_ratio: Optional[float]
    roa: float
    roe: float
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None


class ManagementScore(BaseModel):
    """Management quality scoring model."""
    
    tenure_stability: float = Field(..., ge=0, le=100, description="CEO/CFO tenure score")
    board_independence: float = Field(..., ge=0, le=100, description="Board independence score")
    insider_alignment: float = Field(..., ge=0, le=100, description="Insider trading alignment score")
    governance_red_flags: float = Field(..., ge=0, le=100, description="Governance score (inverted red flags)")
    
    @computed_field
    @property
    def total(self) -> float:
        """Total management quality score (weighted average)."""
        return (
            0.25 * self.tenure_stability +
            0.25 * self.board_independence +
            0.25 * self.insider_alignment +
            0.25 * self.governance_red_flags
        )
    
    commentary: str = Field(default="", description="Qualitative commentary on management")
    details: dict = Field(default_factory=dict, description="Additional scoring details")


class EarningsQualityScore(BaseModel):
    """Earnings quality scoring model."""
    
    accrual_quality: float = Field(..., ge=0, le=100, description="Accrual ratio score")
    working_capital_behavior: float = Field(..., ge=0, le=100, description="Working capital anomaly score")
    one_off_dependency: float = Field(..., ge=0, le=100, description="Inverted one-off dependency")
    earnings_stability: float = Field(..., ge=0, le=100, description="Earnings volatility score")
    
    red_flags: List[str] = Field(default_factory=list, description="List of detected red flags")
    
    @computed_field
    @property
    def total(self) -> float:
        """Total earnings quality score (weighted average)."""
        return (
            0.25 * self.accrual_quality +
            0.25 * self.working_capital_behavior +
            0.25 * self.one_off_dependency +
            0.25 * self.earnings_stability
        )
    
    commentary: str = Field(default="", description="Qualitative commentary on earnings quality")
    details: dict = Field(default_factory=dict, description="Additional scoring details")


class ROICWACCAnalysis(BaseModel):
    """ROIC vs WACC value creation analysis."""
    
    nopat: float = Field(..., description="Net Operating Profit After Tax")
    invested_capital: float = Field(..., description="Total invested capital")
    roic: float = Field(..., description="Return on Invested Capital (%)")
    
    cost_of_equity: float = Field(..., description="Cost of equity (%)")
    cost_of_debt: float = Field(..., description="After-tax cost of debt (%)")
    wacc: float = Field(..., description="Weighted Average Cost of Capital (%)")
    
    @computed_field
    @property
    def value_creation_gap(self) -> float:
        """ROIC - WACC spread (percentage points)."""
        return self.roic - self.wacc
    
    @computed_field
    @property
    def is_value_creating(self) -> bool:
        """Whether the company is creating value (ROIC > WACC)."""
        return self.roic > self.wacc
    
    commentary: str = Field(default="", description="Commentary on value creation")
    assumptions: dict = Field(default_factory=dict, description="Key assumptions used")


class FactorExposures(BaseModel):
    """Factor exposure analysis (standardized z-scores)."""
    
    quality: float = Field(..., description="Quality factor exposure (z-score)")
    value: float = Field(..., description="Value factor exposure (z-score)")
    momentum: float = Field(..., description="Momentum factor exposure (z-score)")
    size: float = Field(..., description="Size factor exposure (z-score)")
    volatility: float = Field(..., description="Volatility factor exposure (z-score)")
    
    commentary: str = Field(default="", description="Commentary on factor positioning")
    details: dict = Field(default_factory=dict, description="Raw factor metrics")


class EarlyWarningSignal(BaseModel):
    """Individual early warning signal."""
    
    signal_name: str
    severity: str = Field(..., description="low, medium, high, critical")
    current_value: float
    threshold_value: float
    description: str


class EarlyWarningSystem(BaseModel):
    """Early warning system output."""
    
    warning_level: str = Field(..., description="none, low, medium, high, critical")
    triggered_signals: List[EarlyWarningSignal] = Field(default_factory=list)
    
    @computed_field
    @property
    def signal_count(self) -> int:
        """Number of triggered signals."""
        return len(self.triggered_signals)
    
    recommendation: str = Field(default="", description="Recommended actions")
    commentary: str = Field(default="", description="Overall risk commentary")


class CapitalAllocationAnalysis(BaseModel):
    """Capital allocation analysis."""
    
    period: str
    dividends: float = Field(default=0.0, description="Dividends paid")
    buybacks: float = Field(default=0.0, description="Share buybacks")
    capex: float = Field(default=0.0, description="Capital expenditures")
    rd_expense: float = Field(default=0.0, description="R&D expenses")
    debt_change: float = Field(default=0.0, description="Net change in debt")
    ma_spending: float = Field(default=0.0, description="M&A spending")
    
    @computed_field
    @property
    def total_shareholder_returns(self) -> float:
        """Dividends + Buybacks."""
        return self.dividends + self.buybacks
    
    @computed_field
    @property
    def total_investment(self) -> float:
        """Capex + R&D + M&A."""
        return self.capex + self.rd_expense + self.ma_spending
    
    commentary: str = Field(default="", description="Commentary on capital allocation")
    allocation_mix: dict = Field(default_factory=dict, description="Percentage breakdown")


class TrendMetric(BaseModel):
    """Single metric trend over time."""
    
    metric_name: str
    periods: List[str]
    values: List[float]
    
    @computed_field
    @property
    def trend_direction(self) -> str:
        """Overall trend direction: improving, declining, stable."""
        if len(self.values) < 2:
            return "insufficient_data"
        
        recent = self.values[-3:] if len(self.values) >= 3 else self.values
        if all(recent[i] > recent[i-1] for i in range(1, len(recent))):
            return "improving"
        elif all(recent[i] < recent[i-1] for i in range(1, len(recent))):
            return "declining"
        else:
            return "stable"
    
    @computed_field
    @property
    def latest_value(self) -> Optional[float]:
        """Most recent value."""
        return self.values[-1] if self.values else None
    
    @computed_field
    @property
    def yoy_change(self) -> Optional[float]:
        """Year-over-year change (if 4+ quarters available)."""
        if len(self.values) >= 4:
            current = self.values[-1]
            year_ago = self.values[-5] if len(self.values) >= 5 else self.values[-4]
            if year_ago != 0:
                return ((current - year_ago) / year_ago) * 100
        return None


class TrendAnalysis(BaseModel):
    """Multi-metric trend analysis."""
    
    stock_code: str
    company_name: str
    metrics: List[TrendMetric]
    summary: str = Field(default="", description="Overall trend summary")


class PeerComparison(BaseModel):
    """Peer comparison result."""
    
    metric_name: str
    companies: List[str]
    values: List[float]
    ranking: List[int]
    
    @computed_field
    @property
    def best_performer(self) -> str:
        """Company with best performance on this metric."""
        if not self.values:
            return "N/A"
        best_idx = self.values.index(max(self.values))
        return self.companies[best_idx]
    
    @computed_field
    @property
    def worst_performer(self) -> str:
        """Company with worst performance on this metric."""
        if not self.values:
            return "N/A"
        worst_idx = self.values.index(min(self.values))
        return self.companies[worst_idx]


class PeerAnalysis(BaseModel):
    """Complete peer analysis."""
    
    period: str
    comparisons: List[PeerComparison]
    summary: str = Field(default="", description="Overall peer positioning summary")
