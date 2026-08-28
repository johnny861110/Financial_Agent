"""Backward-compatible facade over the configured financial data provider."""

from typing import Optional, List

from app.data.factory import get_data_provider
from app.data.context import CanonicalFinancialContext
from app.data.models import SnapshotRecord
from app.data.providers import FinancialDataProvider
from app.models import FinancialSnapshot


class DataLoader:
    """Load financial data without exposing its backing provider to services."""

    def __init__(self, provider: FinancialDataProvider | None = None):
        self.provider = provider or get_data_provider()

    def load_record(self, stock_code: str, period: str) -> Optional[SnapshotRecord]:
        """Load a snapshot together with source and quality metadata."""
        return self.provider.load_record(stock_code, period)

    def load_context(self, stock_code: str, period: str) -> Optional[CanonicalFinancialContext]:
        """Load one filing as a schema-aware service context."""
        record = self.load_record(stock_code, period)
        return CanonicalFinancialContext(record) if record else None

    def load_snapshot(self, stock_code: str, period: str) -> Optional[FinancialSnapshot]:
        """
        Load a single financial snapshot.

        Args:
            stock_code: Stock ticker code
            period: Period identifier (e.g., '2023Q3')

        Returns:
            FinancialSnapshot or None if not found
        """
        record = self.load_record(stock_code, period)
        return record.snapshot if record else None

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

    def load_multiple_contexts(
        self, stock_code: str, periods: List[str]
    ) -> List[CanonicalFinancialContext]:
        """Load available filing contexts while preserving rich provider metadata."""
        contexts = []
        for period in periods:
            context = self.load_context(stock_code, period)
            if context and context.has_analysis_data:
                contexts.append(context)
        return contexts

    def list_available_periods(self, stock_code: str) -> List[str]:
        """
        List all available periods for a stock.

        Args:
            stock_code: Stock ticker code

        Returns:
            List of period identifiers
        """
        return self.provider.list_available_periods(stock_code)

    def list_all_stocks(self) -> List[str]:
        """
        List all stock codes with available data.

        Returns:
            List of stock codes
        """
        return self.provider.list_all_stocks()


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
