"""Capital allocation analysis service."""

from typing import Optional
from app.models import CapitalAllocationAnalysis, FinancialSnapshot
from app.core import DataLoader


class CapitalAllocationService:
    """Service for analyzing capital allocation decisions."""
    
    def __init__(self):
        self.data_loader = DataLoader()
    
    def analyze(
        self,
        stock_code: str,
        period: str,
        # Actual capital allocation data (would come from cash flow statements)
        dividends: float = 0.0,
        buybacks: float = 0.0,
        capex: float = 0.0,
        rd_expense: float = 0.0,
        ma_spending: float = 0.0,
    ) -> Optional[CapitalAllocationAnalysis]:
        """
        Analyze capital allocation strategy.
        
        Args:
            stock_code: Stock ticker code
            period: Period identifier
            dividends: Dividends paid
            buybacks: Share buybacks
            capex: Capital expenditures
            rd_expense: R&D expenses
            ma_spending: M&A spending
        
        Returns:
            CapitalAllocationAnalysis object or None
        """
        snapshot = self.data_loader.load_snapshot(stock_code, period)
        if not snapshot:
            return None
        
        # Calculate debt change (simplified)
        # In real implementation, would compare with previous period
        debt_change = 0.0  # Placeholder
        
        # Calculate allocation mix percentages
        total_allocation = dividends + buybacks + capex + rd_expense + ma_spending + abs(debt_change)
        
        if total_allocation > 0:
            allocation_mix = {
                "dividends": round((dividends / total_allocation) * 100, 1),
                "buybacks": round((buybacks / total_allocation) * 100, 1),
                "capex": round((capex / total_allocation) * 100, 1),
                "rd": round((rd_expense / total_allocation) * 100, 1),
                "ma": round((ma_spending / total_allocation) * 100, 1),
                "debt_change": round((abs(debt_change) / total_allocation) * 100, 1),
            }
        else:
            allocation_mix = {}
        
        # Generate commentary
        commentary = self._generate_commentary(
            dividends, buybacks, capex, rd_expense, ma_spending, 
            debt_change, snapshot, allocation_mix
        )
        
        return CapitalAllocationAnalysis(
            period=period,
            dividends=round(dividends, 2),
            buybacks=round(buybacks, 2),
            capex=round(capex, 2),
            rd_expense=round(rd_expense, 2),
            debt_change=round(debt_change, 2),
            ma_spending=round(ma_spending, 2),
            commentary=commentary,
            allocation_mix=allocation_mix
        )
    
    def _generate_commentary(
        self,
        dividends: float,
        buybacks: float,
        capex: float,
        rd: float,
        ma: float,
        debt_change: float,
        snapshot: FinancialSnapshot,
        mix: dict
    ) -> str:
        """Generate commentary on capital allocation strategy."""
        parts = []
        
        # Calculate key ratios
        total_shareholder_returns = dividends + buybacks
        total_investment = capex + rd + ma
        
        # Shareholder returns focus
        if mix and mix.get("dividends", 0) + mix.get("buybacks", 0) > 50:
            parts.append("Shareholder-focused allocation (dividends + buybacks > 50%)")
        
        # Growth investment focus
        if mix and mix.get("capex", 0) + mix.get("rd", 0) > 50:
            parts.append("Growth-focused allocation (capex + R&D > 50%)")
        
        # Balanced approach
        if mix:
            shareholder_pct = mix.get("dividends", 0) + mix.get("buybacks", 0)
            investment_pct = mix.get("capex", 0) + mix.get("rd", 0)
            if 30 <= shareholder_pct <= 60 and 30 <= investment_pct <= 60:
                parts.append("Balanced allocation between returns and reinvestment")
        
        # Dividend policy
        if dividends > buybacks * 2:
            parts.append("Prefers dividends over buybacks")
        elif buybacks > dividends * 2:
            parts.append("Prefers buybacks over dividends")
        
        # M&A activity
        if mix and mix.get("ma", 0) > 20:
            parts.append(f"Significant M&A activity ({mix.get('ma', 0):.0f}%)")
        
        # Debt management
        if debt_change > 0:
            parts.append("Taking on additional debt")
        elif debt_change < 0:
            parts.append("Reducing debt levels")
        
        # Overall assessment
        if total_investment > total_shareholder_returns:
            parts.append("Prioritizing growth over immediate shareholder returns")
        elif total_shareholder_returns > total_investment * 2:
            parts.append("Prioritizing shareholder returns over reinvestment")
        
        if not parts:
            return "Capital allocation data not available or minimal activity"
        
        return ". ".join(parts) + "."
