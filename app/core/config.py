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

    # AI Review Summary — multi-model providers (disabled by default)
    ai_review_enabled: bool = Field(default=False, alias="AI_REVIEW_ENABLED")
    ai_review_mode: Literal["economy", "balanced", "maximum"] = Field(
        default="economy",
        alias="AI_REVIEW_MODE",
    )
    ai_review_allow_client_mode: bool = Field(
        default=True,
        alias="AI_REVIEW_ALLOW_CLIENT_MODE",
    )
    ai_primary_provider: Literal["openai", "anthropic", "gemini", "deterministic"] = Field(
        default="openai",
        alias="AI_PRIMARY_PROVIDER",
    )
    ai_secondary_provider: Literal["openai", "anthropic", "gemini", "deterministic"] = Field(
        default="anthropic",
        alias="AI_SECONDARY_PROVIDER",
    )
    ai_fallback_order: Annotated[list[str], NoDecode] = Field(
        default=["openai", "anthropic", "gemini", "deterministic"],
        alias="AI_FALLBACK_ORDER",
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    ai_provider_timeout_seconds: float = Field(
        default=20.0,
        alias="AI_PROVIDER_TIMEOUT_SECONDS",
        gt=0,
        le=120,
    )
    ai_max_review_input: int = Field(
        default=40,
        alias="AI_MAX_REVIEW_INPUT",
        ge=1,
        le=500,
    )
    ai_max_estimated_cost_per_request: float = Field(
        default=0.05,
        alias="AI_MAX_ESTIMATED_COST_PER_REQUEST",
        ge=0,
    )
    # Live HTTP to external AI APIs — off unless explicitly enabled AND AI_REVIEW_ENABLED.
    ai_review_live_http: bool = Field(default=False, alias="AI_REVIEW_LIVE_HTTP")

    # AI Shopping Assistant — reuses provider keys; disabled by default
    ai_shopping_enabled: bool = Field(default=False, alias="AI_SHOPPING_ENABLED")
    ai_shopping_mode: Literal["economy", "balanced", "maximum"] = Field(
        default="economy",
        alias="AI_SHOPPING_MODE",
    )
    ai_shopping_allow_client_mode: bool = Field(
        default=True,
        alias="AI_SHOPPING_ALLOW_CLIENT_MODE",
    )
    ai_shopping_max_query_length: int = Field(
        default=500,
        alias="AI_SHOPPING_MAX_QUERY_LENGTH",
        ge=32,
        le=2000,
    )
    ai_shopping_conversation_ttl_seconds: int = Field(
        default=1800,
        alias="AI_SHOPPING_CONVERSATION_TTL_SECONDS",
        ge=60,
        le=86400,
    )
    ai_shopping_live_http: bool = Field(default=False, alias="AI_SHOPPING_LIVE_HTTP")

    # Community Intelligence Platform — connectors + AI summarization (disabled by default)
    community_enabled: bool = Field(default=True, alias="COMMUNITY_ENABLED")
    community_reddit_enabled: bool = Field(default=True, alias="COMMUNITY_REDDIT_ENABLED")
    community_youtube_enabled: bool = Field(default=False, alias="COMMUNITY_YOUTUBE_ENABLED")
    community_amazon_qa_enabled: bool = Field(default=False, alias="COMMUNITY_AMAZON_QA_ENABLED")
    community_marketplace_qa_enabled: bool = Field(
        default=False,
        alias="COMMUNITY_MARKETPLACE_QA_ENABLED",
    )
    community_forums_enabled: bool = Field(default=False, alias="COMMUNITY_FORUMS_ENABLED")
    community_discord_enabled: bool = Field(default=False, alias="COMMUNITY_DISCORD_ENABLED")
    community_use_fixtures: bool = Field(default=True, alias="COMMUNITY_USE_FIXTURES")
    ai_community_enabled: bool = Field(default=False, alias="AI_COMMUNITY_ENABLED")
    ai_community_mode: Literal["economy", "balanced", "maximum"] = Field(
        default="economy",
        alias="AI_COMMUNITY_MODE",
    )
    ai_community_allow_client_mode: bool = Field(
        default=True,
        alias="AI_COMMUNITY_ALLOW_CLIENT_MODE",
    )
    ai_community_live_http: bool = Field(default=False, alias="AI_COMMUNITY_LIVE_HTTP")

    # Knowledge Graph — in-memory, provider-neutral (no external graph DB)
    knowledge_graph_enabled: bool = Field(default=True, alias="KNOWLEDGE_GRAPH_ENABLED")
    knowledge_graph_max_depth: int = Field(
        default=3,
        alias="KNOWLEDGE_GRAPH_MAX_DEPTH",
        ge=1,
        le=10,
    )
    knowledge_graph_max_nodes: int = Field(
        default=100,
        alias="KNOWLEDGE_GRAPH_MAX_NODES",
        ge=1,
        le=1000,
    )
    knowledge_graph_max_edges: int = Field(
        default=200,
        alias="KNOWLEDGE_GRAPH_MAX_EDGES",
        ge=1,
        le=2000,
    )
    knowledge_graph_max_paths: int = Field(
        default=20,
        alias="KNOWLEDGE_GRAPH_MAX_PATHS",
        ge=1,
        le=100,
    )
    knowledge_graph_min_confidence: float = Field(
        default=0.0,
        alias="KNOWLEDGE_GRAPH_MIN_CONFIDENCE",
        ge=0.0,
        le=1.0,
    )
    knowledge_graph_snapshot_schema_version: int = Field(
        default=1,
        alias="KNOWLEDGE_GRAPH_SNAPSHOT_SCHEMA_VERSION",
        ge=1,
        le=100,
    )

    # Personal AI Shopping Agent — fixture profiles, no auth / payment / external DB
    personal_agent_enabled: bool = Field(default=True, alias="PERSONAL_AGENT_ENABLED")
    personal_agent_default_profile_id: str = Field(
        default="profile-budget-student",
        alias="PERSONAL_AGENT_DEFAULT_PROFILE_ID",
    )

    # User Platform — demo/in-memory accounts, no OAuth / MFA / email delivery
    user_platform_enabled: bool = Field(default=True, alias="USER_PLATFORM_ENABLED")

    # Marketplace Data Synchronization — connectors/imports/sync (no real marketplace HTTP)
    marketplace_data_enabled: bool = Field(default=True, alias="MARKETPLACE_DATA_ENABLED")
    marketplace_data_require_auth: bool = Field(
        default=True,
        alias="MARKETPLACE_DATA_REQUIRE_AUTH",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("ai_fallback_order", mode="before")
    @classmethod
    def parse_fallback_order(cls, value: str | list[str]) -> list[str]:
        allowed = {"openai", "anthropic", "gemini", "deterministic"}
        if isinstance(value, str):
            items = [part.strip().lower() for part in value.split(",") if part.strip()]
        else:
            items = [str(part).strip().lower() for part in value]
        cleaned = [item for item in items if item in allowed]
        if "deterministic" not in cleaned:
            cleaned.append("deterministic")
        return cleaned or ["deterministic"]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def ai_external_calls_enabled(self) -> bool:
        """True only when review AI is on AND live HTTP is explicitly enabled."""
        return self.ai_review_enabled and self.ai_review_live_http

    @property
    def ai_shopping_external_calls_enabled(self) -> bool:
        """True only when shopping AI is on AND live HTTP is explicitly enabled."""
        return self.ai_shopping_enabled and self.ai_shopping_live_http

    @property
    def ai_community_external_calls_enabled(self) -> bool:
        """True only when community AI is on AND live HTTP is explicitly enabled."""
        return self.ai_community_enabled and self.ai_community_live_http


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
