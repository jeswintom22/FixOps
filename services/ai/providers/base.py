from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def analyze(self, prompt: str):
        pass