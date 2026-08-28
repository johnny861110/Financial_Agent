"""Context-based existence check tests for CapitalAllocationService.

CapitalAllocationService takes its financial figures as caller-supplied
assumptions (dividends/buybacks/capex/etc.) rather than canonical facts, so
unlike EarningsQuality/EWS/ROIC-WACC there are no required-field/unit/
validation categories to exercise here -- only the filing-existence check
that now goes through CanonicalFinancialContext instead of a raw snapshot.
"""

from app.core import DataLoader
from app.services import CapitalAllocationService
from tests.helpers import RecordProvider, make_record


def test_analyze_returns_none_when_filing_not_found():
    service = CapitalAllocationService(DataLoader(RecordProvider({})))

    result = service.analyze("2330", "2025Q1", dividends=100.0, buybacks=50.0)

    assert result is None


def test_analyze_uses_canonical_context_existence_check():
    record = make_record("2025Q1")
    service = CapitalAllocationService(DataLoader(RecordProvider({("2330", "2025Q1"): record})))

    result = service.analyze(
        "2330", "2025Q1", dividends=100.0, buybacks=50.0, capex=200.0, rd_expense=50.0
    )

    assert result is not None
    assert result.dividends == 100.0
    assert result.buybacks == 50.0
    assert result.capex == 200.0
    assert result.allocation_mix["dividends"] == 25.0
    assert "Growth-focused allocation" in result.commentary
