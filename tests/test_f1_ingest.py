"""F1 ingest: upsert_sessions/upsert_entries/sync_season against a real DB (SQLite), no network."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest

from sports.f1.ingest.schemas import EntryDTO, SessionDTO
from sports.f1.ingest.sessions import sync_season, upsert_entries, upsert_sessions
from sports.f1.orm import F1Base, F1Entry, F1Session


@pytest.fixture
def f1_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Same lru_cache-triple-clear footgun as tests/test_web.py - get_engine()/
    _session_factory() are process-wide cached and must be cleared alongside
    get_settings() whenever DATABASE_URL changes between tests."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/f1_test.db")
    import footy.config as config
    import footy.db as db

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()

    F1Base.metadata.create_all(db.get_engine())
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


def _session_dto(external_id: int = 9141, finished: bool = True) -> SessionDTO:
    return SessionDTO(
        external_session_id=external_id, season=2024, round=1, circuit="Bahrain",
        session_type="RACE", start_time=datetime(2024, 3, 2, 15, 0), finished=finished,
    )


class FakeProvider:
    name = "fake"

    def get_sessions(self, season: int, session_type: str = "RACE") -> list[SessionDTO]:
        return [_session_dto()]

    def get_entries(self, external_session_id: int) -> list[EntryDTO]:
        return [
            EntryDTO(external_session_id=external_session_id, driver_number=1,
                     driver_name="Max Verstappen", team="Red Bull", finish_position=1,
                     status="FINISHED", points=25.0),
            EntryDTO(external_session_id=external_session_id, driver_number=11,
                     driver_name="Sergio Perez", team="Red Bull", finish_position=None,
                     status="DNF", points=0.0),
        ]


def test_upsert_sessions_insert_and_update(f1_db: None) -> None:
    from footy.db import session_scope

    written = upsert_sessions([_session_dto(finished=False)])
    assert written == 1
    with session_scope() as session:
        row = session.query(F1Session).one()
        assert row.status == "SCHEDULED"

    upsert_sessions([_session_dto(finished=True)])
    with session_scope() as session:
        rows = session.query(F1Session).all()
        assert len(rows) == 1  # updated, not duplicated
        assert rows[0].status == "FINISHED"


def test_upsert_entries_requires_synced_session(f1_db: None) -> None:
    written = upsert_entries(9141, [
        EntryDTO(external_session_id=9141, driver_number=1, driver_name="X", team="Y",
                 finish_position=1, status="FINISHED", points=25.0),
    ])
    assert written == 0  # session not synced yet


def test_sync_season_end_to_end_with_fake_provider(f1_db: None) -> None:
    from footy.db import session_scope

    written = sync_season(2024, provider=FakeProvider())
    assert written == 1

    with session_scope() as session:
        entries = session.query(F1Entry).order_by(F1Entry.driver_number).all()
        assert len(entries) == 2
        assert entries[0].finish_position == 1
        assert entries[0].status == "FINISHED"
        assert entries[1].status == "DNF"
        assert entries[1].finish_position is None
