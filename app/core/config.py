"""Core configuration and settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Configuration
    openai_api_key: str = ""
    llm_model: str = "gpt-4-turbo-preview"
    llm_temperature: float = 0.0

    # Langfuse Observability
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = ""
    langfuse_host: str = ""
    langfuse_required: bool = False

    # Data Configuration
    data_dir: Path = Path("./data")
    financial_data_path: Path = Path("./data/financial_reports")

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    api_cors_origins: str = "*"

    # Logging
    log_level: str = "INFO"

    # Scoring Thresholds
    management_tenure_good: int = 3  # years
    management_tenure_excellent: int = 5  # years
    board_independence_threshold: float = 0.3  # 30%

    # Earnings Quality Thresholds
    accrual_ratio_threshold: float = 0.1  # 10%
    working_capital_spike_threshold: float = 0.15  # 15%
    one_off_income_threshold: float = 0.2  # 20%

    # Early Warning Thresholds
    ews_receivable_spike_threshold: float = 0.2  # 20% faster than revenue
    ews_inventory_spike_threshold: float = 0.2  # 20% faster than revenue
    ews_margin_compression_threshold: float = -0.05  # -5% decline
    ews_debt_ratio_critical: float = 0.7  # 70%

    # ROIC/WACC Assumptions
    default_risk_free_rate: float = 0.02  # 2%
    default_market_risk_premium: float = 0.06  # 6%
    default_beta: float = 1.0
    default_tax_rate: float = 0.2  # 20%


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
