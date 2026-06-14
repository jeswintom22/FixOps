from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(alias="DATABASE_URL")
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    ai_provider: str = Field(
        default="",
        validation_alias=AliasChoices("AI_PROVIDER", "LLM_PROVIDER"),
    )
    endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("ENDPOINT", "AZURE_OPENAI_ENDPOINT"),
    )
    api_key: str = Field(
        default="",
        validation_alias=AliasChoices("API_KEY", "AZURE_OPENAI_API_KEY"),
    )
    api_version: str = Field(
        default="",
        validation_alias=AliasChoices("API_VERSION", "AZURE_OPENAI_API_VERSION"),
    )
    chat_model: str = Field(
        default="",
        validation_alias=AliasChoices("CHAT_MODEL", "OPENAI_MODEL"),
    )
    chat_deployment: str = Field(
        default="",
        validation_alias=AliasChoices("CHAT_DEPLOYMENT", "AZURE_OPENAI_DEPLOYMENT"),
    )
    embedding_model: str = Field(default="", validation_alias=AliasChoices("EMBEDDING_MODEL"))
    embedding_deployment: str = Field(
        default="",
        validation_alias=AliasChoices(
            "EMBEDDING_DEPLOYMENT",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        ),
    )

    @field_validator(
        "database_url",
        "app_env",
        "log_level",
        "ai_provider",
        "endpoint",
        "api_key",
        "api_version",
        "chat_model",
        "chat_deployment",
        "embedding_model",
        "embedding_deployment",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}.")
        return normalized

    @model_validator(mode="after")
    def validate_ai_configuration(self) -> "Settings":
        provider = self.resolved_ai_provider
        configured_values = (
            self.ai_provider,
            self.endpoint,
            self.api_key,
            self.api_version,
            self.chat_model,
            self.chat_deployment,
            self.embedding_model,
            self.embedding_deployment,
        )
        if not any(configured_values):
            return self

        if provider == "mock":
            return self

        missing: list[str] = []
        if provider in {"azure_openai", "azure_foundry"}:
            if not self.endpoint:
                missing.append("ENDPOINT")
            if not self.api_key:
                missing.append("API_KEY")
            if not self.api_version:
                missing.append("API_VERSION")
        if provider == "ollama" and not self.endpoint:
            # Keep endpoint optional for local default hosts.
            pass

        if not self.chat_target:
            missing.append("CHAT_MODEL or CHAT_DEPLOYMENT")
        if not self.embedding_target:
            missing.append("EMBEDDING_MODEL or EMBEDDING_DEPLOYMENT")

        if missing:
            raise ValueError(
                f"AI provider configuration is incomplete for {provider}. Missing: "
                + ", ".join(missing)
                + "."
            )
        return self

    @property
    def resolved_ai_provider(self) -> str:
        return (self.ai_provider or "azure_openai").strip().lower()

    @property
    def chat_target(self) -> str:
        return self.chat_deployment or self.chat_model

    @property
    def embedding_target(self) -> str:
        return self.embedding_deployment or self.embedding_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
