"""Early Warning System service for risk detection."""

from typing import List, Optional
from app.models import EarlyWarningSystem, EarlyWarningSignal, FinancialSnapshot
from app.core import DataLoader, get_settings, calculate_growth_rate


class EarlyWarningService:
    """Service for detecting financial red flags and risks."""
    
    def __init__(self):
        self.data_loader = DataLoader()
        self.settings = get_settings()
    
    def detect_warnings(
        self,
        stock_code: str,
        period: str,
        historical_periods: Optional[List[str]] = None
    ) -> Optional[EarlyWarningSystem]:
        """
        Detect early warning signals in financial data.
        
        Args:
            stock_code: Stock ticker code
            period: Current period
            historical_periods: Historical periods for trend comparison
        
        Returns:
            EarlyWarningSystem object or None
        """
        # Load current snapshot
        current = self.data_loader.load_snapshot(stock_code, period)
        if not current:
            return None
        
        # Load historical data
        if historical_periods is None:
            all_periods = self.data_loader.list_available_periods(stock_code)
            historical_periods = all_periods[-5:] if len(all_periods) >= 2 else []
        
        historical = self.data_loader.load_multiple_periods(stock_code, historical_periods)
        
        signals = []
        
        # Run all detection rules
        signals.extend(self._check_receivables_spike(current, historical))
        signals.extend(self._check_inventory_spike(current, historical))
        signals.extend(self._check_margin_compression(current, historical))
        signals.extend(self._check_leverage_deterioration(current))
        signals.extend(self._check_cash_burn(current, historical))
        signals.extend(self._check_negative_cash_flow(current))
        
        # Determine overall warning level
        warning_level = self._determine_warning_level(signals)
        
        # Generate recommendations
        recommendation = self._generate_recommendations(signals, warning_level)
        
        # Generate commentary
        commentary = self._generate_commentary(signals, warning_level)
        
        return EarlyWarningSystem(
            warning_level=warning_level,
            triggered_signals=signals,
            recommendation=recommendation,
            commentary=commentary
        )
    
    def _check_receivables_spike(
        self, 
        current: FinancialSnapshot, 
        historical: List[FinancialSnapshot]
    ) -> List[EarlyWarningSignal]:
        """Check if accounts receivable growing faster than revenue."""
        signals = []
        
        if len(historical) < 1:
            return signals
        
        previous = historical[-1]
        
        revenue_growth = calculate_growth_rate(current.net_revenue, previous.net_revenue)
        receivable_growth = calculate_growth_rate(current.accounts_receivable, previous.accounts_receivable)
        
        threshold = self.settings.ews_receivable_spike_threshold * 100
        
        if receivable_growth > revenue_growth + threshold:
            signals.append(EarlyWarningSignal(
                signal_name="Accounts Receivable Spike",
                severity="medium",
                current_value=receivable_growth,
                threshold_value=revenue_growth + threshold,
                description=f"AR growing at {receivable_growth:.1f}% vs revenue {revenue_growth:.1f}%. May indicate revenue recognition issues or collection problems."
            ))
        
        return signals
    
    def _check_inventory_spike(
        self,
        current: FinancialSnapshot,
        historical: List[FinancialSnapshot]
    ) -> List[EarlyWarningSignal]:
        """Check if inventory growing faster than revenue."""
        signals = []
        
        if len(historical) < 1:
            return signals
        
        previous = historical[-1]
        
        revenue_growth = calculate_growth_rate(current.net_revenue, previous.net_revenue)
        inventory_growth = calculate_growth_rate(current.inventory, previous.inventory)
        
        threshold = self.settings.ews_inventory_spike_threshold * 100
        
        if inventory_growth > revenue_growth + threshold:
            signals.append(EarlyWarningSignal(
                signal_name="Inventory Buildup",
                severity="medium",
                current_value=inventory_growth,
                threshold_value=revenue_growth + threshold,
                description=f"Inventory growing at {inventory_growth:.1f}% vs revenue {revenue_growth:.1f}%. May indicate slowing demand or obsolescence risk."
            ))
        
        return signals
    
    def _check_margin_compression(
        self,
        current: FinancialSnapshot,
        historical: List[FinancialSnapshot]
    ) -> List[EarlyWarningSignal]:
        """Check for significant margin deterioration."""
        signals = []
        
        if len(historical) < 2:
            return signals
        
        # Compare with average of last 2-3 periods
        avg_margin = sum(s.operating_margin for s in historical[-3:]) / min(3, len(historical))
        margin_change = current.operating_margin - avg_margin
        
        threshold = self.settings.ews_margin_compression_threshold * 100
        
        if margin_change < threshold:
            severity = "high" if margin_change < threshold * 2 else "medium"
            signals.append(EarlyWarningSignal(
                signal_name="Margin Compression",
                severity=severity,
                current_value=current.operating_margin,
                threshold_value=avg_margin + threshold,
                description=f"Operating margin declined to {current.operating_margin:.1f}% from avg {avg_margin:.1f}%. Indicates pricing pressure or cost inflation."
            ))
        
        return signals
    
    def _check_leverage_deterioration(self, current: FinancialSnapshot) -> List[EarlyWarningSignal]:
        """Check for excessive leverage."""
        signals = []
        
        debt_ratio = current.debt_ratio / 100
        threshold = self.settings.ews_debt_ratio_critical
        
        if debt_ratio >= threshold:
            severity = "critical" if debt_ratio >= 0.8 else "high"
            signals.append(EarlyWarningSignal(
                signal_name="High Leverage",
                severity=severity,
                current_value=debt_ratio * 100,
                threshold_value=threshold * 100,
                description=f"Debt ratio at {debt_ratio*100:.1f}% exceeds safe threshold. Financial distress risk."
            ))
        
        return signals
    
    def _check_cash_burn(
        self,
        current: FinancialSnapshot,
        historical: List[FinancialSnapshot]
    ) -> List[EarlyWarningSignal]:
        """Check for cash depletion."""
        signals = []
        
        if len(historical) < 2:
            return signals
        
        # Check if cash declining significantly
        avg_cash = sum(s.cash_and_equivalents for s in historical[-3:]) / min(3, len(historical))
        cash_decline_pct = ((current.cash_and_equivalents - avg_cash) / avg_cash) * 100 if avg_cash > 0 else 0
        
        if cash_decline_pct < -30:  # 30% decline
            severity = "high" if cash_decline_pct < -50 else "medium"
            signals.append(EarlyWarningSignal(
                signal_name="Cash Depletion",
                severity=severity,
                current_value=cash_decline_pct,
                threshold_value=-30.0,
                description=f"Cash declined {abs(cash_decline_pct):.1f}%. Liquidity concern."
            ))
        
        return signals
    
    def _check_negative_cash_flow(self, current: FinancialSnapshot) -> List[EarlyWarningSignal]:
        """Check for negative operating cash flow."""
        signals = []
        
        if current.operating_cash_flow and current.operating_cash_flow < 0:
            signals.append(EarlyWarningSignal(
                signal_name="Negative Operating Cash Flow",
                severity="high",
                current_value=current.operating_cash_flow,
                threshold_value=0.0,
                description="Negative operating cash flow. Company burning cash from operations."
            ))
        
        return signals
    
    def _determine_warning_level(self, signals: List[EarlyWarningSignal]) -> str:
        """Determine overall warning level based on triggered signals."""
        if not signals:
            return "none"
        
        # Count by severity
        critical_count = sum(1 for s in signals if s.severity == "critical")
        high_count = sum(1 for s in signals if s.severity == "high")
        medium_count = sum(1 for s in signals if s.severity == "medium")
        
        if critical_count > 0:
            return "critical"
        elif high_count >= 2:
            return "high"
        elif high_count >= 1:
            return "high"
        elif medium_count >= 3:
            return "medium"
        elif medium_count >= 1:
            return "low"
        else:
            return "low"
    
    def _generate_recommendations(self, signals: List[EarlyWarningSignal], level: str) -> str:
        """Generate recommended actions based on warning level."""
        if level == "critical":
            return "URGENT: Immediate review required. Consider reducing position or exiting. High risk of financial distress."
        elif level == "high":
            return "Closely monitor position. Conduct deep-dive analysis. Consider reducing exposure."
        elif level == "medium":
            return "Watch list. Monitor next quarter results. Prepare contingency plans."
        elif level == "low":
            return "Minor concerns identified. Continue regular monitoring."
        else:
            return "No significant concerns. Maintain current monitoring cadence."
    
    def _generate_commentary(self, signals: List[EarlyWarningSignal], level: str) -> str:
        """Generate overall commentary."""
        if not signals:
            return "No early warning signals detected. Financial health appears stable."
        
        signal_names = [s.signal_name for s in signals]
        
        return f"Warning level: {level.upper()}. Detected {len(signals)} signal(s): {', '.join(signal_names)}. Recommend detailed investigation."
