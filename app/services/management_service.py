"""Management quality scoring service."""

from typing import Optional
from app.models import ManagementScore
from app.core import get_settings, normalize_score


class ManagementService:
    """Service for calculating management quality scores."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def calculate_score(
        self,
        ceo_tenure_years: float = 0,
        cfo_tenure_years: float = 0,
        board_independence_ratio: float = 0.0,
        independent_directors: int = 0,
        total_directors: int = 0,
        family_controlled: bool = False,
        insider_buys: int = 0,
        insider_sells: int = 0,
        governance_incidents: int = 0,
        audit_issues: int = 0,
        related_party_transactions: int = 0,
    ) -> ManagementScore:
        """
        Calculate management quality score.
        
        Formula: M = 0.25*T + 0.25*B + 0.25*I + 0.25*G
        
        Args:
            ceo_tenure_years: CEO tenure in years
            cfo_tenure_years: CFO tenure in years
            board_independence_ratio: Ratio of independent directors
            independent_directors: Number of independent directors
            total_directors: Total board size
            family_controlled: Whether family controlled
            insider_buys: Number of insider buy transactions
            insider_sells: Number of insider sell transactions
            governance_incidents: Number of governance red flags
            audit_issues: Number of audit issues
            related_party_transactions: Number of related party transaction concerns
        
        Returns:
            ManagementScore object
        """
        # Component 1: Tenure Stability (T)
        avg_tenure = (ceo_tenure_years + cfo_tenure_years) / 2
        tenure_score = self._score_tenure(avg_tenure)
        
        # Component 2: Board Independence (B)
        if total_directors > 0:
            independence_ratio = independent_directors / total_directors
        else:
            independence_ratio = board_independence_ratio
        
        board_score = self._score_board_independence(independence_ratio, family_controlled)
        
        # Component 3: Insider Alignment (I)
        insider_score = self._score_insider_alignment(insider_buys, insider_sells)
        
        # Component 4: Governance (G) - inverted red flags
        total_red_flags = governance_incidents + audit_issues + related_party_transactions
        governance_score = self._score_governance(total_red_flags)
        
        # Generate commentary
        commentary = self._generate_commentary(
            tenure_score, board_score, insider_score, governance_score,
            avg_tenure, independence_ratio, insider_buys, insider_sells, total_red_flags
        )
        
        details = {
            "avg_tenure_years": round(avg_tenure, 1),
            "board_independence_ratio": round(independence_ratio, 2),
            "insider_net_activity": insider_buys - insider_sells,
            "total_red_flags": total_red_flags,
        }
        
        return ManagementScore(
            tenure_stability=round(tenure_score, 2),
            board_independence=round(board_score, 2),
            insider_alignment=round(insider_score, 2),
            governance_red_flags=round(governance_score, 2),
            commentary=commentary,
            details=details
        )
    
    def _score_tenure(self, avg_tenure: float) -> float:
        """Score management tenure stability (0-100)."""
        # 0 years = 0, 3 years = 60, 5+ years = 100
        if avg_tenure >= self.settings.management_tenure_excellent:
            return 100.0
        elif avg_tenure >= self.settings.management_tenure_good:
            # Linear interpolation between 60 and 100
            return 60.0 + 40.0 * (avg_tenure - self.settings.management_tenure_good) / (
                self.settings.management_tenure_excellent - self.settings.management_tenure_good
            )
        else:
            # Linear from 0 to 60
            return (avg_tenure / self.settings.management_tenure_good) * 60.0
    
    def _score_board_independence(self, independence_ratio: float, family_controlled: bool) -> float:
        """Score board independence (0-100)."""
        # Base score from independence ratio
        base_score = normalize_score(independence_ratio, 0.0, 0.5)
        
        # Penalty for family control
        if family_controlled:
            base_score *= 0.7
        
        return base_score
    
    def _score_insider_alignment(self, buys: int, sells: int) -> float:
        """Score insider trading alignment (0-100)."""
        net = buys - sells
        
        # Strong buying = 100, neutral = 50, strong selling = 0
        if net >= 5:
            return 100.0
        elif net >= 2:
            return 80.0
        elif net >= 0:
            return 60.0
        elif net >= -2:
            return 40.0
        elif net >= -5:
            return 20.0
        else:
            return 0.0
    
    def _score_governance(self, red_flags: int) -> float:
        """Score governance (inverted red flags, 0-100)."""
        # 0 flags = 100, 1 flag = 70, 2 flags = 40, 3+ flags = 0
        if red_flags == 0:
            return 100.0
        elif red_flags == 1:
            return 70.0
        elif red_flags == 2:
            return 40.0
        else:
            return max(0.0, 40.0 - (red_flags - 2) * 20.0)
    
    def _generate_commentary(
        self,
        tenure_score: float,
        board_score: float,
        insider_score: float,
        governance_score: float,
        avg_tenure: float,
        independence_ratio: float,
        buys: int,
        sells: int,
        red_flags: int
    ) -> str:
        """Generate qualitative commentary."""
        parts = []
        
        # Tenure
        if tenure_score >= 80:
            parts.append(f"Experienced management team (avg {avg_tenure:.1f} years)")
        elif tenure_score >= 60:
            parts.append(f"Stable management (avg {avg_tenure:.1f} years)")
        else:
            parts.append(f"Limited tenure (avg {avg_tenure:.1f} years) - execution risk")
        
        # Board
        if board_score >= 70:
            parts.append(f"Strong board independence ({independence_ratio*100:.0f}%)")
        elif board_score >= 50:
            parts.append(f"Moderate board independence ({independence_ratio*100:.0f}%)")
        else:
            parts.append(f"Weak board independence ({independence_ratio*100:.0f}%) - governance concern")
        
        # Insiders
        net = buys - sells
        if net > 0:
            parts.append(f"Insider buying ({net} net transactions) - positive signal")
        elif net < 0:
            parts.append(f"Insider selling ({abs(net)} net transactions) - caution")
        else:
            parts.append("Neutral insider activity")
        
        # Governance
        if red_flags == 0:
            parts.append("Clean governance record")
        elif red_flags <= 2:
            parts.append(f"{red_flags} governance concern(s)")
        else:
            parts.append(f"Multiple governance red flags ({red_flags}) - serious concern")
        
        return ". ".join(parts) + "."
