"""Shared test helpers for provider adapters."""

from __future__ import annotations

from typing import Any

import httpx


class FakeResponse:
    """Minimal stand-in for ``httpx.Response`` used to mock provider HTTP calls."""

    def __init__(self, json_data: Any, status_code: int = 200) -> None:
        self._json = json_data
        self.status_code = status_code

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}", request=None, response=None  # type: ignore[arg-type]
            )
