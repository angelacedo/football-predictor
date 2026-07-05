"""Provider-agnostic DTOs for F1 ingestion. Mirrors footy.ingest.schemas's pattern."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SessionDTO:
    external_session_id: int
    season: int
    round: int
    circuit: str
    session_type: str  # RACE | QUALIFYING | SPRINT
    start_time: datetime
    finished: bool


@dataclass(frozen=True)
class EntryDTO:
    external_session_id: int
    driver_number: int
    driver_name: str
    team: str
    finish_position: int | None
    status: str  # FINISHED | DNF | DNS | DSQ
    points: float | None
    team_colour: str | None = None  # hex, no '#'
