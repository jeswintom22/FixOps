import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from fixops import cli as cli_module
from fixops.config import get_settings
from fixops.security.network import is_loopback_host
from fixops.server import api


@pytest.fixture
def no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("FIXOPS_API_KEY", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def with_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("FIXOPS_API_KEY", "test-key")
    get_settings.cache_clear()
    yield "test-key"
    get_settings.cache_clear()


async def _empty_list_incidents(_session, *, limit: int = 50, offset: int = 0) -> list:
    return []


async def _no_db():
    yield None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api, "list_incidents", _empty_list_incidents)
    api.app.dependency_overrides[api.get_db] = _no_db
    yield
    api.app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", True),
        ("127.5.5.5", True),
        ("::1", True),
        ("[::1]", True),
        ("::ffff:127.0.0.1", True),
        ("localhost", True),
        ("0.0.0.0", False),
        ("::", False),
        ("10.0.0.5", False),
        ("example.com", False),
        ("", False),
        (None, False),
    ],
)
def test_is_loopback_host(host: str | None, expected: bool) -> None:
    assert is_loopback_host(host) is expected


def test_no_key_rejects_non_loopback_client(no_api_key: None, client: None) -> None:
    with TestClient(api.app, client=("203.0.113.7", 50000)) as http:
        response = http.get("/incidents")
    assert response.status_code == 401


def test_no_key_allows_loopback_client(no_api_key: None, client: None) -> None:
    with TestClient(api.app, client=("127.0.0.1", 50000)) as http:
        response = http.get("/incidents")
    assert response.status_code == 200


def test_key_required_and_checked(with_api_key: str, client: None) -> None:
    with TestClient(api.app, client=("203.0.113.7", 50000)) as http:
        assert http.get("/incidents").status_code == 401
        assert http.get("/incidents", headers={"X-API-Key": "wrong"}).status_code == 401
        ok = http.get("/incidents", headers={"X-API-Key": with_api_key})
    assert ok.status_code == 200


@pytest.mark.parametrize("limit", [0, -1, api.MAX_INCIDENT_LIST_LIMIT + 1, 100000])
def test_incident_limit_is_bounded(no_api_key: None, client: None, limit: int) -> None:
    with TestClient(api.app, client=("127.0.0.1", 50000)) as http:
        response = http.get("/incidents", params={"limit": limit})
    assert response.status_code == 422


def test_server_refuses_non_loopback_without_key(
    no_api_key: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import uvicorn

    calls: list[dict] = []
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: calls.append(kw))
    result = CliRunner().invoke(cli_module.cli, ["server", "--host", "0.0.0.0"])
    assert result.exit_code != 0
    assert "Refusing to bind" in result.output
    assert calls == []


def test_server_allows_non_loopback_with_key(
    with_api_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import uvicorn

    calls: list[dict] = []
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: calls.append(kw))
    result = CliRunner().invoke(cli_module.cli, ["server", "--host", "0.0.0.0"])
    assert result.exit_code == 0, result.output
    assert calls and calls[0]["host"] == "0.0.0.0"
