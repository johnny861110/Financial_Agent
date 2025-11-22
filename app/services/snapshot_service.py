"""Snapshot service for single-period financial analysis."""

from typing import Optional
from app.models import FinancialSnapshot
from app.core import DataLoader, enrich_snapshot


class SnapshotService:
    """Service for loading and analyzing single financial snapshots."""
    
    def __init__(self):
        self.data_loader = DataLoader()
    
    def get_snapshot(self, stock_code: str, period: str) -> Optional[FinancialSnapshot]:
        """
        Get enriched financial snapshot for a specific period.
        
        Args:
            stock_code: Stock ticker code
            period: Period identifier (e.g., '2023Q3')
        
        Returns:
            Enriched FinancialSnapshot or None if not found
        """
        snapshot = self.data_loader.load_snapshot(stock_code, period)
        if snapshot:
            return enrich_snapshot(snapshot)
        return None
    
    def get_summary(self, stock_code: str, period: str) -> Optional[dict]:
        """
        Get structured summary of financial snapshot.
        
        Args:
            stock_code: Stock ticker code
            period: Period identifier
        
        Returns:
            Dictionary with key metrics and analysis
        """
        snapshot = self.get_snapshot(stock_code, period)
        if not snapshot:
            return None
        
        return {
            "identification": {
                "stock_code": snapshot.stock_code,
                "company_name": snapshot.company_name,
                "period": snapshot.report_period,
                "currency": snapshot.currency,
                "unit": snapshot.unit,
            },
            "income_statement": {
                "net_revenue": snapshot.net_revenue,
                "gross_profit": snapshot.gross_profit,
                "operating_income": snapshot.operating_income,
                "net_income": snapshot.net_income,
                "eps": snapshot.eps,
            },
            "margins": {
                "gross_margin": round(snapshot.gross_margin, 2),
                "operating_margin": round(snapshot.operating_margin, 2),
                "net_margin": round(snapshot.net_margin, 2),
            },
            "balance_sheet": {
                "total_assets": snapshot.total_assets,
                "total_liabilities": snapshot.total_liabilities,
                "equity": snapshot.equity,
                "cash_and_equivalents": snapshot.cash_and_equivalents,
            },
            "financial_structure": {
                "debt_ratio": round(snapshot.debt_ratio, 2),
                "equity_ratio": round(snapshot.equity_ratio, 2),
                "current_ratio": round(snapshot.current_ratio, 2) if snapshot.current_ratio else None,
            },
            "returns": {
                "roa": round(snapshot.roa, 2),
                "roe": round(snapshot.roe, 2),
            },
        }
