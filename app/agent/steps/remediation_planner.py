from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.agent.state import AgentState, RemediationPlan, RemediationStepPlan
from app.agent.steps.base import AgentStep
from app.core.constants import KnowledgeCategory
from app.services.ai import LLMService


@dataclass(slots=True)
class RemediationPlanningStep(AgentStep):
    llm_service: LLMService
    name: str = "REMEDIATION"
    order: int = 4

    async def execute(self, state: AgentState) -> AgentState:
        if state.root_cause is None:
            raise ValueError("Root cause analysis must complete before remediation planning.")

        response = await self.llm_service.structured_complete(
            prompt=self._build_prompt(state),
            schema=RemediationResponse,
        )
        state.remediation = response.to_domain()
        return state

    def build_output(self, state: AgentState) -> dict[str, Any]:
        if state.remediation is None:
            return {}
        return asdict(state.remediation)

    def _build_prompt(self, state: AgentState) -> str:
        playbooks = "\n\n".join(
            f"{chunk.source_file}#{chunk.chunk_index}\n{chunk.content}"
            for chunk in state.knowledge_chunks
            if chunk.category == KnowledgeCategory.PLAYBOOK
        )
        return "\n".join(
            [
                "Create a ranked remediation plan for the incident.",
                f"Root cause: {state.root_cause}",
                "Playbook context:",
                playbooks or "No playbook context found.",
            ]
        )


@dataclass(slots=True)
class RemediationResponse:
    summary: str
    steps: list[dict[str, Any]] | None = None

    def to_domain(self) -> RemediationPlan:
        return RemediationPlan(
            summary=self.summary,
            steps=[
                RemediationStepPlan(
                    order=int(item.get("order", index)),
                    action=str(item["action"]),
                    rationale=item.get("rationale"),
                    risk_level=str(item.get("risk_level", "LOW")),
                    command_hint=item.get("command_hint"),
                    is_automated=bool(item.get("is_automated", False)),
                )
                for index, item in enumerate(self.steps or [], start=1)
            ],
        )
