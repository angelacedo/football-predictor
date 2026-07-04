"""The Odds API provider adapter — multi-bookmaker 1X2 odds.

Docs: https://the-odds-api.com/liveapi/guides/v4/

The Odds API has no shared id scheme with API-Football, so events are matched
by ``(home_team, away_team)`` plus a kickoff-time tolerance window rather than
:data:`OddsQuery.external_fixture_id`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from footy.config import get_settings
from footy.ingest.providers.base import UnsupportedProviderMixin, http_retry, to_naive_utc
from footy.ingest.schemas import OddsDTO, OddsQuery

log = logging.getLogger("footy.ingest.providers.the_odds_api")

_KICKOFF_TOLERANCE = timedelta(hours=2)
_MARKET = "h2h"


def _matches_event(item: dict[str, Any], query: OddsQuery) -> bool:
    if item.get("home_team") != query.home_team or item.get("away_team") != query.away_team:
        return False
    commence = datetime.fromisoformat(item["commence_time"].replace("Z", "+00:00"))
    return abs(to_naive_utc(commence) - to_naive_utc(query.kickoff)) <= _KICKOFF_TOLERANCE


def _odds_from_event(item: dict[str, Any], query: OddsQuery) -> list[OddsDTO]:
    out: list[OddsDTO] = []
    for bookmaker in item.get("bookmakers", []):
        prices: dict[str, float] = {}
        for market in bookmaker.get("markets", []):
            if market.get("key") != _MARKET:
                continue
            for outcome in market.get("outcomes", []):
                prices[outcome["name"]] = float(outcome["price"])
        if query.home_team in prices and query.away_team in prices and "Draw" in prices:
            out.append(
                OddsDTO(
                    external_fixture_id=query.external_fixture_id,
                    bookmaker=bookmaker.get("title", bookmaker.get("key", "unknown")),
                    odds_home=prices[query.home_team],
                    odds_draw=prices["Draw"],
                    odds_away=prices[query.away_team],
                )
            )
    return out


class TheOddsApiProvider(UnsupportedProviderMixin):
    """Multi-bookmaker 1X2 odds via The Odds API."""

    name = "the_odds_api"

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 sport_key: str | None = None) -> None:
        settings = get_settings()
        self._key = api_key or settings.the_odds_api_key
        self._base = (base_url or settings.the_odds_api_base).rstrip("/")
        self._sport_key = sport_key or settings.the_odds_api_sport_key
        if not self._key:
            raise RuntimeError("THE_ODDS_API_KEY is not set.")

    @http_retry
    def _get_events(self) -> list[dict[str, Any]]:
        url = f"{self._base}/sports/{self._sport_key}/odds"
        resp = httpx.get(
            url,
            params={"apiKey": self._key, "regions": "eu", "markets": _MARKET},
            timeout=30.0,
        )
        resp.raise_for_status()
        result: list[dict[str, Any]] = resp.json()
        return result

    def get_odds(self, query: OddsQuery) -> list[OddsDTO]:
        events = self._get_events()
        for item in events:
            if _matches_event(item, query):
                return _odds_from_event(item, query)
        log.warning(
            "the_odds_api: no event matched %s vs %s near %s",
            query.home_team, query.away_team, query.kickoff,
        )
        return []

    def __repr__(self) -> str:
        return "<TheOddsApiProvider>"
