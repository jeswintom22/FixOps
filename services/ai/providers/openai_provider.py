from .base import LLMProvider


class OpenAIProvider(LLMProvider):

    def analyze(self, prompt: str):
        return {
            "provider": "openai",
            "response": "placeholder"
        }