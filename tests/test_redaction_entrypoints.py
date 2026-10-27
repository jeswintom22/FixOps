import asyncio
from typing import Any

import pytest
from click.testing import CliRunner

import fixops.cli as cli_module
import fixops.server.api as api_module
from fixops.server.api import IncidentCreate, api_create_incident

SECRET = "supersecret123"


def _capture_cli_investigation(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    async def fake_run_investigation(
        settings: Any,
        title: str,
        description: str | None,
        raw_log: str,
        *args: Any,
    ) -> None:
        captured.update(title=title, description=description, raw_log=raw_log)

    monkeypatch.setattr(cli_module, "_run_investigation", fake_run_investigation)
    return captured


def test_cli_inferred_title_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_cli_investigation(monkeypatch)
    result = CliRunner().invoke(
        cli_module.cli,
        ["investigate", "-"],
        input=f"password={SECRET}\nERROR db timeout\n",
    )
    assert result.exit_code == 0, result.output
    assert SECRET not in captured["title"]
    assert "<REDACTED>" in captured["title"]
    assert SECRET not in captured["raw_log"]


def test_cli_explicit_title_and_description_are_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_cli_investigation(monkeypatch)
    result = CliRunner().invoke(
        cli_module.cli,
        [
            "investigate",
            "-",
            "--title",
            f"token={SECRET}",
            "--description",
            f"api_key={SECRET}",
        ],
        input="ERROR db timeout\n",
    )
    assert result.exit_code == 0, result.output
    assert SECRET not in captured["title"]
    assert SECRET not in captured["description"]


def test_cli_no_redaction_keeps_title(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_cli_investigation(monkeypatch)
    result = CliRunner().invoke(
        cli_module.cli,
        ["investigate", "-", "--no-redaction"],
        input=f"password={SECRET}\n",
    )
    assert result.exit_code == 0, result.output
    assert SECRET in captured["title"]


def test_api_create_incident_redacts_all_text_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_create_incident(session: Any, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(api_module, "create_incident", fake_create_incident)
    payload = IncidentCreate(
        title=f"password={SECRET}",
        description=f"api_key={SECRET}",
        raw_log=f"token={SECRET}",
        metadata={"note": f"secret={SECRET}"},
    )
    asyncio.run(api_create_incident(payload, session=None, _=None))  # type: ignore[arg-type]

    assert SECRET not in captured["title"]
    assert SECRET not in captured["description"]
    assert SECRET not in captured["raw_log"]
    assert SECRET not in captured["metadata"]["note"]
