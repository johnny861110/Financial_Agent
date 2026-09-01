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


def describe_api_error(exc: Exception) -> str:
    """
    Turn a failed API call into a message that says what actually went wrong.

    Pages used to collapse every failure into "Data not found", which hides an
    unreachable API, a malformed period, and a real 404 behind the same words.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        detail = _detail_message(exc.response)
        if status == 404:
            return "No data for this stock and period."
        if status == 422:
            return detail or "The request was rejected as invalid."
        if status == 502:
            return f"The upstream data source returned something unusable. {detail}".strip()
        if status == 503:
            return f"The upstream data source is unavailable. {detail}".strip()
        return f"The API returned HTTP {status}. {detail}".strip()
    if isinstance(exc, httpx.TimeoutException):
        return "The API did not respond in time."
    if isinstance(exc, httpx.TransportError):
        return f"Could not reach the API at {get_settings().api_base_url}: {exc}"
    return str(exc)


def _detail_message(response: httpx.Response) -> str:
    """Pull the human-readable half out of a FastAPI error body."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    detail = body.get("detail", body) if isinstance(body, dict) else body
    if isinstance(detail, dict):
        return str(detail.get("message") or detail)
    return str(detail)
