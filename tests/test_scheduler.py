"""run_scheduler.py: F1 ramp-up tier logic, football per-league error isolation."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

import run_scheduler
from footy.db import session_scope
from footy.orm import Base, Match, Prediction
from joblog import JobLogBase, JobRun
from sports.f1.orm import F1Base, F1Session


@pytest.fixture
def sched_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/scheduler_test.db")
    import footy.config as config
    import footy.db as db

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()

    JobLogBase.metadata.create_all(db.get_engine())
    F1Base.metadata.create_all(db.get_engine())
    Base.metadata.create_all(db.get_engine())
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


def _lockout_error(
    detail: str = "Live F1 session in progress. Global API access is restricted.",
) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.openf1.org/v1/sessions")
    response = httpx.Response(401, request=request, json={"detail": detail})
    return httpx.HTTPStatusError("401", request=request, response=response)


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


def test_football_sync_predict_syncs_world_cup_isolated_from_club_leagues(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """World Cup (league id 1) must be synced by its own guarded block - kept out
    of LEAGUES (so train_all never touches it) but still ingested for prediction.
    A WC sync failure must not stop club sync or predict."""
    from datetime import UTC, datetime

    from footy.db import session_scope

    monkeypatch.setenv("LEAGUES", "La Liga")
    monkeypatch.setenv("LEAGUE_IDS", "La Liga:140,World Cup:1")
    import footy.config as config
    config.get_settings.cache_clear()

    synced = []
    monkeypatch.setattr(
        run_scheduler, "sync_league", lambda lid, season: synced.append((lid, season)) or 3
    )
    predicted = []
    monkeypatch.setattr(run_scheduler.predict_upcoming, "main", lambda: predicted.append(True))

    run_scheduler.football_sync_predict()

    # WC synced for the calendar year, not the Aug-cutover club season.
    assert (1, datetime.now(UTC).year) in synced
    with session_scope() as session:
        wc = session.query(JobRun).filter(JobRun.job_name == "world_cup_sync").all()
    assert [r.status for r in wc] == ["SUCCESS"]
    # Prediction still ran (WC block sits before predict, can't skip it).
    assert predicted == [True]

    config.get_settings.cache_clear()


def test_is_lockout_matches_exact_message() -> None:
    assert run_scheduler._is_lockout(_lockout_error())


def test_is_lockout_rejects_other_401() -> None:
    """A different 401 (bad/rotated key) must still look like a real ERROR,
    not get silently swallowed just because the status code matches."""
    assert not run_scheduler._is_lockout(_lockout_error(detail="Invalid API key"))


def test_is_lockout_rejects_non_http_status_error() -> None:
    assert not run_scheduler._is_lockout(ValueError("boom"))


def test_f1_tick_logs_skipped_not_error_on_lockout(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with session_scope() as session:
        session.add(
            F1Session(
                external_session_id=99, season=2026, round=1, circuit="Silverstone",
                session_type="RACE", start_time=datetime.now(UTC) - timedelta(hours=1),
                status="SCHEDULED",
            )
        )

    def _raise(*args: object, **kwargs: object) -> int:
        raise _lockout_error()

    monkeypatch.setattr(run_scheduler, "f1_sync_season", _raise)
    run_scheduler._last_f1_run = None
    run_scheduler.f1_tick()

    with session_scope() as session:
        row = session.scalar(
            select(JobRun).where(JobRun.job_name == "f1_tick").order_by(JobRun.id.desc())
        )
    assert row is not None
    assert row.status == "SKIPPED"
    assert row.detail is not None
    assert row.detail.startswith("LOCKOUT:")


def test_f1_tick_logs_error_on_non_lockout_failure(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*args: object, **kwargs: object) -> int:
        raise RuntimeError("something else broke")

    monkeypatch.setattr(run_scheduler, "f1_sync_season", _raise)
    run_scheduler._last_f1_run = None
    run_scheduler.f1_tick()

    with session_scope() as session:
        row = session.scalar(
            select(JobRun).where(JobRun.job_name == "f1_tick").order_by(JobRun.id.desc())
        )
    assert row is not None
    assert row.status == "ERROR"


def test_f1_tick_escalates_after_three_consecutive_lockouts_past_expected_end(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session ended (by our duration estimate) well over a day ago - if the
    lockout is STILL firing after 3 consecutive ticks, that's the github.com/
    br-g/openf1#280 scenario (lockout outlasting the documented 30min
    post-session window) and must say so, not look like routine business."""
    with session_scope() as session:
        session.add(
            F1Session(
                external_session_id=99, season=2026, round=1, circuit="Silverstone",
                session_type="RACE", start_time=datetime.now(UTC) - timedelta(days=1),
                status="SCHEDULED",
            )
        )

    def _raise(*args: object, **kwargs: object) -> int:
        raise _lockout_error()

    monkeypatch.setattr(run_scheduler, "f1_sync_season", _raise)
    run_scheduler._lockout_streak.clear()

    details = []
    for _ in range(3):
        run_scheduler._last_f1_run = None  # bypass the interval throttle each call
        run_scheduler.f1_tick()
        with session_scope() as session:
            row = session.scalar(
                select(JobRun).where(JobRun.job_name == "f1_tick").order_by(JobRun.id.desc())
            )
            details.append(row.detail if row else None)

    assert details[0] is not None and "unusually long" not in details[0]
    assert details[1] is not None and "unusually long" not in details[1]
    assert details[2] is not None and "unusually long" in details[2]

    run_scheduler._lockout_streak.clear()


def test_f1_tick_streak_resets_on_success(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with session_scope() as session:
        f1_session = F1Session(
            external_session_id=99, season=2026, round=1, circuit="Silverstone",
            session_type="RACE", start_time=datetime.now(UTC) - timedelta(hours=1),
            status="SCHEDULED",
        )
        session.add(f1_session)
        session.flush()
        session_id = f1_session.id

    run_scheduler._lockout_streak[session_id] = 5
    monkeypatch.setattr(run_scheduler, "f1_sync_season", lambda *a, **k: 0)
    monkeypatch.setattr(run_scheduler.predict_f1, "main", lambda: None)
    run_scheduler._last_f1_run = None
    run_scheduler.f1_tick()

    assert session_id not in run_scheduler._lockout_streak


def _add_validated(league: str, model_name: str, n: int, brier: float, days_ago: int) -> None:
    kickoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago)
    with session_scope() as session:
        for i in range(n):
            m = Match(
                api_fixture_id=abs(hash((league, model_name, days_ago, i))) % 1_000_000,
                league=league, season=2025, home_team="X", away_team="Y",
                kickoff=kickoff, status="FINISHED", home_goals=1, away_goals=0,
            )
            session.add(m)
            session.flush()
            session.add(
                Prediction(
                    match_id=m.id, model_name=model_name,
                    prob_home_win=0.5, prob_draw=0.3, prob_away_win=0.2,
                    actual_result="HOME", is_correct=True,
                    brier_score=brier, log_loss=0.5, validated_at=datetime.now(UTC),
                )
            )


def test_football_retrain_check_retrains_on_real_degradation(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_validated("La Liga", "xgboost_La_Liga", n=30, brier=0.65, days_ago=30)
    _add_validated("La Liga", "xgboost_La_Liga", n=8, brier=0.80, days_ago=2)

    calls = []
    monkeypatch.setattr(
        run_scheduler, "train_model", lambda df, model_name: calls.append(model_name)
    )
    run_scheduler.football_retrain_check()

    assert calls == ["xgboost_La_Liga"]
    with session_scope() as session:
        rows = session.query(JobRun).filter(JobRun.job_name == "football_retrain_check").all()
    assert any(r.status == "SUCCESS" and "retrained xgboost_La_Liga" in (r.detail or "")
               for r in rows)


def test_football_retrain_check_ignores_noise_within_margin(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add_validated("La Liga", "xgboost_La_Liga", n=30, brier=0.65, days_ago=30)
    _add_validated("La Liga", "xgboost_La_Liga", n=8, brier=0.66, days_ago=2)

    calls = []
    monkeypatch.setattr(
        run_scheduler, "train_model", lambda df, model_name: calls.append(model_name)
    )
    run_scheduler.football_retrain_check()

    assert calls == []
    with session_scope() as session:
        row = session.scalar(
            select(JobRun).where(JobRun.job_name == "football_retrain_check")
            .order_by(JobRun.id.desc())
        )
    assert row is not None
    assert row.status == "SUCCESS"
    assert row.detail == "no degraded pairs"


def test_football_retrain_check_skips_with_no_validated_predictions(sched_db: None) -> None:
    run_scheduler.football_retrain_check()
    with session_scope() as session:
        row = session.scalar(
            select(JobRun).where(JobRun.job_name == "football_retrain_check")
        )
    assert row is not None
    assert row.status == "SKIPPED"


def test_football_retrain_check_excludes_world_cup(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """World Cup is never in settings.leagues, so even a wildly degraded pair
    under that league name must never trigger a retrain."""
    _add_validated("World Cup", "xgboost_World_Cup", n=30, brier=0.10, days_ago=30)
    _add_validated("World Cup", "xgboost_World_Cup", n=8, brier=0.90, days_ago=2)

    calls = []
    monkeypatch.setattr(
        run_scheduler, "train_model", lambda df, model_name: calls.append(model_name)
    )
    run_scheduler.football_retrain_check()

    assert calls == []
