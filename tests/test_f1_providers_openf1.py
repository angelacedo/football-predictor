"""OpenF1Provider: mocked HTTP JSON -> DTOs (no network)."""

from __future__ import annotations

import pytest

import sports.f1.ingest.providers.openf1 as openf1_mod
from sports.f1.ingest.providers.base import ProviderError
from sports.f1.ingest.providers.openf1 import OpenF1Provider
from tests.conftest import FakeResponse

SESSIONS_JSON = [
    {
        "session_key": 9141, "session_type": "Race", "session_name": "Race",
        "date_start": "2023-07-30T13:00:00+00:00", "date_end": "2023-07-30T15:00:00+00:00",
        "meeting_key": 1216, "circuit_short_name": "Spa-Francorchamps",
        "country_name": "Belgium", "year": 2023, "is_cancelled": False,
    },
    {
        "session_key": 9140, "session_type": "Race", "session_name": "Sprint",
        "date_start": "2023-07-29T15:05:00+00:00", "date_end": "2023-07-29T15:35:00+00:00",
        "meeting_key": 1216, "circuit_short_name": "Spa-Francorchamps",
        "country_name": "Belgium", "year": 2023, "is_cancelled": False,
    },
]

DRIVERS_JSON = [
    {"driver_number": 1, "full_name": "Max VERSTAPPEN", "team_name": "Red Bull Racing"},
    {"driver_number": 11, "full_name": "Sergio PEREZ", "team_name": "Red Bull Racing"},
]

RESULT_JSON = [
    {"position": 1, "driver_number": 1, "points": 25.0, "dnf": False, "dns": False, "dsq": False},
    {"position": None, "driver_number": 11, "points": 0.0, "dnf": True, "dns": False, "dsq": False},
]


def _fake_get(url: str, params: dict, timeout: float) -> FakeResponse:
    if "sessions" in url:
        return FakeResponse(SESSIONS_JSON)
    if "drivers" in url:
        return FakeResponse(DRIVERS_JSON)
    if "session_result" in url:
        return FakeResponse(RESULT_JSON)
    raise AssertionError(f"unexpected url {url}")


@pytest.fixture
def provider() -> OpenF1Provider:
    return OpenF1Provider()


def test_get_sessions_filters_race_from_sprint(
    monkeypatch: pytest.MonkeyPatch, provider: OpenF1Provider
) -> None:
    monkeypatch.setattr(openf1_mod.httpx, "get", _fake_get)
    sessions = provider.get_sessions(2023, "RACE")
    assert len(sessions) == 1
    assert sessions[0].external_session_id == 9141
    assert sessions[0].circuit == "Spa-Francorchamps"
    assert sessions[0].session_type == "RACE"


def test_get_sessions_sprint_type_filters_to_sprint(
    monkeypatch: pytest.MonkeyPatch, provider: OpenF1Provider
) -> None:
    monkeypatch.setattr(openf1_mod.httpx, "get", _fake_get)
    sessions = provider.get_sessions(2023, "SPRINT")
    assert len(sessions) == 1
    assert sessions[0].external_session_id == 9140


def test_get_sessions_unknown_type_raises(provider: OpenF1Provider) -> None:
    with pytest.raises(ProviderError, match="Unknown session_type"):
        provider.get_sessions(2023, "NOPE")


def test_get_entries_maps_status_and_team(
    monkeypatch: pytest.MonkeyPatch, provider: OpenF1Provider
) -> None:
    monkeypatch.setattr(openf1_mod.httpx, "get", _fake_get)
    entries = provider.get_entries(9141)
    assert len(entries) == 2
    winner = next(e for e in entries if e.driver_number == 1)
    assert winner.driver_name == "Max VERSTAPPEN"
    assert winner.team == "Red Bull Racing"
    assert winner.finish_position == 1
    assert winner.status == "FINISHED"

    dnf = next(e for e in entries if e.driver_number == 11)
    assert dnf.status == "DNF"
    assert dnf.finish_position is None
