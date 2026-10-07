from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from fixops.config import Settings
from fixops.llm.base import (
    EmbeddingService,
    LLMService,
    Message,
    StructuredOutputError,
    build_json_prompt,
    parse_and_validate,
)


def _messages_to_openai(messages: list[Message]) -> list[dict[str, str]]:
    return [{"role": msg.role, "content": msg.content} for msg in messages]


@dataclass
class OpenAILLMService(LLMService):
    api_key: str
    model: str
    base_url: str | None = None
    timeout: float = 120.0
    max_tokens: int = 2048
    _client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = AsyncOpenAI(**kwargs)

    async def chat_complete(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=_messages_to_openai(messages),
            temperature=temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        return response.choices[0].message.content or ""

    async def structured_complete(
        self,
        messages: list[Message],
        schema: type[Any],
        *,
        max_tokens: int | None = None,
    ) -> Any:
        system_prompt = build_json_prompt(schema)
        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(_messages_to_openai(messages))

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, max=10),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            reraise=True,
        )
        async def _call() -> Any:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=all_messages,
                temperature=0.1,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"},
            )
            return parse_and_validate(schema, response.choices[0].message.content or "{}")

        try:
            return await _call()
        except StructuredOutputError:
            raise
        except Exception as exc:
            raise StructuredOutputError(f"LLM request failed: {exc}") from exc


@dataclass
class AzureOpenAILLMService(OpenAILLMService):
    endpoint: str = ""
    api_version: str = ""

    def __post_init__(self) -> None:
        from openai import AsyncAzureOpenAI

        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            timeout=self.timeout,
        )


@dataclass
class AzureFoundryLLMService(OpenAILLMService):
    endpoint: str = ""
    api_version: str = ""

    def __post_init__(self) -> None:
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "base_url": self.endpoint,
            "timeout": self.timeout,
        }
        if self.api_version:
            kwargs["default_query"] = {"api-version": self.api_version}
        self._client = AsyncOpenAI(**kwargs)


@dataclass
class OllamaLLMService(LLMService):
    model: str
    base_url: str | None = None
    timeout: float = 120.0
    max_tokens: int = 2048
    _client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            from ollama import AsyncClient
        except ImportError as exc:
            raise ImportError(
                "ollama package is required. Install with: pip install 'fixops[ollama]'"
            ) from exc

        kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.base_url:
            kwargs["host"] = self.base_url
        self._client = AsyncClient(**kwargs)

    async def chat_complete(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        response = await self._client.chat(
            model=self.model,
            messages=_messages_to_openai(messages),
            options={"temperature": temperature, "num_predict": max_tokens or self.max_tokens},
        )
        return str(response.message.content or "")

    async def structured_complete(
        self,
        messages: list[Message],
        schema: type[Any],
        *,
        max_tokens: int | None = None,
    ) -> Any:

        from pydantic import TypeAdapter

        system_prompt = build_json_prompt(schema)
        all_messages = [{"role": "system", "content": system_prompt}]
        all_messages.extend(_messages_to_openai(messages))

        @retry(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, max=5),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            reraise=True,
        )
        async def _call() -> Any:
            schema_adapter = TypeAdapter(schema)
            response = await self._client.chat(
                model=self.model,
                messages=all_messages,
                format=schema_adapter.json_schema(),
                options={"temperature": 0.1, "num_predict": max_tokens or self.max_tokens},
            )
            return parse_and_validate(schema, response.message.content or "{}")

        try:
            return await _call()
        except StructuredOutputError:
            raise
        except Exception as exc:
            raise StructuredOutputError(f"Ollama request failed: {exc}") from exc


@dataclass
class OpenAIEmbeddingService(EmbeddingService):
    api_key: str
    model: str
    base_url: str | None = None
    timeout: float = 120.0
    _client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._client = AsyncOpenAI(**kwargs)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self.model, input=text)
        return list(response.data[0].embedding)


@dataclass
class AzureOpenAIEmbeddingService(OpenAIEmbeddingService):
    endpoint: str = ""
    api_version: str = ""

    def __post_init__(self) -> None:
        from openai import AsyncAzureOpenAI

        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            timeout=self.timeout,
        )


@dataclass
class AzureFoundryEmbeddingService(OpenAIEmbeddingService):
    endpoint: str = ""
    api_version: str = ""

    def __post_init__(self) -> None:
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "base_url": self.endpoint,
            "timeout": self.timeout,
        }
        if self.api_version:
            kwargs["default_query"] = {"api-version": self.api_version}
        self._client = AsyncOpenAI(**kwargs)


@dataclass
class OllamaEmbeddingService(EmbeddingService):
    model: str
    base_url: str | None = None
    timeout: float = 120.0
    _client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            from ollama import AsyncClient
        except ImportError as exc:
            raise ImportError(
                "ollama package is required. Install with: pip install 'fixops[ollama]'"
            ) from exc

        kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.base_url:
            kwargs["host"] = self.base_url
        self._client = AsyncClient(**kwargs)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embed(model=self.model, input=text)
        return [float(value) for value in response.embeddings[0]]


def build_llm_service(settings: Settings) -> LLMService:
    provider = settings.llm_provider
    if provider == "local":
        from fixops.llm.local import LocalLLMService

        return LocalLLMService()
    if provider == "openai":
        return OpenAILLMService(
            api_key=settings.api_key,
            model=settings.llm_target,
            base_url=settings.endpoint or None,
            timeout=settings.request_timeout,
            max_tokens=settings.max_output_tokens,
        )
    if provider == "azure_openai":
        return AzureOpenAILLMService(
            api_key=settings.api_key,
            model=settings.llm_target,
            endpoint=settings.endpoint,
            api_version=settings.api_version,
            timeout=settings.request_timeout,
            max_tokens=settings.max_output_tokens,
        )
    if provider == "azure_foundry":
        return AzureFoundryLLMService(
            api_key=settings.api_key,
            model=settings.llm_target,
            endpoint=settings.endpoint,
            api_version=settings.api_version,
            timeout=settings.request_timeout,
            max_tokens=settings.max_output_tokens,
        )
    if provider == "ollama":
        return OllamaLLMService(
            model=settings.llm_target,
            base_url=settings.endpoint or None,
            timeout=settings.request_timeout,
            max_tokens=settings.max_output_tokens,
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


def build_embedding_service(settings: Settings) -> EmbeddingService | None:
    provider = settings.resolved_embedding_provider
    model = settings.embedding_target or settings.llm_target
    if not model:
        return None
    if provider == "local":
        return None
    if provider == "openai":
        return OpenAIEmbeddingService(
            api_key=settings.api_key,
            model=model,
            base_url=settings.endpoint or None,
            timeout=settings.request_timeout,
        )
    if provider == "azure_openai":
        return AzureOpenAIEmbeddingService(
            api_key=settings.api_key,
            model=model,
            endpoint=settings.endpoint,
            api_version=settings.api_version,
            timeout=settings.request_timeout,
        )
    if provider == "azure_foundry":
        return AzureFoundryEmbeddingService(
            api_key=settings.api_key,
            model=model,
            endpoint=settings.endpoint,
            api_version=settings.api_version,
            timeout=settings.request_timeout,
        )
    if provider == "ollama":
        return OllamaEmbeddingService(
            model=model,
            base_url=settings.endpoint or None,
            timeout=settings.request_timeout,
        )
    raise ValueError(f"Unsupported embedding provider: {provider}")
