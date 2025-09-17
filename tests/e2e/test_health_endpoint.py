"""End-to-end smoke tests for the API health endpoint."""

from __future__ import annotations

import os
from typing import Final

import httpx
from tenacity import RetryError, retry, stop_after_delay, wait_fixed

DEFAULT_BASE_URL: Final[str] = "http://api:8000"
HEALTH_PATH: Final[str] = "/health"


def _build_health_url() -> str:
    base_url = os.getenv("API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return f"{base_url}{HEALTH_PATH}"


@retry(wait=wait_fixed(1), stop=stop_after_delay(60), reraise=True)
def _fetch_health() -> httpx.Response:
    """Poll the health endpoint until it becomes available."""

    url = _build_health_url()
    with httpx.Client(timeout=5.0) as client:
        response = client.get(url)
        response.raise_for_status()
    return response


def test_health_endpoint_returns_ok() -> None:
    """The API should report OK status once the stack is ready."""

    try:
        response = _fetch_health()
    except RetryError as exc:  # pragma: no cover - pytest will expose the failure
        raise AssertionError("/health endpoint did not become ready in time") from exc

    payload = response.json()
    assert payload == {"status": "ok"}
