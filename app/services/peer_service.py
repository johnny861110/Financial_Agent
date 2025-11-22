"""Peer comparison service."""

from typing import List, Optional
from app.models import FinancialSnapshot, PeerComparison, PeerAnalysis
from app.core import DataLoader


class PeerService:
    """Service for cross-sectional peer comparison."""
    
    def __init__(self):
        self.data_loader = DataLoader()
    
    def compare_peers(
        self, 
        stock_codes: List[str], 
        period: str,
        metrics: Optional[List[str]] = None
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
        # Load snapshots for all peers
        snapshots = []
        for code in stock_codes:
            snapshot = self.data_loader.load_snapshot(code, period)
            if snapshot:
                snapshots.append(snapshot)
        
        if len(snapshots) < 2:
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
        
        comparisons = []
        
        # Build comparisons
        if "Gross Margin" in metrics:
            comparisons.append(self._compare_metric(
                "Gross Margin (%)",
                snapshots,
                lambda s: s.gross_margin,
                higher_is_better=True
            ))
        
        if "Operating Margin" in metrics:
            comparisons.append(self._compare_metric(
                "Operating Margin (%)",
                snapshots,
                lambda s: s.operating_margin,
                higher_is_better=True
            ))
        
        if "Net Margin" in metrics:
            comparisons.append(self._compare_metric(
                "Net Margin (%)",
                snapshots,
                lambda s: s.net_margin,
                higher_is_better=True
            ))
        
        if "ROE" in metrics:
            comparisons.append(self._compare_metric(
                "ROE (%)",
                snapshots,
                lambda s: s.roe,
                higher_is_better=True
            ))
        
        if "ROA" in metrics:
            comparisons.append(self._compare_metric(
                "ROA (%)",
                snapshots,
                lambda s: s.roa,
                higher_is_better=True
            ))
        
        if "Debt Ratio" in metrics:
            comparisons.append(self._compare_metric(
                "Debt Ratio (%)",
                snapshots,
                lambda s: s.debt_ratio,
                higher_is_better=False
            ))
        
        if "Current Ratio" in metrics:
            comparisons.append(self._compare_metric(
                "Current Ratio",
                snapshots,
                lambda s: s.current_ratio if s.current_ratio else 0.0,
                higher_is_better=True
            ))
        
        # Generate summary
        summary = self._generate_summary(comparisons, stock_codes)
        
        return PeerAnalysis(
            period=period,
            comparisons=comparisons,
            summary=summary
        )
    
    def _compare_metric(
        self,
        metric_name: str,
        snapshots: List[FinancialSnapshot],
        extractor,
        higher_is_better: bool = True
    ) -> PeerComparison:
        """Build a PeerComparison for a specific metric."""
        companies = [s.company_name for s in snapshots]
        values = [extractor(s) for s in snapshots]
        
        # Calculate rankings (1 = best)
        if higher_is_better:
            sorted_values = sorted(enumerate(values), key=lambda x: x[1], reverse=True)
        else:
            sorted_values = sorted(enumerate(values), key=lambda x: x[1])
        
        ranking = [0] * len(values)
        for rank, (idx, _) in enumerate(sorted_values, start=1):
            ranking[idx] = rank
        
        return PeerComparison(
            metric_name=metric_name,
            companies=companies,
            values=values,
            ranking=ranking
        )
    
    def _generate_summary(self, comparisons: List[PeerComparison], stock_codes: List[str]) -> str:
        """Generate summary of peer positioning."""
        # Count how many times each company ranks #1
        first_place_counts = {}
        for code in stock_codes:
            first_place_counts[code] = 0
        
        for comp in comparisons:
            best = comp.best_performer
            for code in stock_codes:
                if code in best or best in code:
                    first_place_counts[code] = first_place_counts.get(code, 0) + 1
                    break
        
        # Find overall leader
        if first_place_counts:
            leader = max(first_place_counts.items(), key=lambda x: x[1])
            return f"Overall leader: {leader[0]} (top rank in {leader[1]} metrics)"
        
        return "Peer comparison completed"
