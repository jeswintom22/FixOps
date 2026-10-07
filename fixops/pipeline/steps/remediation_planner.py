from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from pydantic.dataclasses import dataclass

from fixops.db import KnowledgeCategory
from fixops.llm.base import LLMService, Message
from fixops.pipeline.state import AgentState, RemediationPlan, RemediationStepPlan
from fixops.pipeline.steps.base import AgentStep


@dataclass
class RemediationStepSchema:
    order: int
    action: str
    rationale: str | None = None
    risk_level: str = "LOW"
    command_hint: str | None = None
    is_automated: bool = False


@dataclass
class RemediationResponse:
    summary: str
    steps: list[RemediationStepSchema] | None = None

    def to_domain(self) -> RemediationPlan:
        return RemediationPlan(
            summary=self.summary,
            steps=[
                RemediationStepPlan(
                    order=item.order or index,
                    action=item.action,
                    rationale=item.rationale,
                    risk_level=item.risk_level or "LOW",
                    command_hint=item.command_hint,
                    is_automated=item.is_automated or False,
                )
                for index, item in enumerate(self.steps or [], start=1)
            ],
        )


class RemediationPlanningStep(AgentStep):
    name = "REMEDIATION"
    order = 4

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def execute(self, state: AgentState) -> AgentState:
        if state.root_cause is None:
            raise ValueError("Root cause analysis must complete before remediation planning")

        response = await self.llm_service.structured_complete(
            messages=[Message(role="user", content=self._build_prompt(state))],
            schema=RemediationResponse,
        )
        state.remediation = response.to_domain()
        # Safety override: never mark remediation steps as automated.
        for step in state.remediation.steps:
            step.is_automated = False
        return state

    def build_output(self, state: AgentState) -> Mapping[str, Any]:
        if state.remediation is None:
            return {}
        return asdict(state.remediation)

    def _build_prompt(self, state: AgentState) -> str:
        runbooks = "\n\n".join(
            f"[{chunk.category}] {chunk.source_file}#{chunk.chunk_index}\n{chunk.content}"
            for chunk in state.knowledge_chunks
            if chunk.category == KnowledgeCategory.RUNBOOK.value
        )
        playbooks = "\n\n".join(
            f"[{chunk.category}] {chunk.source_file}#{chunk.chunk_index}\n{chunk.content}"
            for chunk in state.knowledge_chunks
            if chunk.category == KnowledgeCategory.PLAYBOOK.value
        )
        return "\n".join(
            [
                "Create a ranked remediation plan for the incident. Each step must have a "
                "risk level (LOW, MEDIUM, HIGH) and an optional command hint. "
                "Set is_automated to false; all commands require human confirmation.",
                f"Root cause: {state.root_cause}",
                "Runbook context:",
                runbooks or "No runbook context found.",
                "Playbook context:",
                playbooks or "No playbook context found.",
            ]
        )
