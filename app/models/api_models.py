"""Public response contracts for the deterministic financial API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.data.models import SnapshotRecord


class UnitsMetadata(BaseModel):
    """Units for values in an API response."""

    monetary: str = "TWD_thousands"
    percentages: str = "percent"
    ratios: str = "ratio"
    per_share: str = "TWD_per_share"
    scores: str = "points_0_100"
    factors: str = "z_score"


class SnapshotIdentification(BaseModel):
    stock_code: str
    company_name: str
    period: str
    currency: str
    unit: str


class SnapshotIncomeStatement(BaseModel):
    net_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    profit_before_tax: float | None = None
    net_income: float | None = None
    net_income_attributable_to_parent: float | None = None
    operating_expenses: float | None = None
    rd_expenses: float | None = None
    tax_expense: float | None = None
    comprehensive_income: float | None = None
    net_interest_income: float | None = None
    net_non_interest_income: float | None = None
    loan_loss_provisions: float | None = None
    eps: float | None = None
    eps_diluted: float | None = None


class SnapshotMargins(BaseModel):
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None


class SnapshotBalanceSheet(BaseModel):
    cash_and_equivalents: float | None = None
    accounts_receivable: float | None = None
    inventory: float | None = None
    current_assets: float | None = None
    total_assets: float | None = None
    accounts_payable: float | None = None
    current_liabilities: float | None = None
    total_liabilities: float | None = None
    equity: float | None = None
    equity_attributable_to_parent: float | None = None
    retained_earnings: float | None = None
    share_capital: float | None = None


class SnapshotCashFlow(BaseModel):
    operating_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None
    capex: float | None = None
    free_cash_flow: float | None = None
    cash_beginning: float | None = None
    cash_ending: float | None = None


class SnapshotFinancialStructure(BaseModel):
    debt_ratio: float | None = None
    equity_ratio: float | None = None
    current_ratio: float | None = None


class SnapshotReturns(BaseModel):
    roa: float | None = None
    roe: float | None = None


class SnapshotDataContext(BaseModel):
    schema_version: str
    status: str
    quality_score: float | None = None
    is_stale: bool
    field_states: dict[str, str]
    failed_validations: list[dict[str, Any]] = Field(default_factory=list)


class FinancialSnapshotResponse(BaseModel):
    identification: SnapshotIdentification
    income_statement: SnapshotIncomeStatement
    margins: SnapshotMargins
    balance_sheet: SnapshotBalanceSheet
    cash_flow: SnapshotCashFlow = Field(default_factory=SnapshotCashFlow)
    financial_structure: SnapshotFinancialStructure
    returns: SnapshotReturns
    data_context: SnapshotDataContext
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class TrendMetricResponse(BaseModel):
    metric_name: str
    periods: list[str]
    values: list[float]
    trend_direction: str
    latest_value: float | None = None
    yoy_change: float | None = None


class TrendResponse(BaseModel):
    stock_code: str
    company_name: str
    metrics: list[TrendMetricResponse]
    summary: str
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class PeerComparisonResponse(BaseModel):
    metric_name: str
    companies: list[str]
    values: list[float]
    ranking: list[int]
    best_performer: str
    worst_performer: str


class PeerResponse(BaseModel):
    period: str
    comparisons: list[PeerComparisonResponse]
    summary: str
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class ManagementComponents(BaseModel):
    tenure_stability: float
    board_independence: float
    insider_alignment: float
    governance_red_flags: float


class ManagementResponse(BaseModel):
    total_score: float
    components: ManagementComponents
    commentary: str
    details: dict[str, Any] = Field(default_factory=dict)
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class EarningsComponents(BaseModel):
    accrual_quality: float
    working_capital_behavior: float
    one_off_dependency: float
    earnings_stability: float


class EarningsQualityResponse(BaseModel):
    total_score: float
    components: EarningsComponents
    red_flags: list[str]
    commentary: str
    details: dict[str, Any] = Field(default_factory=dict)
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class ROICWACCResponse(BaseModel):
    nopat: float
    invested_capital: float
    roic: float
    cost_of_equity: float
    cost_of_debt: float
    wacc: float
    value_creation_gap: float
    is_value_creating: bool
    commentary: str
    assumptions: dict[str, Any] = Field(default_factory=dict)
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class FactorResponse(BaseModel):
    quality: float
    value: float
    momentum: float
    size: float
    volatility: float
    commentary: str
    details: dict[str, Any] = Field(default_factory=dict)
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class CapitalAllocationResponse(BaseModel):
    period: str
    dividends: float
    buybacks: float
    capex: float
    rd_expense: float
    ma_spending: float
    debt_change: float
    total_shareholder_returns: float
    total_investment: float
    allocation_mix: dict[str, float] = Field(default_factory=dict)
    commentary: str
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class EarlyWarningSignalResponse(BaseModel):
    signal_name: str
    severity: str
    current_value: float
    threshold_value: float
    description: str


class EarlyWarningResponse(BaseModel):
    warning_level: str
    signal_count: int
    triggered_signals: list[EarlyWarningSignalResponse]
    recommendation: str
    commentary: str
    units: UnitsMetadata = Field(default_factory=UnitsMetadata)


class DataCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str | None = None
    api_version: str | None = None
    source: str | None = None
    operations: list[str] = Field(default_factory=list)


class StockDiscoveryResponse(BaseModel):
    stocks: list[str]


class PeriodDiscoveryResponse(BaseModel):
    stock_code: str
    periods: list[str]


class ProviderOperationResponse(BaseModel):
    """Known job/refresh fields while retaining provider-specific additions."""

    model_config = ConfigDict(extra="allow")

    status: str | None = None
    job_id: str | None = None
    message: str | None = None


class DataRecordResponse(SnapshotRecord):
    """Named contract for the source record endpoint."""
