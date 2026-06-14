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


def build_llm_provider(settings: Settings) -> LLMService:
    """Build the LLM (chat) provider. Reads LLM_PROVIDER env var first, falls back to AI_PROVIDER."""
    provider = (settings.llm_provider or settings.resolved_ai_provider).strip().lower()

    if provider == "ollama":
        return OllamaService.from_settings(settings)
    if provider == "azure_foundry":
        return AzureFoundryService.from_settings(settings)
    if provider == "azure_openai":
        return AzureOpenAIService.from_settings(settings)
    if provider == "mock":
        return MockAIService()
    raise ValueError(
        f"Unsupported LLM provider: {provider}. "
        "Expected one of: azure_openai, azure_foundry, ollama, mock."
    )


def build_embedding_provider(settings: Settings) -> EmbeddingService:
    """Build the embedding provider. Reads EMBEDDING_PROVIDER env var first, falls back to AI_PROVIDER."""
    provider = (settings.embedding_provider or settings.resolved_ai_provider).strip().lower()

    if provider == "azure_openai":
        return AzureOpenAIService.from_settings(settings)
    if provider == "azure_foundry":
        return AzureFoundryService.from_settings(settings)
    if provider == "ollama":
        return OllamaService.from_settings(settings)
    if provider == "mock":
        return MockAIService()
    raise ValueError(
        f"Unsupported embedding provider: {provider}. "
        "Expected one of: azure_openai, azure_foundry, ollama, mock."
    )


@lru_cache
def get_llm_provider() -> LLMService:
    return build_llm_provider(get_settings())


@lru_cache
def get_embedding_provider() -> EmbeddingService:
    return build_embedding_provider(get_settings())


# Keep these as the dependency-injection entry points used by deps.py
def get_llm_service() -> LLMService:
    return get_llm_provider()


def get_embedding_service() -> EmbeddingService:
    return get_embedding_provider()