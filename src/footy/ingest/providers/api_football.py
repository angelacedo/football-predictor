"""API-Football (v3) provider adapter — fixtures + odds + advanced stats.

Wraps the existing :class:`footy.ingest.client.ApiFootball` transport (which
already retries via ``http_retry``) and maps its raw JSON into DTOs.

get_advanced_stats uses /fixtures/statistics - confirmed live 2026-07-05
against 5 real finished La Liga fixtures: "Ball Possession" and
"expected_goals" are real, present stat types (Sportmonks' free tier doesn't
cover La Liga, and TheStatsAPI's configured key has no active subscription -
this endpoint needs neither). response[0]=home/response[1]=away order was
verified against all 5 fixtures' own /fixtures home/away order (5/5 match) -
same order convention _fixture_from_json below already relies on for this
same provider, not a new assumption.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from footy.ingest.client import ApiFootball
from footy.ingest.providers.base import UnsupportedProviderMixin
from footy.ingest.schemas import AdvancedStatsDTO, FixtureDTO, OddsDTO, OddsQuery

log = logging.getLogger("footy.ingest.providers.api_football")

FINISHED_STATUSES = {"FT", "AET", "PEN"}
MATCH_WINNER = "Match Winner"
_SIDE = {"Home": 0, "Draw": 1, "Away": 2}
_POSSESSION_STAT = "Ball Possession"
_XG_STAT = "expected_goals"


def _fixture_from_json(item: dict[str, Any]) -> FixtureDTO:
    fixture = item["fixture"]
    league = item["league"]
    teams = item["teams"]
    goals = item["goals"]
    finished = fixture["status"]["short"] in FINISHED_STATUSES
    return FixtureDTO(
        external_id=fixture["id"],
        league=league["name"],
        season=league["season"],
        home_team=teams["home"]["name"],
        away_team=teams["away"]["name"],
        kickoff=datetime.fromisoformat(fixture["date"].replace("Z", "+00:00")),
        finished=finished,
        home_goals=goals["home"] if finished else None,
        away_goals=goals["away"] if finished else None,
    )


def _match_winner_odds(bookmaker: dict[str, Any]) -> tuple[float, float, float] | None:
    for bet in bookmaker.get("bets", []):
        if bet.get("name") != MATCH_WINNER:
            continue
        odds: list[float | None] = [None, None, None]
        for value in bet.get("values", []):
            idx = _SIDE.get(value.get("value"))
            if idx is not None:
                odds[idx] = float(value["odd"])
        if all(o is not None for o in odds):
            return (odds[0], odds[1], odds[2])  # type: ignore[return-value]
    return None


def _stat_value(team_stats: dict[str, Any], stat_type: str) -> float | None:
    for stat in team_stats.get("statistics", []):
        if stat.get("type") != stat_type:
            continue
        value = stat.get("value")
        if value is None:
            return None
        if isinstance(value, str):
            return float(value.rstrip("%")) if value.endswith("%") else float(value)
        return float(value)
    return None


class ApiFootballProvider(UnsupportedProviderMixin):
    """Fixtures + odds via API-Football."""

    name = "api_football"

    def __init__(self, client: ApiFootball | None = None) -> None:
        self._client = client or ApiFootball()

    def get_fixtures(self, league_id: int, season: int) -> list[FixtureDTO]:
        items = self._client.get("fixtures", {"league": league_id, "season": season})
        return [_fixture_from_json(i) for i in items]

    def get_odds(self, query: OddsQuery) -> list[OddsDTO]:
        items = self._client.get("odds", {"fixture": query.external_fixture_id})
        out: list[OddsDTO] = []
        for item in items:
            for bookmaker in item.get("bookmakers", []):
                parsed = _match_winner_odds(bookmaker)
                if parsed is None:
                    continue
                out.append(
                    OddsDTO(
                        external_fixture_id=query.external_fixture_id,
                        bookmaker=bookmaker.get("name", "unknown"),
                        odds_home=parsed[0],
                        odds_draw=parsed[1],
                        odds_away=parsed[2],
                    )
                )
        return out

    def get_advanced_stats(self, external_fixture_id: int) -> AdvancedStatsDTO | None:
        items = self._client.get("fixtures/statistics", {"fixture": external_fixture_id})
        if len(items) < 2:
            return None
        home, away = items[0], items[1]
        return AdvancedStatsDTO(
            external_fixture_id=external_fixture_id,
            xg_home=_stat_value(home, _XG_STAT),
            xg_away=_stat_value(away, _XG_STAT),
            possession_home=_stat_value(home, _POSSESSION_STAT),
            possession_away=_stat_value(away, _POSSESSION_STAT),
        )

    def __repr__(self) -> str:
        return "<ApiFootballProvider>"
