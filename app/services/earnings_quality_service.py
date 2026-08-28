"""Earnings quality scoring service."""

from typing import List, Optional
from app.models import EarningsQualityScore
from app.core import (
    get_settings,
    calculate_volatility,
    DataLoader,
    required_context_values,
)
from app.data import CanonicalFinancialContext

MONEY_UNIT = "TWD_thousands"

EARNINGS_QUALITY_REQUIRED_FIELDS = [
    "net_income",
    "operating_income",
    "total_assets",
    "net_revenue",
    "accounts_receivable",
    "inventory",
]


class EarningsQualityService:
    """Service for calculating earnings quality scores."""

    def __init__(self, data_loader: DataLoader | None = None):
        self.settings = get_settings()
        self.data_loader = data_loader or DataLoader()

    def calculate_score(
        self, stock_code: str, period: str, periods_for_trend: Optional[List[str]] = None
    ) -> Optional[EarningsQualityScore]:
        """
        Calculate earnings quality score.

        Formula: E = 0.25*AQ + 0.25*WCB + 0.25*OD + 0.25*ES

        Args:
            stock_code: Stock ticker code
            period: Current period
            periods_for_trend: Historical periods for volatility analysis

        Returns:
            EarningsQualityScore object or None if insufficient data
        """
        # Load current filing context
        context = self.data_loader.load_context(stock_code, period)
        if not context or not context.has_analysis_data:
            return None
        required_context_values(
            context,
            EARNINGS_QUALITY_REQUIRED_FIELDS,
            MONEY_UNIT,
            "earnings quality analysis",
        )

        # Load historical contexts for trend analysis
        if periods_for_trend is None:
            periods_for_trend = self.data_loader.list_available_periods(stock_code)[
                -8:
            ]  # Last 8 quarters

        historical_contexts = self.data_loader.load_multiple_contexts(stock_code, periods_for_trend)
        historical_contexts = [
            historical for historical in historical_contexts if historical.period <= period
        ]

        red_flags = []

        # Component 1: Accrual Quality (AQ)
        accrual_score, accrual_flags = self._score_accrual_quality(context)
        red_flags.extend(accrual_flags)

        # Component 2: Working Capital Behavior (WCB)
        wc_score, wc_flags = self._score_working_capital(context, historical_contexts)
        red_flags.extend(wc_flags)

        # Component 3: One-off Dependency (OD) - inverted
        oneoff_score, oneoff_flags = self._score_one_off_dependency(context)
        red_flags.extend(oneoff_flags)

        # Component 4: Earnings Stability (ES)
        stability_score, stability_flags = self._score_earnings_stability(historical_contexts)
        red_flags.extend(stability_flags)

        # Component 5: blocking data-validation failures on required inputs
        red_flags.extend(self._validation_red_flags(context, EARNINGS_QUALITY_REQUIRED_FIELDS))

        # Generate commentary
        commentary = self._generate_commentary(
            accrual_score, wc_score, oneoff_score, stability_score, red_flags
        )

        earnings_series = [
            value
            for value in (
                context.optional_value("net_income", MONEY_UNIT) for context in historical_contexts
            )
            if value is not None
        ]

        details = {
            "accrual_ratio": self._calculate_accrual_ratio(context),
            "earnings_volatility": (
                calculate_volatility(earnings_series) if len(earnings_series) >= 4 else None
            ),
            "num_red_flags": len(red_flags),
        }

        return EarningsQualityScore(
            accrual_quality=round(accrual_score, 2),
            working_capital_behavior=round(wc_score, 2),
            one_off_dependency=round(oneoff_score, 2),
            earnings_stability=round(stability_score, 2),
            red_flags=red_flags,
            commentary=commentary,
            details=details,
        )

    def _calculate_accrual_ratio(self, context: CanonicalFinancialContext) -> float:
        """Calculate accrual ratio: (Net Income - Operating CF) / Total Assets."""
        total_assets = context.required_value("total_assets", MONEY_UNIT)
        operating_cash_flow = context.optional_value("operating_cash_flow", MONEY_UNIT)
        if not operating_cash_flow or total_assets == 0:
            return 0.0

        net_income = context.required_value("net_income", MONEY_UNIT)
        accruals = net_income - operating_cash_flow
        return accruals / total_assets

    def _score_accrual_quality(self, context: CanonicalFinancialContext) -> tuple:
        """Score accrual quality (0-100). Lower accruals = higher quality."""
        accrual_ratio = abs(self._calculate_accrual_ratio(context))
        flags: List[str] = []

        # High accruals = red flag
        threshold = self.settings.accrual_ratio_threshold

        if accrual_ratio >= threshold * 2:
            score = 20.0
            flags.append(f"Very high accruals ({accrual_ratio:.1%}) - earnings quality concern")
        elif accrual_ratio >= threshold:
            score = 50.0
            flags.append(f"Elevated accruals ({accrual_ratio:.1%})")
        elif accrual_ratio >= threshold * 0.5:
            score = 75.0
        else:
            score = 100.0

        return score, flags

    def _score_working_capital(
        self,
        current: CanonicalFinancialContext,
        historical: List[CanonicalFinancialContext],
    ) -> tuple:
        """Score working capital behavior (0-100)."""
        flags: List[str] = []

        if len(historical) < 2:
            return 50.0, flags  # Neutral if insufficient data

        # Find previous period
        previous = historical[-2] if len(historical) >= 2 else historical[-1]
        current_revenue = current.optional_value("net_revenue", MONEY_UNIT)
        current_ar = current.optional_value("accounts_receivable", MONEY_UNIT)
        current_inventory = current.optional_value("inventory", MONEY_UNIT)
        previous_revenue = previous.optional_value("net_revenue", MONEY_UNIT)
        previous_ar = previous.optional_value("accounts_receivable", MONEY_UNIT)
        previous_inventory = previous.optional_value("inventory", MONEY_UNIT)
        if (
            current_revenue is None
            or current_ar is None
            or current_inventory is None
            or previous_revenue is None
            or previous_ar is None
            or previous_inventory is None
        ):
            return 50.0, flags

        revenue_growth = (
            (current_revenue - previous_revenue) / previous_revenue if previous_revenue > 0 else 0
        )

        receivable_growth = (current_ar - previous_ar) / previous_ar if previous_ar > 0 else 0

        inventory_growth = (
            (current_inventory - previous_inventory) / previous_inventory
            if previous_inventory > 0
            else 0
        )

        threshold = self.settings.working_capital_spike_threshold
        score = 100.0

        # Receivables growing much faster than revenue = red flag
        if receivable_growth > revenue_growth + threshold:
            score -= 25
            flags.append(
                f"Receivables growing faster than revenue (AR: {receivable_growth:.1%} vs Rev: {revenue_growth:.1%})"
            )

        # Inventory growing much faster than revenue = red flag
        if inventory_growth > revenue_growth + threshold:
            score -= 25
            flags.append(
                f"Inventory growing faster than revenue (Inv: {inventory_growth:.1%} vs Rev: {revenue_growth:.1%})"
            )

        return max(0.0, score), flags

    def _score_one_off_dependency(self, context: CanonicalFinancialContext) -> tuple:
        """Score one-off income dependency (0-100). Higher one-offs = lower score."""
        flags: List[str] = []

        # Approximate one-off income as (Net Income - Operating Income)
        # This captures non-operating gains/losses
        net_income = context.required_value("net_income", MONEY_UNIT)
        operating_income = context.required_value("operating_income", MONEY_UNIT)
        if net_income == 0:
            return 50.0, flags

        non_operating = net_income - operating_income
        oneoff_ratio = abs(non_operating) / abs(net_income)

        threshold = self.settings.one_off_income_threshold

        if oneoff_ratio >= threshold * 2:
            score = 20.0
            flags.append(f"High non-operating income dependency ({oneoff_ratio:.1%})")
        elif oneoff_ratio >= threshold:
            score = 50.0
            flags.append(f"Moderate non-operating income ({oneoff_ratio:.1%})")
        elif oneoff_ratio >= threshold * 0.5:
            score = 75.0
        else:
            score = 100.0

        return score, flags

    def _score_earnings_stability(self, historical: List[CanonicalFinancialContext]) -> tuple:
        """Score earnings stability based on volatility (0-100)."""
        flags: List[str] = []

        if len(historical) < 4:
            return 50.0, flags  # Neutral if insufficient data

        earnings = [
            value
            for value in (
                context.optional_value("net_income", MONEY_UNIT) for context in historical
            )
            if value is not None
        ]
        if len(earnings) < 4:
            return 50.0, flags
        volatility = calculate_volatility(earnings)

        # Lower volatility = higher score
        if volatility <= 0.1:  # CV < 10%
            score = 100.0
        elif volatility <= 0.2:  # CV < 20%
            score = 80.0
        elif volatility <= 0.3:  # CV < 30%
            score = 60.0
        elif volatility <= 0.5:  # CV < 50%
            score = 40.0
            flags.append(f"High earnings volatility (CV: {volatility:.1%})")
        else:
            score = 20.0
            flags.append(f"Very high earnings volatility (CV: {volatility:.1%})")

        return score, flags

    def _validation_red_flags(
        self, context: CanonicalFinancialContext, fields: List[str]
    ) -> List[str]:
        """Surface blocking (error-severity) validation failures on required inputs."""
        failures = context.failed_validations(fields, severities=["error"])
        flags = []
        for failure in failures:
            if failure.message:
                flags.append(f"Validation failed: {failure.rule_name} - {failure.message}")
            else:
                flags.append(f"Validation failed: {failure.rule_name}")
        return flags

    def _generate_commentary(
        self, accrual: float, wc: float, oneoff: float, stability: float, red_flags: List[str]
    ) -> str:
        """Generate qualitative commentary."""
        total = (accrual + wc + oneoff + stability) / 4

        if total >= 80:
            quality = "High"
        elif total >= 60:
            quality = "Good"
        elif total >= 40:
            quality = "Fair"
        else:
            quality = "Poor"

        parts = [f"{quality} earnings quality (score: {total:.0f})"]

        if red_flags:
            parts.append(f"{len(red_flags)} concern(s) identified")
        else:
            parts.append("No major concerns")

        # Add specific insights
        if accrual < 50:
            parts.append("high accruals")
        if wc < 50:
            parts.append("working capital anomalies")
        if oneoff < 50:
            parts.append("one-off income dependency")
        if stability < 50:
            parts.append("volatile earnings")

        return ". ".join(parts) + "."
