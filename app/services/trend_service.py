"""Trend analysis service for multi-period analysis."""

from collections.abc import Callable
from typing import List, Optional, cast
from app.models import FinancialSnapshot, TrendMetric, TrendAnalysis
from app.core import DataLoader
from app.data import CanonicalFinancialContext


class TrendService:
    """Service for analyzing trends across multiple periods."""

    def __init__(self, data_loader: DataLoader | None = None):
        self.data_loader = data_loader or DataLoader()

    def analyze_trend(
        self, stock_code: str, periods: Optional[List[str]] = None
    ) -> Optional[TrendAnalysis]:
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

        contexts = self.data_loader.load_multiple_contexts(stock_code, periods)
        if len(contexts) < 2:
            return None

        contexts.sort(key=lambda context: context.period)

        company_name = contexts[0].company_name

        # Build trend metrics
        metrics = []

        # Revenue trend
        metrics.append(
            self._build_context_metric(
                "Net Revenue",
                contexts,
                lambda context: context.optional_value("net_revenue", "TWD_thousands"),
            )
        )

        # Margin trends
        metrics.append(
            self._build_context_metric(
                "Gross Margin (%)",
                contexts,
                lambda context: context.ratio_percent(
                    "gross_margin", "gross_profit", "net_revenue"
                ),
            )
        )

        metrics.append(
            self._build_context_metric(
                "Operating Margin (%)",
                contexts,
                lambda context: context.ratio_percent(
                    "operating_margin", "operating_income", "net_revenue"
                ),
            )
        )

        metrics.append(
            self._build_context_metric(
                "Net Margin (%)",
                contexts,
                lambda context: context.ratio_percent("net_margin", "net_income", "net_revenue"),
            )
        )

        # EPS trend
        metrics.append(
            self._build_context_metric(
                "EPS",
                contexts,
                lambda context: context.optional_value("eps_basic", "TWD_per_share"),
            )
        )

        # Debt ratio trend
        metrics.append(
            self._build_context_metric(
                "Debt Ratio (%)",
                contexts,
                lambda context: context.ratio_percent(
                    "debt_ratio", "total_liabilities", "total_assets"
                ),
            )
        )

        # ROE trend
        metrics.append(
            self._build_context_metric(
                "ROE (%)",
                contexts,
                lambda context: context.ratio_percent("roe", "net_income", "equity", annualize=4),
            )
        )

        # Generate summary
        summary = self._generate_summary(metrics)

        return TrendAnalysis(
            stock_code=stock_code, company_name=company_name, metrics=metrics, summary=summary
        )

    def _build_context_metric(
        self,
        metric_name: str,
        contexts: List[CanonicalFinancialContext],
        extractor: Callable[[CanonicalFinancialContext], float | None],
    ) -> TrendMetric:
        """Build a trend without converting unavailable values to zero."""
        pairs = []
        for context in contexts:
            value = extractor(context)
            if value is not None:
                pairs.append((context.period, value))
        return TrendMetric(
            metric_name=metric_name,
            periods=[period for period, _ in pairs],
            values=[value for _, value in pairs],
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
        return cast(
            Optional[FinancialSnapshot], self.data_loader.load_snapshot(stock_code, latest_period)
        )
