"""Central application configuration via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://localhost/elections"
    database_url_sync: str = "postgresql+psycopg2://localhost/elections"

    # App
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    dashboard_port: int = 8501
    log_level: str = "INFO"

    # Scraper
    eci_base_url: str = "https://results.eci.gov.in/ResultAcGenMay2026"
    scraper_rate_limit_delay: float = 1.0
    scraper_max_retries: int = 3
    scraper_timeout: int = 30
    raw_data_dir: str = "data/raw"

    # Cache
    cache_ttl: int = 3600  # 1 hour — results are fully declared and static

    @property
    def raw_data_path(self) -> Path:
        return Path(self.raw_data_dir)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
