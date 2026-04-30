"""Agent service configuration — env-driven via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # Shared secret between Django and the agent service
    agent_service_internal_token: str = Field(default="dev-internal-token")

    # Database (Postgres + pgvector) — used to fetch brand, references, chunks
    database_url: str = Field(default="postgres://helix:helix_password_change_me@localhost:5432/helix")

    # Redis pub/sub for streaming events to Django channels
    agent_stream_redis_url: str = Field(default="redis://localhost:6379/4")

    # LiteLLM / model routing
    default_model: str = Field(default="openai/gpt-4o-mini")
    critic_model: str = Field(default="openai/gpt-4o")
    embedding_model: str = Field(default="openai/text-embedding-3-small")

    # Observability
    langsmith_api_key: str = Field(default="")
    langsmith_project: str = Field(default="helix-dev")
    langsmith_tracing: bool = Field(default=False)

    # Provider keys (LiteLLM reads from env directly; we read them so we know what's configured)
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    return Settings()
