from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from platformdirs import user_data_dir
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["local", "ollama", "openai", "azure_openai", "azure_foundry"]


class Settings(BaseSettings):
    """Environment and CLI configuration for FixOps."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Data persistence
    data_dir: Path = Field(
        default_factory=lambda: Path(user_data_app_dir()),
        validation_alias=AliasChoices("FIXOPS_DATA_DIR"),
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def _coerce_data_dir(cls, value: Path | str) -> Path:
        if isinstance(value, str):
            return Path(value)
        return value

    # LLM provider configuration
    llm_provider: Provider = Field(
        default="local",
        validation_alias=AliasChoices("LLM_PROVIDER", "AI_PROVIDER"),
    )
    llm_model: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_MODEL", "CHAT_MODEL", "OLLAMA_MODEL"),
    )
    llm_deployment: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_DEPLOYMENT", "CHAT_DEPLOYMENT"),
    )

    # Embedding provider configuration (defaults to the LLM provider)
    embedding_provider: Provider | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_PROVIDER"),
    )
    embedding_model: str = Field(
        default="",
        validation_alias=AliasChoices("EMBEDDING_MODEL"),
    )
    embedding_deployment: str = Field(
        default="",
        validation_alias=AliasChoices("EMBEDDING_DEPLOYMENT"),
    )

    # Provider credentials
    endpoint: str = Field(default="", validation_alias=AliasChoices("ENDPOINT", "OPENAI_BASE_URL"))
    api_key: str = Field(default="", validation_alias=AliasChoices("API_KEY", "OPENAI_API_KEY"))
    api_version: str = Field(default="", validation_alias=AliasChoices("API_VERSION"))

    # Server / UI
    api_auth_token: str = Field(
        default="",
        validation_alias=AliasChoices("API_AUTH_TOKEN", "FIXOPS_API_KEY"),
    )
    cors_origins: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )
    server_host: str = Field(default="127.0.0.1", validation_alias=AliasChoices("SERVER_HOST"))
    server_port: int = Field(default=8000, validation_alias=AliasChoices("SERVER_PORT"))

    # Pipeline behavior
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))
    request_timeout: float = Field(default=120.0, validation_alias=AliasChoices("REQUEST_TIMEOUT"))
    max_output_tokens: int = Field(default=2048, validation_alias=AliasChoices("MAX_OUTPUT_TOKENS"))
    raw_log_prompt_budget: int = Field(
        default=20000,
        validation_alias=AliasChoices("RAW_LOG_PROMPT_BUDGET"),
    )
    top_k_default: int = Field(default=5, validation_alias=AliasChoices("TOP_K_DEFAULT"))
    top_k_high_severity: int = Field(
        default=10, validation_alias=AliasChoices("TOP_K_HIGH_SEVERITY")
    )

    # Redaction
    redaction_enabled: bool = Field(
        default=True, validation_alias=AliasChoices("REDACTION_ENABLED")
    )

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("llm_provider", "embedding_provider", mode="before")
    @classmethod
    def _normalize_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized in {"mock", "none"}:
            return "local"
        return normalized

    @property
    def database_path(self) -> Path:
        return self.data_dir / "fixops.sqlite"

    @property
    def llm_target(self) -> str:
        return self.llm_deployment or self.llm_model

    @property
    def embedding_target(self) -> str:
        return self.embedding_deployment or self.embedding_model

    @property
    def resolved_embedding_provider(self) -> Provider:
        return self.embedding_provider or self.llm_provider

    def require_credentials(self) -> None:
        """Raise ValueError if the selected provider needs credentials that are missing."""
        for provider in {self.llm_provider, self.resolved_embedding_provider}:
            if provider in {"openai", "azure_openai", "azure_foundry"} and not self.api_key:
                raise ValueError(f"Provider {provider} requires API_KEY or OPENAI_API_KEY.")
            if provider in {"azure_openai", "azure_foundry"}:
                if not self.endpoint:
                    raise ValueError(f"Provider {provider} requires ENDPOINT.")
                if not self.api_version:
                    raise ValueError(f"Provider {provider} requires API_VERSION.")
            if provider in {"openai", "ollama"} and not self.llm_target:
                raise ValueError(
                    f"Provider {provider} requires LLM_MODEL (or CHAT_MODEL / OLLAMA_MODEL)."
                )


def user_data_app_dir() -> str:
    return user_data_dir(appname="fixops", appauthor=False)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
