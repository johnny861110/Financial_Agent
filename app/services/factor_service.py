"""Factor exposure analysis service."""

import math
import statistics
from typing import List, Optional
from app.models import FactorExposures
from app.core import (
    DataLoader,
    InsufficientDataError,
    calculate_z_score,
    required_context_values,
    safe_divide,
)
from app.data import CanonicalFinancialContext, UnitMismatchError

MONEY_UNIT = "TWD_thousands"
EPS_UNIT = "TWD_per_share"

FACTOR_MONEY_FIELDS = [
    "equity",
    "total_liabilities",
    "total_assets",
    "net_income",
    "net_revenue",
    "operating_income",
]


class FactorService:
    """Service for calculating factor exposures."""

    def __init__(self, data_loader: DataLoader | None = None):
        self.data_loader = data_loader or DataLoader()

    def calculate_exposures(
        self, stock_code: str, period: str, peer_stocks: Optional[List[str]] = None
    ) -> Optional[FactorExposures]:
        """
        Calculate factor exposures (standardized z-scores vs peers).

        Args:
            stock_code: Target stock code
            period: Period identifier
            peer_stocks: List of peer stock codes for comparison

        Returns:
            FactorExposures object or None
        """
        # Load target context
        target = self.data_loader.load_context(stock_code, period)
        if not target or not target.has_analysis_data:
            return None
        required_context_values(target, FACTOR_MONEY_FIELDS, MONEY_UNIT, "factor exposure analysis")
        required_context_values(target, ["eps_basic"], EPS_UNIT, "factor exposure analysis")

        # Load peer contexts
        if peer_stocks is None or len(peer_stocks) < 3:
            # If no peers specified, use all available stocks as universe
            all_stocks = self.data_loader.list_all_stocks()
            peer_stocks = [s for s in all_stocks if s != stock_code][:20]  # Use up to 20 peers

        peers: List[CanonicalFinancialContext] = []
        for peer_code in peer_stocks:
            peer_context = self.data_loader.load_context(peer_code, period)
            if not peer_context or not peer_context.has_analysis_data:
                continue
            try:
                required_context_values(
                    peer_context, FACTOR_MONEY_FIELDS, MONEY_UNIT, "factor exposure analysis"
                )
                required_context_values(
                    peer_context, ["eps_basic"], EPS_UNIT, "factor exposure analysis"
                )
            except (InsufficientDataError, UnitMismatchError):
                continue
            peers.append(peer_context)

        if len(peers) < 3:
            # Need minimum peers for meaningful z-scores
            return None

        # Calculate factor z-scores
        quality_z = self._calculate_quality_factor(target, peers)
        value_z = self._calculate_value_factor(target, peers)
        momentum_z = self._calculate_momentum_factor(target, peers)
        size_z = self._calculate_size_factor(target, peers)
        volatility_z = self._calculate_volatility_factor(target, peers)

        # Generate commentary
        commentary = self._generate_commentary(quality_z, value_z, momentum_z, size_z, volatility_z)

        details = {
            "peer_count": len(peers),
            "target_roe": round(self._roe(target), 2),
            "target_total_assets": target.required_value("total_assets", MONEY_UNIT),
        }

        return FactorExposures(
            quality=round(quality_z, 2),
            value=round(value_z, 2),
            momentum=round(momentum_z, 2),
            size=round(size_z, 2),
            volatility=round(volatility_z, 2),
            commentary=commentary,
            details=details,
        )

    def _operating_margin(self, context: CanonicalFinancialContext) -> float:
        revenue = context.required_value("net_revenue", MONEY_UNIT)
        operating_income = context.required_value("operating_income", MONEY_UNIT)
        return safe_divide(operating_income, revenue) * 100

    def _net_margin(self, context: CanonicalFinancialContext) -> float:
        revenue = context.required_value("net_revenue", MONEY_UNIT)
        net_income = context.required_value("net_income", MONEY_UNIT)
        return safe_divide(net_income, revenue) * 100

    def _roe(self, context: CanonicalFinancialContext) -> float:
        equity = context.required_value("equity", MONEY_UNIT)
        net_income = context.required_value("net_income", MONEY_UNIT)
        return safe_divide(net_income, equity) * 100 * 4  # annualized

    def _debt_ratio(self, context: CanonicalFinancialContext) -> float:
        total_assets = context.required_value("total_assets", MONEY_UNIT)
        total_liabilities = context.required_value("total_liabilities", MONEY_UNIT)
        return safe_divide(total_liabilities, total_assets) * 100

    def _calculate_quality_factor(
        self, target: CanonicalFinancialContext, peers: List[CanonicalFinancialContext]
    ) -> float:
        """
        Quality factor: ROE, margins, low debt.
        Composite of ROE + Operating Margin - Debt Ratio
        """

        def quality_score(context: CanonicalFinancialContext) -> float:
            return (
                self._roe(context)
                + self._operating_margin(context)
                - (self._debt_ratio(context) / 2)
            )

        target_score = quality_score(target)
        peer_scores = [quality_score(p) for p in peers]

        mean_score = statistics.mean(peer_scores)
        std_score = statistics.stdev(peer_scores) if len(peer_scores) > 1 else 1.0

        return calculate_z_score(target_score, mean_score, std_score)

    def _calculate_value_factor(
        self, target: CanonicalFinancialContext, peers: List[CanonicalFinancialContext]
    ) -> float:
        """
        Value factor: inverse of P/E proxy.
        Use EPS as proxy (higher EPS relative to peers = more value)
        """
        target_eps = target.required_value("eps_basic", EPS_UNIT)
        peer_eps = [p.required_value("eps_basic", EPS_UNIT) for p in peers]

        mean_eps = statistics.mean(peer_eps)
        std_eps = statistics.stdev(peer_eps) if len(peer_eps) > 1 else 1.0

        return calculate_z_score(target_eps, mean_eps, std_eps)

    def _calculate_momentum_factor(
        self, target: CanonicalFinancialContext, peers: List[CanonicalFinancialContext]
    ) -> float:
        """
        Momentum factor: revenue growth proxy.
        We'll use net margin as a proxy (higher margin suggests positive momentum)
        In real implementation, would use historical price or revenue growth
        """
        target_margin = self._net_margin(target)
        peer_margins = [self._net_margin(p) for p in peers]

        mean_margin = statistics.mean(peer_margins)
        std_margin = statistics.stdev(peer_margins) if len(peer_margins) > 1 else 1.0

        return calculate_z_score(target_margin, mean_margin, std_margin)

    def _calculate_size_factor(
        self, target: CanonicalFinancialContext, peers: List[CanonicalFinancialContext]
    ) -> float:
        """
        Size factor: total assets (negative z-score = small cap premium).
        """
        target_assets = target.required_value("total_assets", MONEY_UNIT)
        target_size = math.log(target_assets) if target_assets > 0 else 0
        peer_sizes = []
        for peer in peers:
            peer_assets = peer.required_value("total_assets", MONEY_UNIT)
            peer_sizes.append(math.log(peer_assets) if peer_assets > 0 else 0)

        mean_size = statistics.mean(peer_sizes)
        std_size = statistics.stdev(peer_sizes) if len(peer_sizes) > 1 else 1.0

        return calculate_z_score(target_size, mean_size, std_size)

    def _calculate_volatility_factor(
        self, target: CanonicalFinancialContext, peers: List[CanonicalFinancialContext]
    ) -> float:
        """
        Volatility factor: debt ratio as proxy for volatility risk.
        Higher debt = higher volatility
        """
        target_debt = self._debt_ratio(target)
        peer_debts = [self._debt_ratio(p) for p in peers]

        mean_debt = statistics.mean(peer_debts)
        std_debt = statistics.stdev(peer_debts) if len(peer_debts) > 1 else 1.0

        # Invert: higher debt = higher volatility = positive z-score
        return calculate_z_score(target_debt, mean_debt, std_debt)

    def _generate_commentary(
        self, quality: float, value: float, momentum: float, size: float, volatility: float
    ) -> str:
        """Generate commentary on factor positioning."""
        parts = []

        # Quality
        if quality > 1.5:
            parts.append("Strong quality profile")
        elif quality > 0.5:
            parts.append("Above-average quality")
        elif quality < -1.5:
            parts.append("Weak quality profile")
        elif quality < -0.5:
            parts.append("Below-average quality")

        # Value
        if value > 1.0:
            parts.append("attractive valuation")
        elif value < -1.0:
            parts.append("expensive valuation")

        # Momentum
        if momentum > 1.0:
            parts.append("strong momentum")
        elif momentum < -1.0:
            parts.append("weak momentum")

        # Size
        if size > 1.5:
            parts.append("large cap")
        elif size < -1.5:
            parts.append("small cap")
        else:
            parts.append("mid cap")

        # Volatility
        if volatility > 1.0:
            parts.append("higher volatility/risk")
        elif volatility < -1.0:
            parts.append("lower volatility/risk")

        if not parts:
            return "Neutral factor profile across dimensions"

        return ". ".join(p.capitalize() for p in parts) + "."
