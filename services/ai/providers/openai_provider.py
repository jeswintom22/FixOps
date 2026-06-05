from openai import OpenAI
from .base import LLMProvider
import json
import os


class OpenAIProvider(LLMProvider):

    def analyze(self, prompt: str):

        client = OpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY"
            )
        )

        model = os.getenv(
            "OPENAI_MODEL",
            "gpt-4.1-mini"
        )

        response = client.responses.create(
            model=model,
            input=prompt
        )

        text = response.output_text

        return json.loads(text)