"""Peer comparison service."""

from typing import Callable, List, Optional
from app.models import PeerComparison, PeerAnalysis
from app.core import DataLoader
from app.data import CanonicalFinancialContext

MONEY_UNIT = "TWD_thousands"


class PeerService:
    """Service for cross-sectional peer comparison."""

    def __init__(self, data_loader: DataLoader | None = None):
        self.data_loader = data_loader or DataLoader()

    def compare_peers(
        self, stock_codes: List[str], period: str, metrics: Optional[List[str]] = None
    ) -> Optional[PeerAnalysis]:
        """
        Compare multiple companies on key metrics for a given period.

        Args:
            stock_codes: List of stock codes to compare
            period: Period identifier (e.g., '2023Q3')
            metrics: Optional list of metric names to compare

        Returns:
            PeerAnalysis object or None if insufficient data
        """
        # Load contexts for all peers
        contexts = []
        for code in stock_codes:
            context = self.data_loader.load_context(code, period)
            if context and context.has_analysis_data:
                contexts.append(context)

        if len(contexts) < 2:
            return None

        # Default metrics if none specified
        if metrics is None:
            metrics = [
                "Gross Margin",
                "Operating Margin",
                "Net Margin",
                "ROE",
                "ROA",
                "Debt Ratio",
            ]

        comparisons: List[PeerComparison] = []

        # Build comparisons; a company missing the specific metric's inputs is
        # excluded from that comparison rather than contributing a fabricated
        # zero.
        if "Gross Margin" in metrics:
            self._append_comparison(
                comparisons,
                "Gross Margin (%)",
                contexts,
                lambda c: c.ratio_percent("gross_margin", "gross_profit", "net_revenue"),
                higher_is_better=True,
            )

        if "Operating Margin" in metrics:
            self._append_comparison(
                comparisons,
                "Operating Margin (%)",
                contexts,
                lambda c: c.ratio_percent("operating_margin", "operating_income", "net_revenue"),
                higher_is_better=True,
            )

        if "Net Margin" in metrics:
            self._append_comparison(
                comparisons,
                "Net Margin (%)",
                contexts,
                lambda c: c.ratio_percent("net_margin", "net_income", "net_revenue"),
                higher_is_better=True,
            )

        if "ROE" in metrics:
            self._append_comparison(
                comparisons,
                "ROE (%)",
                contexts,
                lambda c: c.ratio_percent("roe", "net_income", "equity", annualize=4),
                higher_is_better=True,
            )

        if "ROA" in metrics:
            self._append_comparison(
                comparisons,
                "ROA (%)",
                contexts,
                lambda c: c.ratio_percent("roa", "net_income", "total_assets", annualize=4),
                higher_is_better=True,
            )

        if "Debt Ratio" in metrics:
            self._append_comparison(
                comparisons,
                "Debt Ratio (%)",
                contexts,
                lambda c: c.ratio_percent("debt_ratio", "total_liabilities", "total_assets"),
                higher_is_better=False,
            )

        if "Current Ratio" in metrics:
            self._append_comparison(
                comparisons,
                "Current Ratio",
                contexts,
                self._current_ratio,
                higher_is_better=True,
            )

        # Generate summary
        summary = self._generate_summary(comparisons, contexts)

        return PeerAnalysis(period=period, comparisons=comparisons, summary=summary)

    def _current_ratio(self, context: CanonicalFinancialContext) -> Optional[float]:
        """Current assets / current liabilities, preferring a producer-supplied ratio."""
        ratio = context.metric_value("current_ratio", "ratio")
        if ratio is not None:
            return ratio
        current_assets = context.optional_value("current_assets", MONEY_UNIT)
        current_liabilities = context.optional_value("current_liabilities", MONEY_UNIT)
        if current_assets is None or current_liabilities is None or current_liabilities == 0:
            return None
        return current_assets / current_liabilities

    def _append_comparison(
        self,
        comparisons: List[PeerComparison],
        metric_name: str,
        contexts: List[CanonicalFinancialContext],
        extractor: Callable[[CanonicalFinancialContext], Optional[float]],
        *,
        higher_is_better: bool = True,
    ) -> None:
        """Build a PeerComparison for a specific metric, skipping companies without it."""
        companies: List[str] = []
        values: List[float] = []
        for context in contexts:
            value = extractor(context)
            if value is not None:
                companies.append(context.company_name)
                values.append(value)

        if len(values) < 2:
            return

        # Calculate rankings (1 = best)
        if higher_is_better:
            sorted_values = sorted(enumerate(values), key=lambda x: x[1], reverse=True)
        else:
            sorted_values = sorted(enumerate(values), key=lambda x: x[1])

        ranking = [0] * len(values)
        for rank, (idx, _) in enumerate(sorted_values, start=1):
            ranking[idx] = rank

        comparisons.append(
            PeerComparison(
                metric_name=metric_name, companies=companies, values=values, ranking=ranking
            )
        )

    def _generate_summary(
        self, comparisons: List[PeerComparison], contexts: List[CanonicalFinancialContext]
    ) -> str:
        """Generate summary of peer positioning."""
        # Comparisons name companies by company_name, which is the stock code only
        # when the producer has no name for it. Map back through the contexts
        # rather than matching codes against names as text.
        code_by_name = {context.company_name: context.stock_code for context in contexts}
        first_place_counts = {context.stock_code: 0 for context in contexts}

        for comp in comparisons:
            code = code_by_name.get(comp.best_performer)
            if code is not None:
                first_place_counts[code] += 1

        if not first_place_counts:
            return "Peer comparison completed"
        leader, wins = max(first_place_counts.items(), key=lambda item: item[1])
        if wins == 0:
            # Every count tied at zero; max() would name the first peer anyway.
            return "Peer comparison completed"
        # The comparison rows name companies, so the summary names the leader
        # both ways; a bare code left the answer unable to tie 2330 to 台積電.
        name = next(c.company_name for c in contexts if c.stock_code == leader)
        label = leader if name == leader else f"{leader} {name}"
        return f"Overall leader: {label} (top rank in {wins} metrics)"
