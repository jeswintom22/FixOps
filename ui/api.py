from __future__ import annotations

from typing import Any

import requests

from ui.config import get_api_base_url


class FixOpsApiError(RuntimeError):
    """Raised when the FixOps API returns an unexpected response."""


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{get_api_base_url()}{path}"

    try:
        response = requests.request(method=method, url=url, json=payload, timeout=120)
    except requests.RequestException as exc:
        raise FixOpsApiError(f"Unable to connect to FixOps API at {url}.") from exc

    if response.ok:
        return response.json()

    detail = _extract_error_detail(response)
    raise FixOpsApiError(f"{response.status_code} {response.reason}: {detail}")


def _extract_error_detail(response: requests.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text.strip() or "Unknown error"

    detail = data.get("detail")
    if isinstance(detail, str):
        return detail
    error = data.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message
    return "Unexpected API error"


def create_incident(payload: dict[str, Any]) -> dict[str, Any]:
    return _request("POST", "/incidents", payload)


def run_investigation(incident_id: str) -> dict[str, Any]:
    return _request("POST", "/investigate", {"incident_id": incident_id})


def get_report(report_id: str) -> dict[str, Any]:
    return _request("GET", f"/reports/{report_id}")
