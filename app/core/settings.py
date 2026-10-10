"""Application settings, loaded from environment / .env (see .env.example)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_env: str = "local"
    log_level: str = "INFO"

    # LLM (OpenRouter / OpenAI-compatible)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model_fast: str = "openai/gpt-4o-mini"
    openrouter_model_smart: str = "anthropic/claude-3.5-sonnet"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2

    # Storage
    storage_backend: Literal["local", "gcs"] = "local"
    local_storage_dir: str = "./data"
    gcs_bucket: str = ""
    gcs_prefix: str = "switch-jobs-engine"

    # Observability
    otel_enabled: bool = False
    otel_service_name: str = "switch-jobs-engine"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    langfuse_enabled: bool = False
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # Ingestion
    http_user_agent: str = "switch-jobs-engine/0.1 (+personal job search assistant)"
    ingestion_fetch_timeout_seconds: float = 30.0

    @property
    def llm_offline(self) -> bool:
        """True when no API key is configured: the LLM client returns deterministic stubs."""
        return not self.openrouter_api_key.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
