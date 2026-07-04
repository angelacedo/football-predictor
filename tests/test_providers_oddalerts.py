"""OddAlertsProvider: mocked HTTP JSON -> closing-odds DTOs (no network)."""

from __future__ import annotations

from datetime import datetime

import pytest

import footy.ingest.providers.oddalerts as oddalerts_mod
from footy.ingest.providers.oddalerts import OddAlertsProvider
from footy.ingest.schemas import OddsQuery
from tests.conftest import FakeResponse

HISTORY_JSON = [
    {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "kickoff": "2024-05-01T18:00:00+00:00",
        "closing": [{"bookmaker": "Pinnacle", "home": 2.05, "draw": 3.5, "away": 3.7}],
    }
]


@pytest.fixture
def provider() -> OddAlertsProvider:
    return OddAlertsProvider(api_key="test-key")


def test_get_odds_matches_and_tags_closing(
    monkeypatch: pytest.MonkeyPatch, provider: OddAlertsProvider
) -> None:
    monkeypatch.setattr(oddalerts_mod.httpx, "get", lambda *a, **k: FakeResponse(HISTORY_JSON))
    query = OddsQuery(external_fixture_id=5, home_team="Arsenal", away_team="Chelsea",
                       kickoff=datetime.fromisoformat("2024-05-01T18:00:00+00:00"))
    odds = provider.get_odds(query)
    assert len(odds) == 1
    assert odds[0].is_closing is True
    assert odds[0].bookmaker == "Pinnacle"
    assert (odds[0].odds_home, odds[0].odds_draw, odds[0].odds_away) == (2.05, 3.5, 3.7)


def test_get_odds_no_match(monkeypatch: pytest.MonkeyPatch, provider: OddAlertsProvider) -> None:
    monkeypatch.setattr(oddalerts_mod.httpx, "get", lambda *a, **k: FakeResponse(HISTORY_JSON))
    query = OddsQuery(external_fixture_id=7, home_team="Everton", away_team="Fulham",
                       kickoff=datetime.fromisoformat("2024-05-01T18:00:00+00:00"))
    assert provider.get_odds(query) == []
