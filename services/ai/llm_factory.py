import os

from dotenv import load_dotenv

from services.ai.providers.openai_provider import (
    OpenAIProvider
)

from services.ai.providers.ollama_provider import (
    OllamaProvider
)

load_dotenv()


def get_provider():

    provider = os.getenv(
        "LLM_PROVIDER",
        "ollama"
    ).lower()

    if provider == "openai":
        return OpenAIProvider()

    if provider == "ollama":
        return OllamaProvider()

    raise ValueError(
        f"Unsupported provider: {provider}"
    )