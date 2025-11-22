"""Data loading utilities."""

import json
from pathlib import Path
from typing import Optional, List
from app.models import FinancialSnapshot
from app.core.config import get_settings


class DataLoader:
    """Load financial data from JSON files."""
    
    def __init__(self):
        self.settings = get_settings()
        self.data_path = self.settings.financial_data_path
    
    def load_snapshot(self, stock_code: str, period: str) -> Optional[FinancialSnapshot]:
        """
        Load a single financial snapshot.
        
        Args:
            stock_code: Stock ticker code
            period: Period identifier (e.g., '2023Q3')
        
        Returns:
            FinancialSnapshot or None if not found
        """
        filename = f"{stock_code}_{period}_enhanced.json"
        file_path = Path(self.data_path) / filename
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return FinancialSnapshot(**data)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return None
    
    def load_multiple_periods(self, stock_code: str, periods: List[str]) -> List[FinancialSnapshot]:
        """
        Load multiple periods for a stock.
        
        Args:
            stock_code: Stock ticker code
            periods: List of period identifiers
        
        Returns:
            List of FinancialSnapshot objects (may be incomplete if some files missing)
        """
        snapshots = []
        for period in periods:
            snapshot = self.load_snapshot(stock_code, period)
            if snapshot:
                snapshots.append(snapshot)
        return snapshots
    
    def list_available_periods(self, stock_code: str) -> List[str]:
        """
        List all available periods for a stock.
        
        Args:
            stock_code: Stock ticker code
        
        Returns:
            List of period identifiers
        """
        pattern = f"{stock_code}_*_enhanced.json"
        files = list(Path(self.data_path).glob(pattern))
        
        periods = []
        for file in files:
            # Extract period from filename: stock_PERIOD_enhanced.json
            parts = file.stem.split('_')
            if len(parts) >= 2:
                period = parts[1]
                periods.append(period)
        
        return sorted(periods)
    
    def list_all_stocks(self) -> List[str]:
        """
        List all stock codes with available data.
        
        Returns:
            List of stock codes
        """
        files = list(Path(self.data_path).glob("*_enhanced.json"))
        
        stocks = set()
        for file in files:
            parts = file.stem.split('_')
            if parts:
                stock_code = parts[0]
                stocks.add(stock_code)
        
        return sorted(list(stocks))


def enrich_snapshot(snapshot: FinancialSnapshot) -> FinancialSnapshot:
    """
    Enrich snapshot with additional derived metrics.
    This function is mainly for validation as computed fields are automatic.
    
    Args:
        snapshot: Input financial snapshot
    
    Returns:
        Same snapshot (computed fields are automatic)
    """
    # Computed fields are automatically calculated by Pydantic
    # This function exists for any manual enrichment if needed in the future
    return snapshot
