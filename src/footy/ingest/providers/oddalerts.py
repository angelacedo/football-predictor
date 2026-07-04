"""OddAlerts provider adapter — historical/closing odds for CLV.

Assumed response shape (verify against real docs before going live):

.. code-block:: json

    [{"home_team": "Arsenal", "away_team": "Chelsea",
      "kickoff": "2024-05-01T18:00:00+00:00",
      "closing": [{"bookmaker": "Pinnacle", "home": 2.05, "draw": 3.5, "away": 3.7}]}]

Like The Odds API, OddAlerts has no shared id scheme with API-Football, so
events are matched by team names + a kickoff tolerance window. All odds
returned are tagged ``is_closing=True``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from footy.config import get_settings
from footy.ingest.providers.base import UnsupportedProviderMixin, http_retry, to_naive_utc
from footy.ingest.schemas import OddsDTO, OddsQuery

log = logging.getLogger("footy.ingest.providers.oddalerts")

_KICKOFF_TOLERANCE = timedelta(hours=2)


def _matches_event(item: dict[str, Any], query: OddsQuery) -> bool:
    if item.get("home_team") != query.home_team or item.get("away_team") != query.away_team:
        return False
    kickoff = datetime.fromisoformat(item["kickoff"])
    return abs(to_naive_utc(kickoff) - to_naive_utc(query.kickoff)) <= _KICKOFF_TOLERANCE


class OddAlertsProvider(UnsupportedProviderMixin):
    """Historical/closing 1X2 odds via OddAlerts."""

    name = "oddalerts"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self._key = api_key or settings.oddalerts_api_key
        self._base = (base_url or settings.oddalerts_api_base).rstrip("/")
        if not self._key:
            raise RuntimeError("ODDALERTS_API_KEY is not set.")

    @http_retry
    def _get_history(self) -> list[dict[str, Any]]:
        url = f"{self._base}/odds/history"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {self._key}"}, timeout=30.0)
        resp.raise_for_status()
        result: list[dict[str, Any]] = resp.json()
        return result

    def get_odds(self, query: OddsQuery) -> list[OddsDTO]:
        for item in self._get_history():
            if not _matches_event(item, query):
                continue
            return [
                OddsDTO(
                    external_fixture_id=query.external_fixture_id,
                    bookmaker=c["bookmaker"],
                    odds_home=float(c["home"]),
                    odds_draw=float(c["draw"]),
                    odds_away=float(c["away"]),
                    is_closing=True,
                )
                for c in item.get("closing", [])
            ]
        log.warning(
            "oddalerts: no historical event matched %s vs %s near %s",
            query.home_team, query.away_team, query.kickoff,
        )
        return []

    def __repr__(self) -> str:
        return "<OddAlertsProvider>"
