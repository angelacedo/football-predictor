"""TheStatsAPI provider adapter — advanced stats (xG, possession) only.

Assumed response shape (verify against real docs before going live):

.. code-block:: json

    {"fixture_id": 5001,
     "home": {"xg": 1.74, "possession": 54.2},
     "away": {"xg": 0.81, "possession": 45.8}}
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from footy.config import get_settings
from footy.ingest.providers.base import UnsupportedProviderMixin, http_retry
from footy.ingest.schemas import AdvancedStatsDTO

log = logging.getLogger("footy.ingest.providers.thestatsapi")


class TheStatsApiProvider(UnsupportedProviderMixin):
    """Advanced stats (xG, possession) via TheStatsAPI."""

    name = "thestatsapi"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self._key = api_key or settings.thestatsapi_key
        self._base = (base_url or settings.thestatsapi_base).rstrip("/")
        if not self._key:
            raise RuntimeError("THESTATSAPI_KEY is not set.")

    @http_retry
    def _get(self, fixture_id: int) -> dict[str, Any] | None:
        url = f"{self._base}/matches/{fixture_id}/stats"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {self._key}"}, timeout=30.0)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    def get_advanced_stats(self, external_fixture_id: int) -> AdvancedStatsDTO | None:
        payload = self._get(external_fixture_id)
        if payload is None:
            return None
        home, away = payload.get("home", {}), payload.get("away", {})
        return AdvancedStatsDTO(
            external_fixture_id=external_fixture_id,
            xg_home=home.get("xg"),
            xg_away=away.get("xg"),
            possession_home=home.get("possession"),
            possession_away=away.get("possession"),
        )

    def __repr__(self) -> str:
        return "<TheStatsApiProvider>"
