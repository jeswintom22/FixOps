from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.services.ai import (
    AzureFoundryService,
    AzureOpenAIService,
    EmbeddingService,
    LLMService,
    MockAIService,
    OllamaService,
    ProviderAIService,
)


def build_ai_provider(settings: Settings) -> ProviderAIService:
    provider = settings.resolved_ai_provider
    if provider == "azure_foundry":
        return AzureFoundryService.from_settings(settings)
    if provider == "azure_openai":
        return AzureOpenAIService.from_settings(settings)
    if provider == "ollama":
        return OllamaService.from_settings(settings)
    if provider == "mock":
        return MockAIService()
    raise ValueError(
        "Unsupported AI_PROVIDER. Expected one of: azure_openai, azure_foundry, ollama, mock."
    )


@lru_cache
def get_ai_provider() -> ProviderAIService:
    return build_ai_provider(get_settings())


def get_llm_service() -> LLMService:
    return get_ai_provider()


def get_embedding_service() -> EmbeddingService:
    return get_ai_provider()
