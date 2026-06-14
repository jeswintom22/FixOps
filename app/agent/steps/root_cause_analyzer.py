from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.agent.state import AgentState, EvidenceReference, RootCauseResult
from app.agent.steps.base import AgentStep
from app.services.ai import LLMService


@dataclass(slots=True)
class RootCauseAnalysisStep(AgentStep):
    llm_service: LLMService
    name: str = "ROOT_CAUSE_ANALYSIS"
    order: int = 3

    async def execute(self, state: AgentState) -> AgentState:
        if state.log_signals is None:
            raise ValueError("Log analysis must complete before root cause analysis.")

        response = await self.llm_service.structured_complete(
            prompt=self._build_prompt(state),
            schema=RootCauseResponse,
        )
        state.root_cause = response.to_domain()
        return state

    def build_output(self, state: AgentState) -> dict[str, Any]:
        if state.root_cause is None:
            return {}
        return asdict(state.root_cause)

    def _build_prompt(self, state: AgentState) -> str:
        knowledge_context = "\n\n".join(
            f"[{chunk.category or 'UNKNOWN'}] {chunk.source_file}#{chunk.chunk_index}\n{chunk.content}"
            for chunk in state.knowledge_chunks
        )
        return "\n".join(
            [
                "Determine the most likely root cause for the incident.",
                f"Incident title: {state.incident_title}",
                f"Raw log: {state.raw_log}",
                f"Log signals: {state.log_signals}",
                "Knowledge context:",
                knowledge_context or "No knowledge context found.",
            ]
        )


@dataclass(slots=True)
class RootCauseResponse:
    primary_cause: str
    contributing_factors: list[str] | None = None
    confidence_score: float | None = None
    reasoning_chain: str = ""
    evidence_refs: list[dict[str, Any]] | None = None

    def to_domain(self) -> RootCauseResult:
        evidence = [
            EvidenceReference(
                source_type=str(item.get("source_type", "UNKNOWN")),
                source_ref=str(item.get("source_ref", "")),
                content=str(item.get("content", "")),
                relevance_score=_as_float(item.get("relevance_score")),
            )
            for item in self.evidence_refs or []
        ]
        return RootCauseResult(
            primary_cause=self.primary_cause,
            contributing_factors=list(self.contributing_factors or []),
            confidence_score=self.confidence_score,
            reasoning_chain=self.reasoning_chain,
            evidence_refs=evidence,
        )


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
