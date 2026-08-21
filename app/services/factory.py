"""Lazy service registry for API request handlers."""

from dataclasses import dataclass
from functools import lru_cache

from app.core import DataLoader
from app.services.capital_allocation_service import CapitalAllocationService
from app.services.earnings_quality_service import EarningsQualityService
from app.services.ews_service import EarlyWarningService
from app.services.factor_service import FactorService
from app.services.management_service import ManagementService
from app.services.peer_service import PeerService
from app.services.roic_wacc_service import ROICWACCService
from app.services.snapshot_service import SnapshotService
from app.services.trend_service import TrendService


@dataclass
class ServiceRegistry:
    snapshot: SnapshotService
    trend: TrendService
    peer: PeerService
    management: ManagementService
    earnings_quality: EarningsQualityService
    roic_wacc: ROICWACCService
    factor: FactorService
    capital_allocation: CapitalAllocationService
    ews: EarlyWarningService

    @classmethod
    def build(cls, data_loader: DataLoader | None = None) -> "ServiceRegistry":
        loader = data_loader or DataLoader()
        return cls(
            snapshot=SnapshotService(loader),
            trend=TrendService(loader),
            peer=PeerService(loader),
            management=ManagementService(),
            earnings_quality=EarningsQualityService(loader),
            roic_wacc=ROICWACCService(loader),
            factor=FactorService(loader),
            capital_allocation=CapitalAllocationService(loader),
            ews=EarlyWarningService(loader),
        )


@lru_cache()
def get_service_registry() -> ServiceRegistry:
    return ServiceRegistry.build()
