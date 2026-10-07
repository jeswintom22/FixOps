from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, TextIO

import click
from rich.console import Console
from rich.markdown import Markdown
from sqlalchemy.ext.asyncio import AsyncSession

from fixops.config import Settings, get_settings
from fixops.db import (
    IncidentSeverity,
    IncidentStatus,
    KnowledgeChunk,
    init_db,
    make_engine,
)
from fixops.knowledge.loader import KnowledgeChunk as LoaderChunk
from fixops.knowledge.loader import load_knowledge_base
from fixops.knowledge.retriever import KeywordRetriever
from fixops.llm.providers import build_llm_service
from fixops.pipeline import AgentOrchestrator
from fixops.pipeline.state import AgentState
from fixops.pipeline.steps import (
    KnowledgeRetrievalStep,
    LogAnalysisStep,
    RemediationPlanningStep,
    ReportGenerationStep,
    RootCauseAnalysisStep,
)
from fixops.repository import (
    create_incident,
    create_investigation,
    create_or_update_report,
    get_incident,
    get_report_for_investigation,
    list_incidents,
    mark_investigation_completed,
    mark_investigation_failed,
    mark_investigation_running,
    save_knowledge_chunks,
    update_incident_status,
)
from fixops.security.redaction import redact

console = Console()
logger = logging.getLogger("fixops")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWLEDGE_DIR = REPO_ROOT / "knowledge_base"


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


async def setup_database() -> None:
    await init_db()


def _make_session() -> AsyncSession:
    settings = get_settings()
    engine = make_engine(str(settings.database_path))
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return session_factory()


async def _load_retriever(session: AsyncSession) -> KeywordRetriever:
    from fixops.repository import list_knowledge_chunks

    db_chunks = await list_knowledge_chunks(session)
    if not db_chunks:
        console.print(
            "[yellow]Knowledge base is empty. Run `fixops ingest` first,"
            " or supply a directory.[/yellow]"
        )
        chunks = load_knowledge_base(DEFAULT_KNOWLEDGE_DIR)
    else:
        chunks = [
            LoaderChunk(
                source_file=chunk.source_file,
                chunk_index=chunk.chunk_index,
                category=chunk.category,
                content=chunk.content,
                keywords=list(chunk.keywords),
            )
            for chunk in db_chunks
        ]
    return KeywordRetriever(chunks)


async def _save_kb_to_db(session: AsyncSession, chunks: list[LoaderChunk]) -> int:
    db_chunks = [
        KnowledgeChunk(
            source_file=chunk.source_file,
            chunk_index=chunk.chunk_index,
            category=chunk.category,
            content=chunk.content,
            keywords=chunk.keywords,
            embedding=None,
        )
        for chunk in chunks
    ]
    return await save_knowledge_chunks(session, db_chunks)


@click.group()
@click.option("--data-dir", envvar="FIXOPS_DATA_DIR", help="Directory for the SQLite database.")
@click.option("--log-level", envvar="LOG_LEVEL", default="INFO", help="Log level.")
@click.option(
    "--llm-provider",
    envvar="LLM_PROVIDER",
    default=None,
    help="LLM provider: local, ollama, openai, azure_openai, azure_foundry.",
)
@click.option("--llm-model", envvar="LLM_MODEL", default=None, help="Chat model identifier.")
@click.pass_context
def cli(
    ctx: click.Context,
    data_dir: str | None,
    log_level: str,
    llm_provider: str | None,
    llm_model: str | None,
) -> None:
    """FixOps: AI SRE agent for incident investigation."""
    configure_logging(log_level)

    # Propagate CLI overrides via environment variables so the cached settings object
    # and all downstream modules see the same values.
    if data_dir:
        os.environ["FIXOPS_DATA_DIR"] = str(Path(data_dir).resolve())
    if llm_provider:
        os.environ["LLM_PROVIDER"] = llm_provider
    if llm_model:
        os.environ["LLM_MODEL"] = llm_model

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ctx.ensure_object(dict)
    ctx.obj["settings"] = settings

    asyncio.run(setup_database())


@cli.command()
@click.option(
    "--knowledge-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=str(DEFAULT_KNOWLEDGE_DIR),
    help="Directory containing markdown runbooks, playbooks, and postmortems.",
)
@click.pass_context
def ingest(ctx: click.Context, knowledge_dir: Path) -> None:
    """Ingest the knowledge base into the local database."""

    async def _run() -> None:
        async with _make_session() as session:
            chunks = load_knowledge_base(knowledge_dir)
            count = await _save_kb_to_db(session, chunks)
            console.print(f"[green]Ingested {count} chunks from {knowledge_dir}[/green]")

    asyncio.run(_run())


@cli.command()
@click.argument("log_input", required=False, type=click.File("r", encoding="utf-8"))
@click.option("--title", default=None, help="Incident title.")
@click.option("--description", default=None, help="Incident description.")
@click.option(
    "--severity",
    type=click.Choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"], case_sensitive=False),
    default="MEDIUM",
    help="Incident severity.",
)
@click.option("--service", default=None, help="Affected service name.")
@click.option("--env", "environment", default=None, help="Deployment environment.")
@click.option(
    "--no-redaction",
    is_flag=True,
    help="Disable automatic secret/PII redaction before analysis.",
)
@click.pass_context
def investigate(
    ctx: click.Context,
    log_input: TextIO | None,
    title: str | None,
    description: str | None,
    severity: str,
    service: str | None,
    environment: str | None,
    no_redaction: bool,
) -> None:
    """Investigate an incident from a log file or stdin."""
    settings: Settings = ctx.obj["settings"]

    # Read log from file or stdin.
    if log_input is None:
        if sys.stdin.isatty():
            console.print(
                "[yellow]No log file provided and stdin is empty. "
                "Usage: fixops investigate logs.txt[/yellow]"
            )
            sys.exit(1)
        raw_log = sys.stdin.read()
        source = "stdin"
    else:
        raw_log = log_input.read()
        source = getattr(log_input, "name", "file")

    if not raw_log.strip():
        console.print("[red]Error: empty log input.[/red]")
        sys.exit(1)

    title = title or _infer_title(raw_log)

    if not no_redaction:
        raw_log = redact(raw_log)

    asyncio.run(
        _run_investigation(
            settings, title, description, raw_log, severity, service, environment, source
        )
    )


def _infer_title(raw_log: str) -> str:
    first = raw_log.splitlines()[0].strip()
    return first[:80] if first else "Untitled incident"


async def _run_investigation(
    settings: Settings,
    title: str,
    description: str | None,
    raw_log: str,
    severity: str,
    service: str | None,
    environment: str | None,
    source: str,
) -> None:
    llm_service = build_llm_service(settings)

    async with _make_session() as session:
        retriever = await _load_retriever(session)
        orchestrator = AgentOrchestrator(
            steps=[
                LogAnalysisStep(llm_service=llm_service),
                KnowledgeRetrievalStep(retriever=retriever),
                RootCauseAnalysisStep(llm_service=llm_service),
                RemediationPlanningStep(llm_service=llm_service),
                ReportGenerationStep(llm_service=llm_service),
            ]
        )

        incident = await create_incident(
            session,
            title=title,
            description=description,
            raw_log=raw_log,
            severity=IncidentSeverity(severity.upper()),
            source=source,
            service_name=service,
            environment=environment,
        )
        investigation = await create_investigation(session, incident_id=incident.id)
        await mark_investigation_running(session, investigation.id)

        state = AgentState(
            investigation_id=investigation.id,
            incident_id=incident.id,
            incident_title=incident.title,
            raw_log=incident.raw_log,
            incident_description=incident.description,
            incident_metadata=dict(incident.metadata_),
            service_name=incident.service_name,
            source=incident.source,
            environment=incident.environment,
        )

        try:
            final_state = await orchestrator.run(state)
        except Exception as exc:
            logger.exception("Investigation failed")
            await mark_investigation_failed(session, investigation.id, str(exc))
            console.print(f"[red]Investigation failed: {exc}[/red]")
            sys.exit(1)

        if final_state.report is None:
            await mark_investigation_failed(session, investigation.id, "No report generated")
            console.print("[red]Investigation completed but no report was generated.[/red]")
            sys.exit(1)

        report_data = final_state.to_report_payload()
        report = await create_or_update_report(session, report_data)

        await mark_investigation_completed(
            session,
            investigation.id,
            confidence_score=final_state.root_cause.confidence_score
            if final_state.root_cause
            else None,
            root_cause_retried=final_state.root_cause_retried,
            remediation_retried=final_state.remediation_retried,
        )
        await update_incident_status(session, incident.id, IncidentStatus.ANALYZED)

        await session.refresh(incident)
        await session.refresh(investigation)

    console.print(_format_report(final_state, report.id, incident, investigation))


def _format_report(
    state: AgentState,
    report_id: Any,
    incident: Any,
    investigation: Any,
) -> Markdown:
    lines = [
        f"# {state.report.title if state.report else 'Investigation Report'}",
        "",
        f"**Incident ID:** {incident.id}",
        f"**Investigation ID:** {investigation.id}",
        f"**Report ID:** {report_id}",
        f"**Severity:** {incident.severity.value}",
        f"**Status:** {incident.status.value}",
        "",
        "## Executive Summary",
        state.report.executive_summary if state.report else "N/A",
        "",
        "## Incident Summary",
        state.report.incident_summary if state.report else "N/A",
        "",
        "## Root Cause Analysis",
        state.report.root_cause_section if state.report else "N/A",
        "",
        "## Supporting Evidence",
    ]
    if state.root_cause and state.root_cause.evidence_refs:
        for ref in state.root_cause.evidence_refs:
            lines.append(f"- **{ref.source_type}** `{ref.source_ref}`: {ref.content}")
    else:
        lines.append("_No evidence references available._")

    lines.extend(["", "## Remediation Plan"])
    if state.remediation and state.remediation.steps:
        for step in state.remediation.steps:
            lines.append(f"{step.order}. **{step.action}**  ")
            lines.append(f"   Risk: `{step.risk_level}`")
            if step.rationale:
                lines.append(f"   Rationale: {step.rationale}")
            if step.command_hint:
                lines.append(f"   Command hint: `{step.command_hint}`")
    else:
        lines.append("_No remediation steps available._")

    if investigation.root_cause_retried:
        lines.extend(["", "_Root cause analysis was retried with expanded context._"])
    if investigation.remediation_retried:
        lines.extend(["", "_Remediation planning was retried._"])

    return Markdown("\n".join(lines))


@cli.command(name="history")
@click.option("--limit", default=20, help="Maximum number of incidents to show.")
@click.pass_context
def history(ctx: click.Context, limit: int) -> None:
    """List recent incidents and their analysis status."""

    async def _run() -> None:
        async with _make_session() as session:
            incidents = await list_incidents(session, limit=limit)
            if not incidents:
                console.print("No incidents found.")
                return
            for incident in incidents:
                console.print(
                    f"{incident.id} | {incident.created_at:%Y-%m-%d %H:%M} | "
                    f"{incident.severity.value:9} | {incident.status.value:12} | {incident.title}"
                )

    asyncio.run(_run())


@cli.command()
@click.argument("incident_id")
@click.pass_context
def show(ctx: click.Context, incident_id: str) -> None:
    """Show the latest report for an incident."""

    async def _run() -> None:
        import uuid

        async with _make_session() as session:
            try:
                iid = uuid.UUID(incident_id)
            except ValueError:
                console.print("[red]Invalid incident ID.[/red]")
                sys.exit(1)
            incident = await get_incident(session, iid)
            if incident is None:
                console.print("[red]Incident not found.[/red]")
                sys.exit(1)
            report = await get_report_for_investigation(session, incident.investigations[-1].id)
            if report is None:
                console.print("[yellow]No report for this incident yet.[/yellow]")
                return
            console.print(Markdown(report.remediation_section or ""))

    asyncio.run(_run())


@cli.command()
@click.argument("incident_id")
@click.pass_context
def resolve(ctx: click.Context, incident_id: str) -> None:
    """Mark an incident as resolved."""

    async def _run() -> None:
        import uuid

        async with _make_session() as session:
            try:
                iid = uuid.UUID(incident_id)
            except ValueError:
                console.print("[red]Invalid incident ID.[/red]")
                sys.exit(1)
            await update_incident_status(session, iid, IncidentStatus.RESOLVED)
            console.print("[green]Incident marked RESOLVED.[/green]")

    asyncio.run(_run())


@cli.command()
@click.option("--host", default=None, help="Bind host.")
@click.option("--port", default=None, type=int, help="Bind port.")
@click.pass_context
def server(ctx: click.Context, host: str | None, port: int | None) -> None:
    """Start the optional FixOps API server (requires server extras)."""
    try:
        import uvicorn
    except ImportError as exc:
        console.print(
            "[red]Server dependencies are missing. Install with: pip install 'fixops[server]'[/red]"
        )
        raise click.ClickException(str(exc)) from exc

    settings: Settings = ctx.obj["settings"]
    # Import here to avoid hard dependency on FastAPI for CLI-only installs.
    from fixops.server.api import app

    uvicorn.run(
        app,
        host=host or settings.server_host,
        port=port or settings.server_port,
    )


def main() -> None:
    cli(auto_envvar_prefix="FIXOPS")


if __name__ == "__main__":
    main()
