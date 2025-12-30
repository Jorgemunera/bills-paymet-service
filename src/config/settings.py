"""Application settings using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    environment: str = "development"
    app_name: str = "payment-service"
    app_version: str = "1.0.0"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (SQLite)
    database_path: str = "data/payments.db"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    idempotency_ttl_seconds: int = 86400  # 24 hours

    # Business Rules
    max_retries: int = 3
    retry_success_probability: float = 0.5

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def redis_url(self) -> str:
        """Build Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()