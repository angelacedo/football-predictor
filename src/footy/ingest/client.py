"""Thin API-Football (v3) HTTP client.

Docs: https://www.api-football.com/documentation-v3

Example:
    >>> client = ApiFootball()             # doctest: +SKIP
    >>> client.get("fixtures", {"league": 39, "season": 2023})  # doctest: +SKIP
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from footy.config import get_settings

log = logging.getLogger("footy.ingest.client")


class ApiFootball:
    """Minimal wrapper returning the ``response`` array of an API-Football call."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self._key = api_key or settings.football_api_key
        self._base = (base_url or settings.football_api_base).rstrip("/")
        if not self._key:
            raise RuntimeError("FOOTBALL_API_KEY is not set — cannot call API-Football.")

    def get(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """GET ``/{path}`` and return the ``response`` list.

        Raises:
            httpx.HTTPStatusError: on non-2xx responses.
        """
        url = f"{self._base}/{path.lstrip('/')}"
        headers = {"x-apisports-key": self._key}
        resp = httpx.get(url, params=params, headers=headers, timeout=30.0)
        resp.raise_for_status()
        payload = resp.json()
        errors = payload.get("errors")
        if errors:
            log.warning("API-Football returned errors for %s: %s", path, errors)
        result: list[dict[str, Any]] = payload.get("response", [])
        return result

    def __repr__(self) -> str:
        return f"<ApiFootball base={self._base}>"
