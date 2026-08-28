"""Field-state, unit, and peer-filtering tests for FactorService."""

import pytest

from app.core import DataLoader, InsufficientDataError
from app.data import CanonicalFact, FieldAvailability, UnitMismatchError
from app.services import FactorService
from tests.helpers import RecordProvider, make_record

TARGET = dict(
    net_revenue=1000.0,
    operating_income=250.0,
    net_income=200.0,
    equity=2000.0,
    total_assets=5000.0,
    total_liabilities=2000.0,
    eps=10.0,
)

PEER_1 = dict(
    net_revenue=800.0,
    operating_income=100.0,
    net_income=64.0,
    equity=1600.0,
    total_assets=4000.0,
    total_liabilities=2400.0,
    eps=5.0,
)

PEER_2 = dict(
    net_revenue=900.0,
    operating_income=90.0,
    net_income=45.0,
    equity=1500.0,
    total_assets=4500.0,
    total_liabilities=1800.0,
    eps=4.0,
)

PEER_3 = dict(
    net_revenue=1100.0,
    operating_income=110.0,
    net_income=55.0,
    equity=1800.0,
    total_assets=5500.0,
    total_liabilities=2200.0,
    eps=6.0,
)

PEER_INCOMPLETE = dict(
    net_revenue=700.0,
    operating_income=None,  # excluded from the peer pool
    net_income=40.0,
    equity=1200.0,
    total_assets=3500.0,
    total_liabilities=1400.0,
    eps=3.0,
)


def _provider(target_overrides=None, target_kwargs=None):
    records = {
        ("2330", "2025Q1"): make_record(
            "2025Q1",
            stock_code="2330",
            snapshot_overrides=target_overrides or TARGET,
            **(target_kwargs or {}),
        ),
        ("1101", "2025Q1"): make_record("2025Q1", stock_code="1101", snapshot_overrides=PEER_1),
        ("1216", "2025Q1"): make_record("2025Q1", stock_code="1216", snapshot_overrides=PEER_2),
        ("2317", "2025Q1"): make_record("2025Q1", stock_code="2317", snapshot_overrides=PEER_3),
        ("2454", "2025Q1"): make_record(
            "2025Q1", stock_code="2454", snapshot_overrides=PEER_INCOMPLETE
        ),
    }
    return RecordProvider(records)


def test_calculate_exposures_excludes_incomplete_peers():
    service = FactorService(DataLoader(_provider()))

    exposures = service.calculate_exposures(
        "2330", "2025Q1", peer_stocks=["1101", "1216", "2317", "2454"]
    )

    assert exposures is not None
    assert exposures.details["peer_count"] == 3
    assert isinstance(exposures.quality, float)
    assert isinstance(exposures.value, float)
    assert isinstance(exposures.momentum, float)
    assert isinstance(exposures.size, float)
    assert isinstance(exposures.volatility, float)
    assert exposures.commentary


def test_calculate_exposures_returns_none_with_fewer_than_three_valid_peers():
    service = FactorService(DataLoader(_provider()))

    exposures = service.calculate_exposures("2330", "2025Q1", peer_stocks=["1101", "2454", "9999"])

    assert exposures is None


def test_calculate_exposures_raises_for_missing_required_field():
    service = FactorService(
        DataLoader(_provider(target_overrides={**TARGET, "operating_income": None}))
    )

    with pytest.raises(InsufficientDataError) as exc_info:
        service.calculate_exposures("2330", "2025Q1", peer_stocks=["1101", "1216", "2317"])

    assert "operating_income" in exc_info.value.missing_fields


def test_calculate_exposures_treats_not_applicable_as_unusable():
    service = FactorService(
        DataLoader(
            _provider(
                target_kwargs={
                    "field_availability": [
                        FieldAvailability(
                            field="equity",
                            statement="balance_sheet",
                            unit="TWD_thousands",
                            state="not_applicable",
                            reason="Non-standard filing",
                        )
                    ]
                }
            )
        )
    )

    with pytest.raises(InsufficientDataError) as exc_info:
        service.calculate_exposures("2330", "2025Q1", peer_stocks=["1101", "1216", "2317"])

    assert "equity" in exc_info.value.missing_fields


def test_calculate_exposures_raises_on_unit_mismatch():
    service = FactorService(
        DataLoader(
            _provider(
                target_kwargs={
                    "facts": [
                        CanonicalFact(
                            id=1,
                            field="net_income",
                            value=200.0,
                            unit="USD_thousands",
                            statement="income_statement",
                            period_type="duration",
                            source_type="xbrl",
                            confidence=1.0,
                        )
                    ]
                }
            )
        )
    )

    with pytest.raises(UnitMismatchError):
        service.calculate_exposures("2330", "2025Q1", peer_stocks=["1101", "1216", "2317"])
