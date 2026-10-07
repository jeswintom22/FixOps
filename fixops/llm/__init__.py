"""LLM and embedding provider abstractions."""

from fixops.llm.base import EmbeddingService, LLMService, Message, StructuredOutputError
from fixops.llm.local import LocalLLMService
from fixops.llm.providers import (
    AzureFoundryLLMService,
    AzureOpenAILLMService,
    OllamaLLMService,
    OpenAILLMService,
    build_llm_service,
)

__all__ = [
    "AzureFoundryLLMService",
    "AzureOpenAILLMService",
    "EmbeddingService",
    "LLMService",
    "LocalLLMService",
    "Message",
    "OllamaLLMService",
    "OpenAILLMService",
    "StructuredOutputError",
    "build_llm_service",
]
