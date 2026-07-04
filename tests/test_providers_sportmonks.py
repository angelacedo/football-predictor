"""SportmonksProvider: mocked HTTP JSON -> DTOs (no network)."""

from __future__ import annotations

import pytest

import footy.ingest.providers.sportmonks as sportmonks_mod
from footy.ingest.providers.sportmonks import SportmonksProvider
from tests.conftest import FakeResponse

FIXTURE_JSON = {
    "id": 5001,
    "league": {"name": "EPL"},
    "season": {"id": 2024},
    "starting_at": "2024-05-01T18:00:00+00:00",
    "state": "FT",
    "participants": [
        {"name": "Arsenal", "meta": {"location": "home"}},
        {"name": "Chelsea", "meta": {"location": "away"}},
    ],
    "scores": {"home": 2, "away": 2},
}

STATS_JSON = {
    "id": 5001,
    "statistics": [
        {"type": {"code": "expected-goals"}, "location": "home", "data": {"value": 1.83}},
        {"type": {"code": "expected-goals"}, "location": "away", "data": {"value": 0.92}},
        {"type": {"code": "ball-possession"}, "location": "home", "data": {"value": 61.5}},
        {"type": {"code": "ball-possession"}, "location": "away", "data": {"value": 38.5}},
    ],
}


@pytest.fixture
def provider() -> SportmonksProvider:
    return SportmonksProvider(api_key="test-key")


def test_get_fixtures(monkeypatch: pytest.MonkeyPatch, provider: SportmonksProvider) -> None:
    monkeypatch.setattr(
        sportmonks_mod.httpx, "get",
        lambda *a, **k: FakeResponse({"data": [FIXTURE_JSON]}),
    )
    fixtures = provider.get_fixtures(league_id=8, season=2024)
    assert len(fixtures) == 1
    fx = fixtures[0]
    assert fx.home_team == "Arsenal" and fx.away_team == "Chelsea"
    assert fx.finished is True
    assert fx.home_goals == 2 and fx.away_goals == 2


def test_get_advanced_stats(monkeypatch: pytest.MonkeyPatch, provider: SportmonksProvider) -> None:
    monkeypatch.setattr(
        sportmonks_mod.httpx, "get",
        lambda *a, **k: FakeResponse({"data": STATS_JSON}),
    )
    stats = provider.get_advanced_stats(5001)
    assert stats is not None
    assert stats.xg_home == pytest.approx(1.83)
    assert stats.xg_away == pytest.approx(0.92)
    assert stats.possession_home == pytest.approx(61.5)


def test_get_advanced_stats_missing(
    monkeypatch: pytest.MonkeyPatch, provider: SportmonksProvider
) -> None:
    monkeypatch.setattr(
        sportmonks_mod.httpx, "get",
        lambda *a, **k: FakeResponse({"data": None}),
    )
    assert provider.get_advanced_stats(9999) is None


def test_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPORTMONKS_API_KEY", "")
    from footy.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        SportmonksProvider(api_key="")
    get_settings.cache_clear()
