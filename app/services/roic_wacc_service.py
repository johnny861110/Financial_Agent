"""ROIC vs WACC value creation analysis service."""

from typing import Optional
from app.models import ROICWACCAnalysis
from app.core import DataLoader, get_settings, required_context_values, safe_divide
from app.data import CanonicalFinancialContext

MONEY_UNIT = "TWD_thousands"

ROIC_WACC_REQUIRED_FIELDS = [
    "operating_income",
    "equity",
    "total_liabilities",
]


class ROICWACCService:
    """Service for ROIC vs WACC analysis."""

    def __init__(self, data_loader: DataLoader | None = None):
        self.data_loader = data_loader or DataLoader()
        self.settings = get_settings()

    def analyze(
        self,
        stock_code: str,
        period: str,
        market_beta: Optional[float] = None,
        cost_of_debt: Optional[float] = None,
        tax_rate: Optional[float] = None,
    ) -> Optional[ROICWACCAnalysis]:
        """
        Calculate ROIC vs WACC to assess value creation.

        Args:
            stock_code: Stock ticker code
            period: Period identifier
            market_beta: Market beta (defaults to 1.0)
            cost_of_debt: Pre-tax cost of debt (defaults to estimated)
            tax_rate: Corporate tax rate (defaults to 20%)

        Returns:
            ROICWACCAnalysis object or None
        """
        context = self.data_loader.load_context(stock_code, period)
        if not context or not context.has_analysis_data:
            return None
        required_context_values(
            context,
            ROIC_WACC_REQUIRED_FIELDS,
            MONEY_UNIT,
            "ROIC/WACC analysis",
        )

        # Use defaults if not provided
        if market_beta is None:
            market_beta = self.settings.default_beta
        if tax_rate is None:
            tax_rate = self.settings.default_tax_rate

        # Calculate ROIC components
        nopat = self._calculate_nopat(context, tax_rate)
        invested_capital = self._calculate_invested_capital(context)
        roic = safe_divide(nopat, invested_capital) * 100  # as percentage

        # Calculate WACC components
        cost_of_equity = self._calculate_cost_of_equity(market_beta)

        if cost_of_debt is None:
            cost_of_debt = self._estimate_cost_of_debt(context)

        after_tax_cost_of_debt = cost_of_debt * (1 - tax_rate)

        # Calculate WACC
        equity = context.required_value("equity", MONEY_UNIT)
        total_liabilities = context.required_value("total_liabilities", MONEY_UNIT)
        total_capital = equity + total_liabilities
        equity_weight = safe_divide(equity, total_capital)
        debt_weight = safe_divide(total_liabilities, total_capital)

        wacc = (equity_weight * cost_of_equity + debt_weight * after_tax_cost_of_debt) * 100

        # Generate commentary
        commentary = self._generate_commentary(roic, wacc, context)
        validation_notes = self._validation_notes(context, ROIC_WACC_REQUIRED_FIELDS)
        if validation_notes:
            commentary = commentary + " " + " ".join(validation_notes)

        assumptions = {
            "beta": market_beta,
            "risk_free_rate": self.settings.default_risk_free_rate * 100,
            "market_risk_premium": self.settings.default_market_risk_premium * 100,
            "tax_rate": tax_rate * 100,
            "cost_of_debt_pretax": cost_of_debt * 100,
            "equity_weight": equity_weight * 100,
            "debt_weight": debt_weight * 100,
        }

        return ROICWACCAnalysis(
            nopat=round(nopat, 2),
            invested_capital=round(invested_capital, 2),
            roic=round(roic, 2),
            cost_of_equity=round(cost_of_equity * 100, 2),
            cost_of_debt=round(after_tax_cost_of_debt * 100, 2),
            wacc=round(wacc, 2),
            commentary=commentary,
            assumptions=assumptions,
        )

    def _calculate_nopat(self, context: CanonicalFinancialContext, tax_rate: float) -> float:
        """Calculate Net Operating Profit After Tax."""
        operating_income = context.required_value("operating_income", MONEY_UNIT)
        return operating_income * (1 - tax_rate)

    def _calculate_invested_capital(self, context: CanonicalFinancialContext) -> float:
        """
        Calculate invested capital.
        Approximation: Total Assets - Non-interest-bearing current liabilities
        Simplified: Equity + Total Debt
        """
        # Simplified approach
        equity = context.required_value("equity", MONEY_UNIT)
        total_liabilities = context.required_value("total_liabilities", MONEY_UNIT)
        return equity + total_liabilities

    def _calculate_cost_of_equity(self, beta: float) -> float:
        """
        Calculate cost of equity using CAPM.
        Cost of Equity = Risk-free Rate + Beta * Market Risk Premium
        """
        rf = self.settings.default_risk_free_rate
        mrp = self.settings.default_market_risk_premium
        return float(rf + beta * mrp)

    def _estimate_cost_of_debt(self, context: CanonicalFinancialContext) -> float:
        """
        Estimate pre-tax cost of debt.
        Simple heuristic based on debt ratio.
        """
        base_rate = 0.03  # 3%

        # total_assets is not a required field for this analysis (only needed
        # for this optional heuristic default); if it is unavailable, fall
        # back to the base rate alone rather than guessing a leverage spread.
        debt_ratio_percent = context.ratio_percent(
            "debt_ratio", "total_liabilities", "total_assets"
        )
        if debt_ratio_percent is None:
            return base_rate

        debt_ratio = debt_ratio_percent / 100
        leverage_spread = debt_ratio * 0.05  # Up to 5% additional

        return base_rate + leverage_spread

    def _generate_commentary(
        self, roic: float, wacc: float, context: CanonicalFinancialContext
    ) -> str:
        """Generate commentary on value creation."""
        spread = roic - wacc

        parts = []

        # Value creation assessment
        if spread > 5:
            parts.append(
                f"Strong value creation: ROIC ({roic:.1f}%) significantly exceeds WACC ({wacc:.1f}%)"
            )
        elif spread > 2:
            parts.append(f"Positive value creation: ROIC ({roic:.1f}%) above WACC ({wacc:.1f}%)")
        elif spread > 0:
            parts.append(
                f"Marginal value creation: ROIC ({roic:.1f}%) slightly above WACC ({wacc:.1f}%)"
            )
        elif spread > -2:
            parts.append(f"Value neutral: ROIC ({roic:.1f}%) near WACC ({wacc:.1f}%)")
        else:
            parts.append(f"Value destruction: ROIC ({roic:.1f}%) below WACC ({wacc:.1f}%)")

        # Capital efficiency
        if roic >= 15:
            parts.append("Highly efficient capital allocation")
        elif roic >= 10:
            parts.append("Good capital efficiency")
        elif roic >= 5:
            parts.append("Moderate capital efficiency")
        else:
            parts.append("Poor capital efficiency")

        # Leverage commentary (only when total_assets is actually available;
        # do not fabricate a 0% debt ratio when the input is unavailable)
        debt_ratio = context.ratio_percent("debt_ratio", "total_liabilities", "total_assets")
        if debt_ratio is not None:
            if debt_ratio > 60:
                parts.append(f"High leverage ({debt_ratio:.0f}%) increases WACC")
            elif debt_ratio < 30:
                parts.append(f"Conservative capital structure ({debt_ratio:.0f}%)")

        return ". ".join(parts) + "."

    def _validation_notes(self, context: CanonicalFinancialContext, fields: list[str]) -> list[str]:
        """Surface blocking (error-severity) validation failures on required inputs."""
        notes = []
        for failure in context.failed_validations(fields, severities=["error"]):
            if failure.message:
                notes.append(f"Validation failed: {failure.rule_name} - {failure.message}.")
            else:
                notes.append(f"Validation failed: {failure.rule_name}.")
        return notes
