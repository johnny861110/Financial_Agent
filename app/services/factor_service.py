"""Factor exposure analysis service."""

from typing import List, Optional
import statistics
from app.models import FactorExposures, FinancialSnapshot
from app.core import DataLoader, calculate_z_score


class FactorService:
    """Service for calculating factor exposures."""
    
    def __init__(self):
        self.data_loader = DataLoader()
    
    def calculate_exposures(
        self,
        stock_code: str,
        period: str,
        peer_stocks: Optional[List[str]] = None
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
        # Load target snapshot
        target = self.data_loader.load_snapshot(stock_code, period)
        if not target:
            return None
        
        # Load peer snapshots
        if peer_stocks is None or len(peer_stocks) < 3:
            # If no peers specified, use all available stocks as universe
            all_stocks = self.data_loader.list_all_stocks()
            peer_stocks = [s for s in all_stocks if s != stock_code][:20]  # Use up to 20 peers
        
        peers = []
        for peer_code in peer_stocks:
            peer_snapshot = self.data_loader.load_snapshot(peer_code, period)
            if peer_snapshot:
                peers.append(peer_snapshot)
        
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
        commentary = self._generate_commentary(
            quality_z, value_z, momentum_z, size_z, volatility_z
        )
        
        details = {
            "peer_count": len(peers),
            "target_roe": target.roe,
            "target_total_assets": target.total_assets,
        }
        
        return FactorExposures(
            quality=round(quality_z, 2),
            value=round(value_z, 2),
            momentum=round(momentum_z, 2),
            size=round(size_z, 2),
            volatility=round(volatility_z, 2),
            commentary=commentary,
            details=details
        )
    
    def _calculate_quality_factor(self, target: FinancialSnapshot, peers: List[FinancialSnapshot]) -> float:
        """
        Quality factor: ROE, margins, low debt.
        Composite of ROE + Operating Margin - Debt Ratio
        """
        def quality_score(s: FinancialSnapshot) -> float:
            return s.roe + s.operating_margin - (s.debt_ratio / 2)
        
        target_score = quality_score(target)
        peer_scores = [quality_score(p) for p in peers]
        
        mean_score = statistics.mean(peer_scores)
        std_score = statistics.stdev(peer_scores) if len(peer_scores) > 1 else 1.0
        
        return calculate_z_score(target_score, mean_score, std_score)
    
    def _calculate_value_factor(self, target: FinancialSnapshot, peers: List[FinancialSnapshot]) -> float:
        """
        Value factor: inverse of P/E proxy.
        Use EPS as proxy (higher EPS relative to peers = more value)
        """
        target_eps = target.eps
        peer_eps = [p.eps for p in peers if p.eps > 0]
        
        if not peer_eps:
            return 0.0
        
        mean_eps = statistics.mean(peer_eps)
        std_eps = statistics.stdev(peer_eps) if len(peer_eps) > 1 else 1.0
        
        return calculate_z_score(target_eps, mean_eps, std_eps)
    
    def _calculate_momentum_factor(self, target: FinancialSnapshot, peers: List[FinancialSnapshot]) -> float:
        """
        Momentum factor: revenue growth proxy.
        We'll use net margin as a proxy (higher margin suggests positive momentum)
        In real implementation, would use historical price or revenue growth
        """
        target_margin = target.net_margin
        peer_margins = [p.net_margin for p in peers]
        
        mean_margin = statistics.mean(peer_margins)
        std_margin = statistics.stdev(peer_margins) if len(peer_margins) > 1 else 1.0
        
        return calculate_z_score(target_margin, mean_margin, std_margin)
    
    def _calculate_size_factor(self, target: FinancialSnapshot, peers: List[FinancialSnapshot]) -> float:
        """
        Size factor: total assets (negative z-score = small cap premium).
        """
        import math
        
        target_size = math.log(target.total_assets) if target.total_assets > 0 else 0
        peer_sizes = [math.log(p.total_assets) if p.total_assets > 0 else 0 for p in peers]
        
        mean_size = statistics.mean(peer_sizes)
        std_size = statistics.stdev(peer_sizes) if len(peer_sizes) > 1 else 1.0
        
        return calculate_z_score(target_size, mean_size, std_size)
    
    def _calculate_volatility_factor(self, target: FinancialSnapshot, peers: List[FinancialSnapshot]) -> float:
        """
        Volatility factor: debt ratio as proxy for volatility risk.
        Higher debt = higher volatility
        """
        target_debt = target.debt_ratio
        peer_debts = [p.debt_ratio for p in peers]
        
        mean_debt = statistics.mean(peer_debts)
        std_debt = statistics.stdev(peer_debts) if len(peer_debts) > 1 else 1.0
        
        # Invert: higher debt = higher volatility = positive z-score
        return calculate_z_score(target_debt, mean_debt, std_debt)
    
    def _generate_commentary(
        self,
        quality: float,
        value: float,
        momentum: float,
        size: float,
        volatility: float
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
