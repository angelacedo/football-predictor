"""Shared test helpers for provider adapters."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest


@pytest.fixture
def model_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Isolate ml.registry's model_dir to a tmp dir for the test's duration.

    footy.config.get_settings() is process-cached (lru_cache), so tests that
    save/load models must point MODEL_DIR here and clear the cache before and
    after, or they'd read/pollute whatever real model_dir is configured.
    """
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    from footy.config import get_settings

    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


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
