"""Sportmonks provider adapter — fixtures + advanced stats (xG, possession).

Field names follow Sportmonks Football API v3 (``include=participants;scores;
statistics.type``). Verify against your actual plan/version before going live —
this adapter is built and tested against the shape documented below, not a
live account.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from footy.config import get_settings
from footy.ingest.providers.base import ProviderError, UnsupportedProviderMixin, http_retry
from footy.ingest.schemas import AdvancedStatsDTO, FixtureDTO

log = logging.getLogger("footy.ingest.providers.sportmonks")

_FINISHED_STATES = {"FT", "AET", "PEN"}
_XG_STAT = "expected-goals"
_POSSESSION_STAT = "ball-possession"


def _team_name(item: dict[str, Any], location: str) -> str:
    for p in item.get("participants", []):
        if p.get("meta", {}).get("location") == location:
            return str(p["name"])
    raise ProviderError(f"sportmonks: no {location} participant in fixture {item.get('id')}")


def _fixture_from_json(item: dict[str, Any]) -> FixtureDTO:
    state = item.get("state", "NS")
    finished = state in _FINISHED_STATES
    scores = item.get("scores") or {}
    return FixtureDTO(
        external_id=item["id"],
        league=item.get("league", {}).get("name", "unknown"),
        season=item.get("season", {}).get("id", 0),
        home_team=_team_name(item, "home"),
        away_team=_team_name(item, "away"),
        kickoff=datetime.fromisoformat(item["starting_at"]),
        finished=finished,
        home_goals=scores.get("home") if finished else None,
        away_goals=scores.get("away") if finished else None,
    )


def _stat_value(stats: list[dict[str, Any]], type_code: str, location: str) -> float | None:
    for s in stats:
        if s.get("type", {}).get("code") == type_code and s.get("location") == location:
            value = s.get("data", {}).get("value")
            return float(value) if value is not None else None
    return None


class SportmonksProvider(UnsupportedProviderMixin):
    """Fixtures + advanced stats via Sportmonks."""

    name = "sportmonks"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self._key = api_key or settings.sportmonks_api_key
        self._base = (base_url or settings.sportmonks_api_base).rstrip("/")
        if not self._key:
            raise RuntimeError("SPORTMONKS_API_KEY is not set.")

    @http_retry
    def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self._base}/{path.lstrip('/')}"
        resp = httpx.get(
            url, params={**params, "api_token": self._key}, timeout=30.0
        )
        resp.raise_for_status()
        return resp.json().get("data")

    def get_fixtures(self, league_id: int, season: int) -> list[FixtureDTO]:
        items: list[dict[str, Any]] = self._get(
            "fixtures",
            {"filters": f"leagueIds:{league_id}", "season_id": season,
             "include": "participants;scores"},
        ) or []
        return [_fixture_from_json(i) for i in items]

    def get_advanced_stats(self, external_fixture_id: int) -> AdvancedStatsDTO | None:
        item: dict[str, Any] | None = self._get(
            f"fixtures/{external_fixture_id}", {"include": "statistics.type"}
        )
        if not item:
            return None
        stats = item.get("statistics", [])
        return AdvancedStatsDTO(
            external_fixture_id=external_fixture_id,
            xg_home=_stat_value(stats, _XG_STAT, "home"),
            xg_away=_stat_value(stats, _XG_STAT, "away"),
            possession_home=_stat_value(stats, _POSSESSION_STAT, "home"),
            possession_away=_stat_value(stats, _POSSESSION_STAT, "away"),
        )

    def __repr__(self) -> str:
        return "<SportmonksProvider>"
