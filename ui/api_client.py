"""Shared synchronous API client used by Streamlit pages."""

from typing import Any

import httpx

from app.core.config import get_settings


def api_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    base_url = get_settings().api_base_url.rstrip("/")
    response = httpx.request(
        method,
        f"{base_url}{path}",
        params=params,
        json=json,
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Financial Agent API returned a non-object response")
    return body
