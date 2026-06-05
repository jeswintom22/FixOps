from ollama import chat
from .base import LLMProvider
import json
import os


class OllamaProvider(LLMProvider):

    def analyze(self, prompt: str):

        model = os.getenv(
            "OLLAMA_MODEL",
            "qwen3:8b"
        )

        response = chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        text = response["message"]["content"]

        print(text)  # temporary debugging

        return json.loads(text)