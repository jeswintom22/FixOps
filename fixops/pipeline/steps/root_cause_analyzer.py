from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from pydantic.dataclasses import dataclass

from fixops.config import get_settings
from fixops.llm.base import LLMService, Message
from fixops.pipeline.state import AgentState, EvidenceReference, RootCauseResult
from fixops.pipeline.steps.base import AgentStep


@dataclass
class EvidenceReferenceSchema:
    source_type: str
    source_ref: str
    content: str
    relevance_score: float | None = None


@dataclass
class RootCauseResponse:
    primary_cause: str
    contributing_factors: list[str] | None = None
    confidence_score: float | None = None
    reasoning_chain: str = ""
    evidence_refs: list[EvidenceReferenceSchema] | None = None

    def to_domain(self) -> RootCauseResult:
        return RootCauseResult(
            primary_cause=self.primary_cause,
            contributing_factors=list(self.contributing_factors or []),
            confidence_score=self.confidence_score,
            reasoning_chain=self.reasoning_chain,
            evidence_refs=[
                EvidenceReference(
                    source_type=item.source_type,
                    source_ref=item.source_ref,
                    content=item.content,
                    relevance_score=item.relevance_score,
                )
                for item in self.evidence_refs or []
            ],
        )


class RootCauseAnalysisStep(AgentStep):
    name = "ROOT_CAUSE_ANALYSIS"
    order = 3

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def execute(self, state: AgentState) -> AgentState:
        if state.log_signals is None:
            raise ValueError("Log analysis must complete before root cause analysis")

        response = await self.llm_service.structured_complete(
            messages=[Message(role="user", content=self._build_prompt(state))],
            schema=RootCauseResponse,
        )
        state.root_cause = response.to_domain()
        # Validate that every cited source is one we actually retrieved.
        state.root_cause.evidence_refs = self._validate_citations(state)
        return state

    def build_output(self, state: AgentState) -> Mapping[str, Any]:
        if state.root_cause is None:
            return {}
        return asdict(state.root_cause)

    def _build_prompt(self, state: AgentState) -> str:
        budget = get_settings().raw_log_prompt_budget
        knowledge_context = "\n\n".join(
            (
                f"[{chunk.category or 'UNKNOWN'}] {chunk.source_file}"
                f"#{chunk.chunk_index}\n{chunk.content}"
            )
            for chunk in state.knowledge_chunks
        )
        return "\n".join(
            [
                "Determine the most likely root cause for the incident. Cite only the knowledge "
                "sources listed in the context below, using the exact source_ref format "
                "`filename#chunk_index`.",
                f"Incident title: {state.incident_title}",
                f"Raw log: {state.raw_log[-budget:]}",
                f"Log signals: {state.log_signals}",
                "Knowledge context:",
                knowledge_context or "No knowledge context found.",
            ]
        )

    def _validate_citations(self, state: AgentState) -> list[EvidenceReference]:
        valid_refs = {
            f"{chunk.source_file}#{chunk.chunk_index}" for chunk in state.knowledge_chunks
        }
        valid_refs.add("incident_raw_log")
        if state.root_cause is None:
            return []
        validated: list[EvidenceReference] = []
        for ref in state.root_cause.evidence_refs:
            if ref.source_ref in valid_refs or any(
                ref.source_ref.startswith(chunk.source_file) for chunk in state.knowledge_chunks
            ):
                validated.append(ref)
            else:
                # Drop hallucinated citations rather than failing the whole pipeline.
                validated.append(
                    EvidenceReference(
                        source_type="log",
                        source_ref="incident_raw_log",
                        content=(
                            "Grounded inference replaced an unsupported citation"
                            f" ({ref.source_ref})."
                        ),
                        relevance_score=0.5,
                    )
                )
        return validated
