from __future__ import annotations

import os


API_URL_ENV_VAR = "FIXOPS_API_URL"
DEFAULT_API_URL = "http://127.0.0.1:8000"


def get_api_base_url() -> str:
    return os.getenv(API_URL_ENV_VAR, DEFAULT_API_URL).rstrip("/")
