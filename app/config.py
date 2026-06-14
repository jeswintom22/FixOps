from functools import lru_cache

from pydantic import Field, field_validator, model_validator
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
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_embedding_deployment: str = Field(
        default="",
        alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    )
    azure_openai_api_version: str = Field(default="", alias="AZURE_OPENAI_API_VERSION")

    @field_validator(
        "database_url",
        "app_env",
        "log_level",
        "azure_openai_endpoint",
        "azure_openai_api_key",
        "azure_openai_deployment",
        "azure_openai_embedding_deployment",
        "azure_openai_api_version",
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
    def validate_azure_configuration(self) -> "Settings":
        azure_values = (
            self.azure_openai_endpoint,
            self.azure_openai_api_key,
            self.azure_openai_deployment,
            self.azure_openai_embedding_deployment,
            self.azure_openai_api_version,
        )
        configured = [bool(value) for value in azure_values]
        if any(configured) and not all(configured):
            raise ValueError(
                "Azure OpenAI configuration is incomplete. Set "
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, "
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT, and AZURE_OPENAI_API_VERSION together."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
