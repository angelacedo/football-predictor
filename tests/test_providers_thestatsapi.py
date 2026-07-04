"""TheStatsApiProvider: mocked HTTP JSON -> AdvancedStatsDTO (no network)."""

from __future__ import annotations

from datetime import datetime

import pytest

import footy.ingest.providers.thestatsapi as thestatsapi_mod
from footy.ingest.providers.base import ProviderError
from footy.ingest.providers.thestatsapi import TheStatsApiProvider
from footy.ingest.schemas import OddsQuery
from tests.conftest import FakeResponse

STATS_JSON = {
    "fixture_id": 5001,
    "home": {"xg": 1.74, "possession": 54.2},
    "away": {"xg": 0.81, "possession": 45.8},
}


@pytest.fixture
def provider() -> TheStatsApiProvider:
    return TheStatsApiProvider(api_key="test-key")


def test_get_advanced_stats(
    monkeypatch: pytest.MonkeyPatch, provider: TheStatsApiProvider
) -> None:
    monkeypatch.setattr(
        thestatsapi_mod.httpx, "get", lambda *a, **k: FakeResponse(STATS_JSON)
    )
    stats = provider.get_advanced_stats(5001)
    assert stats is not None
    assert stats.xg_home == pytest.approx(1.74)
    assert stats.xg_away == pytest.approx(0.81)
    assert stats.possession_home == pytest.approx(54.2)
    assert stats.possession_away == pytest.approx(45.8)


def test_get_advanced_stats_404_returns_none(
    monkeypatch: pytest.MonkeyPatch, provider: TheStatsApiProvider
) -> None:
    monkeypatch.setattr(
        thestatsapi_mod.httpx, "get", lambda *a, **k: FakeResponse(None, status_code=404)
    )
    assert provider.get_advanced_stats(9999) is None


def test_odds_unsupported(provider: TheStatsApiProvider) -> None:
    query = OddsQuery(external_fixture_id=1, home_team="A", away_team="B",
                       kickoff=datetime(2024, 1, 1))
    with pytest.raises(ProviderError):
        provider.get_odds(query)
