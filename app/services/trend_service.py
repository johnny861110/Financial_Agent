"""Trend analysis service for multi-period analysis."""

from typing import List, Optional
from app.models import FinancialSnapshot, TrendMetric, TrendAnalysis
from app.core import DataLoader


class TrendService:
    """Service for analyzing trends across multiple periods."""
    
    def __init__(self):
        self.data_loader = DataLoader()
    
    def analyze_trend(self, stock_code: str, periods: Optional[List[str]] = None) -> Optional[TrendAnalysis]:
        """
        Analyze trends for a stock across multiple periods.
        
        Args:
            stock_code: Stock ticker code
            periods: Optional list of periods. If None, uses all available periods.
        
        Returns:
            TrendAnalysis object or None if insufficient data
        """
        if periods is None:
            periods = self.data_loader.list_available_periods(stock_code)
        
        if len(periods) < 2:
            return None
        
        snapshots = self.data_loader.load_multiple_periods(stock_code, periods)
        if len(snapshots) < 2:
            return None
        
        # Sort snapshots by period
        snapshots.sort(key=lambda s: s.report_period)
        
        # Extract company name
        company_name = snapshots[0].company_name
        
        # Build trend metrics
        metrics = []
        
        # Revenue trend
        metrics.append(self._build_metric(
            "Net Revenue",
            snapshots,
            lambda s: s.net_revenue
        ))
        
        # Margin trends
        metrics.append(self._build_metric(
            "Gross Margin (%)",
            snapshots,
            lambda s: s.gross_margin
        ))
        
        metrics.append(self._build_metric(
            "Operating Margin (%)",
            snapshots,
            lambda s: s.operating_margin
        ))
        
        metrics.append(self._build_metric(
            "Net Margin (%)",
            snapshots,
            lambda s: s.net_margin
        ))
        
        # EPS trend
        metrics.append(self._build_metric(
            "EPS",
            snapshots,
            lambda s: s.eps
        ))
        
        # Debt ratio trend
        metrics.append(self._build_metric(
            "Debt Ratio (%)",
            snapshots,
            lambda s: s.debt_ratio
        ))
        
        # ROE trend
        metrics.append(self._build_metric(
            "ROE (%)",
            snapshots,
            lambda s: s.roe
        ))
        
        # Generate summary
        summary = self._generate_summary(metrics)
        
        return TrendAnalysis(
            stock_code=stock_code,
            company_name=company_name,
            metrics=metrics,
            summary=summary
        )
    
    def _build_metric(
        self, 
        metric_name: str, 
        snapshots: List[FinancialSnapshot], 
        extractor
    ) -> TrendMetric:
        """Build a TrendMetric from snapshots."""
        periods = [s.report_period for s in snapshots]
        values = [extractor(s) for s in snapshots]
        
        return TrendMetric(
            metric_name=metric_name,
            periods=periods,
            values=values
        )
    
    def _generate_summary(self, metrics: List[TrendMetric]) -> str:
        """Generate a text summary of trends."""
        improving = []
        declining = []
        stable = []
        
        for metric in metrics:
            if metric.trend_direction == "improving":
                improving.append(metric.metric_name)
            elif metric.trend_direction == "declining":
                declining.append(metric.metric_name)
            else:
                stable.append(metric.metric_name)
        
        parts = []
        if improving:
            parts.append(f"Improving: {', '.join(improving)}")
        if declining:
            parts.append(f"Declining: {', '.join(declining)}")
        if stable:
            parts.append(f"Stable: {', '.join(stable)}")
        
        return "; ".join(parts) if parts else "Insufficient data for trend analysis"
    
    def get_latest_snapshot(self, stock_code: str) -> Optional[FinancialSnapshot]:
        """
        Get the most recent snapshot for a stock.
        
        Args:
            stock_code: Stock ticker code
        
        Returns:
            Latest FinancialSnapshot or None
        """
        periods = self.data_loader.list_available_periods(stock_code)
        if not periods:
            return None
        
        latest_period = periods[-1]
        return self.data_loader.load_snapshot(stock_code, latest_period)
