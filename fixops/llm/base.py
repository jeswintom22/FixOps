from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar


@dataclass
class Message:
    role: str
    content: str


T = TypeVar("T")


class StructuredOutputError(RuntimeError):
    """Raised when the model returns output that cannot be validated."""


class LLMService(Protocol):
    """Abstract chat completion service."""

    async def chat_complete(
        self,
        messages: list[Message],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str: ...

    async def structured_complete(
        self,
        messages: list[Message],
        schema: type[T],
        *,
        max_tokens: int | None = None,
    ) -> T: ...


class EmbeddingService(Protocol):
    """Abstract embedding service."""

    async def embed(self, text: str) -> list[float]: ...


class InMemoryEmbeddingCache:
    """Simple cache for embeddings used during a single pipeline run."""

    def __init__(self, service: EmbeddingService | None) -> None:
        self.service = service
        self._cache: dict[str, list[float]] = {}

    async def embed(self, text: str) -> list[float] | None:
        if self.service is None:
            return None
        if text in self._cache:
            return self._cache[text]
        embedding = await self.service.embed(text)
        self._cache[text] = embedding
        return embedding


def build_json_prompt(schema: type[T], instructions: str | None = None) -> str:
    """Build a prompt that asks the model to return JSON matching the given schema."""
    import json

    from pydantic import TypeAdapter

    schema_adapter = TypeAdapter(schema)
    json_schema = schema_adapter.json_schema()
    parts = [
        instructions or "Return a JSON object matching the schema below.",
        "Do not wrap the JSON in markdown. Output only the JSON object.",
        f"Schema: {json.dumps(json_schema)}",
    ]
    return "\n\n".join(parts)


def parse_and_validate(schema: type[T], raw: str) -> T:
    import json

    from pydantic import TypeAdapter, ValidationError

    text = raw.strip()
    # Strip markdown code fences if present.
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(f"Invalid JSON: {exc}") from exc
    try:
        return TypeAdapter(schema).validate_python(data)
    except ValidationError as exc:
        raise StructuredOutputError(f"JSON does not match schema: {exc}") from exc
