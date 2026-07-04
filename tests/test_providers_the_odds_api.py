"""TheOddsApiProvider: mocked HTTP JSON -> DTOs, matched by team+kickoff (no network)."""

from __future__ import annotations

from datetime import datetime

import pytest

import footy.ingest.providers.the_odds_api as odds_api_mod
from footy.ingest.providers.the_odds_api import TheOddsApiProvider
from footy.ingest.schemas import OddsQuery
from tests.conftest import FakeResponse

EVENTS_JSON = [
    {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "commence_time": "2024-05-01T18:00:00Z",
        "bookmakers": [
            {
                "key": "bet365",
                "title": "Bet365",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.1},
                            {"name": "Draw", "price": 3.4},
                            {"name": "Chelsea", "price": 3.6},
                        ],
                    }
                ],
            }
        ],
    },
    {
        "home_team": "Liverpool",
        "away_team": "Everton",
        "commence_time": "2024-05-01T15:00:00Z",
        "bookmakers": [],
    },
]


@pytest.fixture
def provider() -> TheOddsApiProvider:
    return TheOddsApiProvider(api_key="test-key")


def test_get_odds_matches_by_team_and_kickoff(
    monkeypatch: pytest.MonkeyPatch, provider: TheOddsApiProvider
) -> None:
    monkeypatch.setattr(odds_api_mod.httpx, "get", lambda *a, **k: FakeResponse(EVENTS_JSON))
    query = OddsQuery(external_fixture_id=5, home_team="Arsenal", away_team="Chelsea",
                       kickoff=datetime.fromisoformat("2024-05-01T18:00:00+00:00"))
    odds = provider.get_odds(query)
    assert len(odds) == 1
    assert odds[0].bookmaker == "Bet365"
    assert (odds[0].odds_home, odds[0].odds_draw, odds[0].odds_away) == (2.1, 3.4, 3.6)
    assert odds[0].external_fixture_id == 5


def test_get_odds_no_match_returns_empty(
    monkeypatch: pytest.MonkeyPatch, provider: TheOddsApiProvider
) -> None:
    monkeypatch.setattr(odds_api_mod.httpx, "get", lambda *a, **k: FakeResponse(EVENTS_JSON))
    query = OddsQuery(external_fixture_id=99, home_team="Man City", away_team="Spurs",
                       kickoff=datetime.fromisoformat("2024-05-01T18:00:00+00:00"))
    assert provider.get_odds(query) == []


def test_kickoff_outside_tolerance_no_match(
    monkeypatch: pytest.MonkeyPatch, provider: TheOddsApiProvider
) -> None:
    monkeypatch.setattr(odds_api_mod.httpx, "get", lambda *a, **k: FakeResponse(EVENTS_JSON))
    # Arsenal vs Chelsea event is at 18:00; ask for a kickoff 5 hours away (> 2h tolerance).
    query = OddsQuery(external_fixture_id=5, home_team="Arsenal", away_team="Chelsea",
                       kickoff=datetime.fromisoformat("2024-05-01T23:30:00+00:00"))
    assert provider.get_odds(query) == []
