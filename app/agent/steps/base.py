from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from app.agent.state import AgentState


class AgentStep(ABC):
    name: str
    order: int

    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    @abstractmethod
    def build_output(self, state: AgentState) -> Mapping[str, Any]:
        raise NotImplementedError
