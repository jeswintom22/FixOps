from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from openai import AsyncAzureOpenAI
from pydantic import TypeAdapter

from app.config import Settings

SchemaT = TypeVar("SchemaT")


class AzureAIService(ABC):
    @abstractmethod
    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        raise NotImplementedError


@dataclass(slots=True)
class AzureAIServiceStub(AzureAIService):
    chat_handler: Callable[[str, str, dict[str, Any] | None], Awaitable[str]] | None = None
    embedding_handler: Callable[[str], Awaitable[list[float]]] | None = None
    structured_handler: Callable[[str, type[SchemaT]], Awaitable[SchemaT]] | None = None

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if self.chat_handler is None:
            raise NotImplementedError("AzureAIServiceStub.chat_complete has not been configured.")
        return await self.chat_handler(system_prompt, user_prompt, response_format)

    async def embed(self, text: str) -> list[float]:
        if self.embedding_handler is None:
            raise NotImplementedError("AzureAIServiceStub.embed has not been configured.")
        return await self.embedding_handler(text)

    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        if self.structured_handler is None:
            raise NotImplementedError(
                "AzureAIServiceStub.structured_complete has not been configured."
            )
        return await self.structured_handler(prompt, schema)


@dataclass(slots=True)
class AzureOpenAIService(AzureAIService):
    endpoint: str
    api_key: str
    chat_deployment: str
    embedding_deployment: str
    api_version: str
    _client: AsyncAzureOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in (
                ("AZURE_OPENAI_ENDPOINT", self.endpoint),
                ("AZURE_OPENAI_API_KEY", self.api_key),
                ("AZURE_OPENAI_DEPLOYMENT", self.chat_deployment),
                ("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", self.embedding_deployment),
                ("AZURE_OPENAI_API_VERSION", self.api_version),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Azure OpenAI configuration is incomplete. Missing: " + ", ".join(missing)
            )

        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "AzureOpenAIService":
        return cls(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            chat_deployment=settings.azure_openai_deployment,
            embedding_deployment=settings.azure_openai_embedding_deployment,
            api_version=settings.azure_openai_api_version,
        )

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        request_kwargs: dict[str, Any] = {
            "model": self.chat_deployment,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format

        completion = await self._client.chat.completions.create(**request_kwargs)
        return completion.choices[0].message.content or ""

    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        schema_adapter = TypeAdapter(schema)
        schema_name = getattr(schema, "__name__", "StructuredResponse")
        json_schema = schema_adapter.json_schema()
        schema_payload = {
            "name": schema_name,
            "schema": json_schema,
            "strict": True,
        }
        completion = await self._client.chat.completions.create(
            model=self.chat_deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only JSON that matches the provided schema. "
                        "Do not wrap the JSON in markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": schema_payload,
            },
        )
        content = completion.choices[0].message.content or "{}"
        return schema_adapter.validate_python(json.loads(content))

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self.embedding_deployment,
            input=text,
        )
        return list(response.data[0].embedding)
