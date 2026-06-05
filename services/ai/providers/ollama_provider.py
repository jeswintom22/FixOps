from .base import LLMProvider


class OllamaProvider(LLMProvider):

    def analyze(self, prompt: str):
        return {
            "root_cause": "Placeholder root cause",
            "severity": "HIGH",
            "suggested_fix": "Placeholder fix"
        }