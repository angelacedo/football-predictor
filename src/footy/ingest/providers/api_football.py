"""API-Football (v3) provider adapter — fixtures + odds.

Wraps the existing :class:`footy.ingest.client.ApiFootball` transport (which
already retries via ``http_retry``) and maps its raw JSON into DTOs. No
advanced-stats support — that's Sportmonks/TheStatsAPI's job.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from footy.ingest.client import ApiFootball
from footy.ingest.providers.base import UnsupportedProviderMixin
from footy.ingest.schemas import FixtureDTO, OddsDTO, OddsQuery

log = logging.getLogger("footy.ingest.providers.api_football")

FINISHED_STATUSES = {"FT", "AET", "PEN"}
MATCH_WINNER = "Match Winner"
_SIDE = {"Home": 0, "Draw": 1, "Away": 2}


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

    def __repr__(self) -> str:
        return "<ApiFootballProvider>"
