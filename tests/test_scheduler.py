"""run_scheduler.py: F1 ramp-up tier logic, football per-league error isolation."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

import run_scheduler
from joblog import JobLogBase, JobRun


@pytest.fixture
def sched_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/scheduler_test.db")
    import footy.config as config
    import footy.db as db

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()

    JobLogBase.metadata.create_all(db.get_engine())
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


@pytest.mark.parametrize(
    ("hours_until", "expected"),
    [
        (200, timedelta(hours=24)),    # far out -> baseline
        (73, timedelta(hours=24)),     # just over 72h -> still baseline
        (72, timedelta(hours=2)),      # exactly at the 72h boundary -> ramped
        (24, timedelta(hours=2)),      # within the quali/sprint window
        (6, timedelta(hours=1)),       # at the 6h boundary -> tighter tier
        (3, timedelta(hours=1)),
        (0.5, timedelta(hours=1)),     # still not started - 1h tier, not 15min yet
        (-1, timedelta(minutes=15)),   # started 1h ago, still trying
        (-5, timedelta(hours=24)),     # started >4h ago -> back to baseline
    ],
)
def test_f1_interval_tiers(hours_until: float, expected: timedelta) -> None:
    now = datetime(2026, 7, 5, 13, 0, tzinfo=UTC)
    next_start = now + timedelta(hours=hours_until)
    assert run_scheduler._f1_interval(next_start, now) == expected


def test_f1_interval_no_upcoming_session_is_baseline() -> None:
    now = datetime(2026, 7, 5, 13, 0, tzinfo=UTC)
    assert run_scheduler._f1_interval(None, now) == timedelta(hours=24)


def test_football_sync_predict_missing_league_id_logs_error_and_continues(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One league with no league_id must not block the rest, per the incident review."""
    from footy.db import session_scope

    monkeypatch.setenv("LEAGUES", "La Liga,Fantasyland FC")
    monkeypatch.setenv("LEAGUE_IDS", "La Liga:140")
    import footy.config as config
    config.get_settings.cache_clear()

    synced = []
    monkeypatch.setattr(
        run_scheduler, "sync_league", lambda lid, season: synced.append((lid, season))
    )
    monkeypatch.setattr(run_scheduler.predict_upcoming, "main", lambda: None)

    run_scheduler.football_sync_predict()

    with session_scope() as session:
        rows = session.query(JobRun).filter(JobRun.job_name == "football_sync").all()
    detail_by_status = {r.status: r.detail for r in rows}
    assert "Fantasyland FC" in detail_by_status.get("ERROR", "")
    assert "La Liga" in detail_by_status.get("SUCCESS", "")
    # The configured league still got synced despite the other one being broken.
    assert any(lid == 140 for lid, _season in synced)

    config.get_settings.cache_clear()
