"""ApiFootballProvider: fixture/odds JSON -> DTOs, via a fake transport (no network)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from footy.ingest.providers.api_football import ApiFootballProvider
from footy.ingest.schemas import OddsQuery

FIXTURE_JSON = {
    "fixture": {"id": 5, "date": "2024-05-01T18:00:00+00:00", "status": {"short": "FT"}},
    "league": {"name": "EPL", "season": 2024},
    "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
    "goals": {"home": 3, "away": 1},
}

ODDS_JSON = {
    "bookmakers": [
        {
            "name": "Bet365",
            "bets": [
                {
                    "name": "Match Winner",
                    "values": [
                        {"value": "Home", "odd": "2.10"},
                        {"value": "Draw", "odd": "3.40"},
                        {"value": "Away", "odd": "3.60"},
                    ],
                }
            ],
        },
        {"name": "NoMarket", "bets": [{"name": "Over/Under", "values": []}]},
    ]
}


STATS_JSON = [
    {"team": {"name": "Arsenal"}, "statistics": [
        {"type": "Ball Possession", "value": "58%"},
        {"type": "expected_goals", "value": "1.74"},
    ]},
    {"team": {"name": "Chelsea"}, "statistics": [
        {"type": "Ball Possession", "value": "42%"},
        {"type": "expected_goals", "value": 0.81},
    ]},
]


class FakeClient:
    def __init__(self, fixtures: list[dict[str, Any]] | None = None,
                 odds: list[dict[str, Any]] | None = None,
                 stats: list[dict[str, Any]] | None = None) -> None:
        self._fixtures = fixtures or []
        self._odds = odds or []
        self._stats = stats or []

    def get(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if path == "fixtures":
            return self._fixtures
        if path == "fixtures/statistics":
            return self._stats
        return self._odds


def test_get_fixtures_maps_to_dto() -> None:
    provider = ApiFootballProvider(client=FakeClient(fixtures=[FIXTURE_JSON]))
    fixtures = provider.get_fixtures(league_id=39, season=2024)
    assert len(fixtures) == 1
    fx = fixtures[0]
    assert fx.external_id == 5
    assert fx.home_team == "Arsenal"
    assert fx.finished is True
    assert fx.home_goals == 3 and fx.away_goals == 1


def test_get_fixtures_unfinished_has_no_goals() -> None:
    item = {**FIXTURE_JSON, "fixture": {**FIXTURE_JSON["fixture"], "status": {"short": "NS"}}}
    provider = ApiFootballProvider(client=FakeClient(fixtures=[item]))
    fx = provider.get_fixtures(39, 2024)[0]
    assert fx.finished is False
    assert fx.home_goals is None and fx.away_goals is None


def test_get_odds_extracts_match_winner_only() -> None:
    provider = ApiFootballProvider(client=FakeClient(odds=[ODDS_JSON]))
    query = OddsQuery(external_fixture_id=5, home_team="Arsenal", away_team="Chelsea",
                       kickoff=datetime(2024, 5, 1, 18, 0))
    odds = provider.get_odds(query)
    assert len(odds) == 1
    assert odds[0].bookmaker == "Bet365"
    assert (odds[0].odds_home, odds[0].odds_draw, odds[0].odds_away) == (2.10, 3.40, 3.60)


def test_get_advanced_stats_maps_possession_and_xg() -> None:
    """response[0]=home/response[1]=away order - verified live 2026-07-05
    against 5 real finished La Liga fixtures, same convention
    _fixture_from_json already relies on for this provider."""
    provider = ApiFootballProvider(client=FakeClient(stats=STATS_JSON))
    stats = provider.get_advanced_stats(5)
    assert stats is not None
    assert stats.possession_home == 58.0
    assert stats.possession_away == 42.0
    assert stats.xg_home == 1.74
    assert stats.xg_away == 0.81


def test_get_advanced_stats_returns_none_when_incomplete() -> None:
    provider = ApiFootballProvider(client=FakeClient(stats=[STATS_JSON[0]]))
    assert provider.get_advanced_stats(5) is None


def test_get_advanced_stats_missing_stat_type_is_none() -> None:
    stats_json = [
        {"team": {"name": "Arsenal"}, "statistics": []},
        {"team": {"name": "Chelsea"}, "statistics": []},
    ]
    provider = ApiFootballProvider(client=FakeClient(stats=stats_json))
    stats = provider.get_advanced_stats(5)
    assert stats is not None
    assert stats.xg_home is None
    assert stats.possession_home is None
