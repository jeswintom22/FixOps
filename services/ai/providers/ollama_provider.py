from .base import LLMProvider


class OllamaProvider(LLMProvider):

    def analyze(self, prompt: str):
        return {
            "provider": "ollama",
            "response": "placeholder"
        }