"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the DealBrain backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="DealBrain", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://dealbrain:dealbrain@localhost:5432/dealbrain",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    # Canonical registry backend: "memory" (demo/default) or "sqlalchemy"
    canonical_registry_backend: Literal["memory", "sqlalchemy"] = Field(
        default="memory",
        alias="CANONICAL_REGISTRY_BACKEND",
    )

    # Price history backend: "memory" (demo/default) or "sqlalchemy"
    price_history_backend: Literal["memory", "sqlalchemy"] = Field(
        default="memory",
        alias="PRICE_HISTORY_BACKEND",
    )

    # Deterministic trend threshold (percent). See price_history statistics docs.
    price_trend_threshold_percent: float = Field(
        default=2.0,
        alias="PRICE_TREND_THRESHOLD_PERCENT",
    )

    # Seed development-only iPhone mock history on price-history search (never in production).
    price_history_seed_demo_mock: bool = Field(
        default=True,
        alias="PRICE_HISTORY_SEED_DEMO_MOCK",
    )

    # CORS
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
