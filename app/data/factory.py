"""Construct the configured financial data provider."""

from functools import lru_cache

from app.core.config import get_settings
from app.data.providers import (
    FallbackFinancialDataProvider,
    FinancialDataProvider,
    FinancialReportsProvider,
    JsonFinancialDataProvider,
)


@lru_cache()
def get_data_provider() -> FinancialDataProvider:
    settings = get_settings()
    json_provider = JsonFinancialDataProvider(settings.financial_data_path)

    if settings.data_provider == "json":
        return json_provider
    if settings.data_provider != "financial_reports":
        raise ValueError(f"Unsupported DATA_PROVIDER: {settings.data_provider}")

    remote_provider = FinancialReportsProvider(
        base_url=settings.financial_reports_base_url,
        timeout=settings.financial_reports_timeout,
        max_retries=settings.financial_reports_max_retries,
        cache_ttl_seconds=settings.data_cache_ttl_seconds,
    )
    if settings.allow_json_fallback:
        return FallbackFinancialDataProvider(remote_provider, json_provider)
    return remote_provider
