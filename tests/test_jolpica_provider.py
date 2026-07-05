"""JolpicaProvider: synthetic id scheme (round-trip + collision-freedom) and
mocked HTTP -> DTOs (no network), mirroring test_f1_providers_openf1.py.
"""

from __future__ import annotations

import pytest

import sports.f1.ingest.providers.jolpica as jolpica_mod
from sports.f1.ingest.providers.base import ProviderError
from sports.f1.ingest.providers.jolpica import (
    JolpicaProvider,
    decode_jolpica_session_id,
    jolpica_session_id,
)
from tests.conftest import FakeResponse

SCHEDULE_JSON = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "season": "2014", "round": "1", "raceName": "Australian Grand Prix",
                    "Circuit": {
                        "circuitId": "albert_park",
                        "circuitName": "Albert Park Grand Prix Circuit",
                    },
                    "date": "2014-03-16", "time": "05:00:00Z",
                },
            ]
        }
    }
}

RESULTS_JSON = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "Results": [
                        {
                            "number": "44", "position": "1", "points": "25",
                            "Driver": {
                                "permanentNumber": "44",
                                "givenName": "Lewis",
                                "familyName": "Hamilton",
                            },
                            "Constructor": {"name": "Mercedes"},
                            "status": "Finished",
                        },
                        {
                            "number": "3", "position": "15", "points": "0",
                            "Driver": {
                                "permanentNumber": "3",
                                "givenName": "Daniel",
                                "familyName": "Ricciardo",
                            },
                            "Constructor": {"name": "Red Bull"},
                            "status": "Engine",
                        },
                    ]
                }
            ]
        }
    }
}


@pytest.fixture
def provider() -> JolpicaProvider:
    return JolpicaProvider()


# --- synthetic id scheme ---


@pytest.mark.parametrize(
    ("season", "round_", "session_type"),
    [(2014, 1, "RACE"), (2023, 22, "RACE"), (1950, 1, "QUALIFYING"), (2099, 24, "SPRINT")],
)
def test_id_round_trips(season: int, round_: int, session_type: str) -> None:
    encoded = jolpica_session_id(season, round_, session_type)
    assert encoded < 0
    assert decode_jolpica_session_id(encoded) == (season, round_, session_type)


def test_decode_rejects_non_negative() -> None:
    with pytest.raises(ProviderError, match="not a Jolpica-sourced id"):
        decode_jolpica_session_id(9141)  # a real-looking OpenF1 session_key


def test_ids_never_collide_with_real_openf1_ids() -> None:
    real_openf1_ids = [9141, 9140, 11322, 11326, 1]  # all seen live this session
    encoded = [jolpica_session_id(2023, r, "RACE") for r in range(1, 23)]
    assert all(e < 0 for e in encoded)
    assert not set(encoded) & set(real_openf1_ids)


def test_ids_collision_free_across_seasons_rounds_and_tiers() -> None:
    """Not just 'no collision with today's OpenF1 ids' - the encoding itself
    must be injective across every (season, round, session_type) combo,
    including edge seasons at both ends of the supported range and every tier.
    A 2-digit-looking round in one tier must never land on the same int as a
    different (season, round) in another tier."""
    seasons = [1950, 1999, 2005, 2014, 2023, 2026, 2099]
    rounds = range(1, 25)
    types = ("RACE", "QUALIFYING", "SPRINT")

    encoded = [
        jolpica_session_id(season, round_, session_type)
        for season in seasons
        for round_ in rounds
        for session_type in types
    ]
    assert len(encoded) == len(set(encoded)), "synthetic id scheme produced a collision"

    for season in seasons:
        for round_ in rounds:
            for session_type in types:
                e = jolpica_session_id(season, round_, session_type)
                assert decode_jolpica_session_id(e) == (season, round_, session_type)


def test_unknown_session_type_rejected() -> None:
    with pytest.raises(ProviderError, match="Unknown session_type"):
        jolpica_session_id(2023, 1, "NOPE")


# --- get_sessions / get_entries ---


def _fake_get(url: str, timeout: float) -> FakeResponse:
    if "results.json" in url:
        return FakeResponse(RESULTS_JSON)
    return FakeResponse(SCHEDULE_JSON)


def test_get_sessions_returns_race_with_synthetic_id(
    monkeypatch: pytest.MonkeyPatch, provider: JolpicaProvider
) -> None:
    monkeypatch.setattr(jolpica_mod.httpx, "get", _fake_get)
    sessions = provider.get_sessions(2014, "RACE")
    assert len(sessions) == 1
    assert sessions[0].external_session_id == jolpica_session_id(2014, 1, "RACE")
    assert sessions[0].circuit == "Albert Park Grand Prix Circuit"
    assert sessions[0].finished  # 2014-03-16 is long past


def test_get_sessions_rejects_non_race(provider: JolpicaProvider) -> None:
    with pytest.raises(ProviderError, match="only supports RACE"):
        provider.get_sessions(2014, "QUALIFYING")


def test_get_entries_maps_status_and_permanent_number(
    monkeypatch: pytest.MonkeyPatch, provider: JolpicaProvider
) -> None:
    monkeypatch.setattr(jolpica_mod.httpx, "get", _fake_get)
    session_id = jolpica_session_id(2014, 1, "RACE")
    entries = provider.get_entries(session_id)
    assert len(entries) == 2

    winner = next(e for e in entries if e.driver_number == 44)
    assert winner.driver_name == "Lewis Hamilton"
    assert winner.team == "Mercedes"
    assert winner.finish_position == 1
    assert winner.status == "FINISHED"
    assert winner.team_colour is None

    dnf = next(e for e in entries if e.driver_number == 3)
    assert dnf.status == "DNF"
    assert dnf.finish_position is None
