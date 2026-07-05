"""Upsert F1 sessions/entries, provider-agnostic. Mirrors footy.ingest.matches's pattern.

Reuses footy.db.session_scope directly (same Postgres instance, confirmed - no
separate DB for F1), but writes only to F1's own f1_-prefixed tables.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from footy.db import session_scope
from sports.f1.ingest.providers.base import F1Provider
from sports.f1.ingest.providers.registry import build_provider
from sports.f1.ingest.schemas import EntryDTO, SessionDTO
from sports.f1.orm import F1Entry, F1Session

log = logging.getLogger("sports.f1.ingest.sessions")

DEFAULT_PROVIDER = "openf1"


def upsert_sessions(sessions: list[SessionDTO]) -> int:
    """Insert new sessions or update existing ones (keyed by external_session_id)."""
    written = 0
    with session_scope() as session:
        for sx in sessions:
            existing = session.scalar(
                select(F1Session).where(F1Session.external_session_id == sx.external_session_id)
            )
            values = {
                "external_session_id": sx.external_session_id,
                "season": sx.season,
                "round": sx.round,
                "circuit": sx.circuit,
                "session_type": sx.session_type,
                "start_time": sx.start_time,
                "status": "FINISHED" if sx.finished else "SCHEDULED",
            }
            if existing is None:
                session.add(F1Session(**values))
            else:
                for key, val in values.items():
                    setattr(existing, key, val)
            written += 1
    log.info("Upserted %d F1 session(s)", written)
    return written


def upsert_entries(external_session_id: int, entries: list[EntryDTO]) -> int:
    """Insert new entries or update existing ones for one session."""
    written = 0
    with session_scope() as session:
        f1_session = session.scalar(
            select(F1Session).where(F1Session.external_session_id == external_session_id)
        )
        if f1_session is None:
            log.warning("Session %d not synced yet - run sync_season first", external_session_id)
            return 0
        for en in entries:
            existing = session.scalar(
                select(F1Entry).where(
                    F1Entry.session_id == f1_session.id,
                    F1Entry.driver_number == en.driver_number,
                )
            )
            values = {
                "session_id": f1_session.id,
                "driver_number": en.driver_number,
                "driver_name": en.driver_name,
                "team": en.team,
                "finish_position": en.finish_position,
                "status": en.status,
                "points": en.points,
                "team_colour": en.team_colour,
            }
            if existing is None:
                session.add(F1Entry(**values))
            else:
                for key, val in values.items():
                    setattr(existing, key, val)
            written += 1
    log.info("Upserted %d F1 entr(y/ies) for session %d", written, external_session_id)
    return written


def sync_season(season: int, session_type: str = "RACE", provider: F1Provider | None = None) -> int:
    """Fetch all sessions + entries for a season, upsert them.

    Args:
        season: Year, e.g. 2024.
        session_type: RACE | QUALIFYING | SPRINT.
        provider: Defaults to OpenF1.

    Returns:
        Number of session rows written.
    """
    active = provider or build_provider(DEFAULT_PROVIDER)
    sessions = active.get_sessions(season, session_type)
    written = upsert_sessions(sessions)
    for sx in sessions:
        if sx.finished:
            entries = active.get_entries(sx.external_session_id)
            upsert_entries(sx.external_session_id, entries)
    return written
