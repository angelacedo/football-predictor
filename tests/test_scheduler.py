"""run_scheduler.py: football per-league error isolation, WC sync, retrain check."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

import run_scheduler
from footy.db import session_scope
from footy.orm import Base, Match, Prediction
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
    Base.metadata.create_all(db.get_engine())
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


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


def test_football_fetch_stats_only_targets_finished_matches_missing_xg(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with session_scope() as session:
        session.add(Match(
            api_fixture_id=1, league="La Liga", season=2025, home_team="A", away_team="B",
            kickoff=datetime.now(UTC), status="FINISHED", home_goals=1, away_goals=0,
        ))  # missing stats - should be fetched
        session.add(Match(
            api_fixture_id=2, league="La Liga", season=2025, home_team="C", away_team="D",
            kickoff=datetime.now(UTC), status="FINISHED", home_goals=2, away_goals=2,
            xg_home=1.0, xg_away=1.0, possession_home=50.0, possession_away=50.0,
        ))  # already has stats - must not be refetched
        session.add(Match(
            api_fixture_id=3, league="La Liga", season=2025, home_team="E", away_team="F",
            kickoff=datetime.now(UTC), status="SCHEDULED",
        ))  # not finished yet - must not be fetched

    fetched = []
    monkeypatch.setattr(
        run_scheduler, "fetch_stats", lambda fid: fetched.append(fid) or True
    )
    run_scheduler.football_fetch_stats()

    assert fetched == [1]
    with session_scope() as session:
        row = session.scalar(
            select(JobRun).where(JobRun.job_name == "football_fetch_stats")
        )
    assert row is not None
    assert row.status == "SUCCESS"
    assert row.detail == "1 written, 0 failed, 1 candidates"


def test_football_fetch_stats_no_candidates_is_success(sched_db: None) -> None:
    run_scheduler.football_fetch_stats()
    with session_scope() as session:
        row = session.scalar(
            select(JobRun).where(JobRun.job_name == "football_fetch_stats")
        )
    assert row is not None
    assert row.status == "SUCCESS"
    assert row.detail == "no matches missing stats"


def test_football_fetch_stats_reports_error_status_on_failures(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with session_scope() as session:
        session.add(Match(
            api_fixture_id=1, league="La Liga", season=2025, home_team="A", away_team="B",
            kickoff=datetime.now(UTC), status="FINISHED", home_goals=1, away_goals=0,
        ))

    def _raise(fixture_id: int) -> bool:
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(run_scheduler, "fetch_stats", _raise)
    run_scheduler.football_fetch_stats()

    with session_scope() as session:
        row = session.scalar(
            select(JobRun).where(JobRun.job_name == "football_fetch_stats")
        )
    assert row is not None
    assert row.status == "ERROR"


def test_football_validate_runs_fetch_stats_then_retrain_check(
    sched_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """football_validate must chain into both new/existing calls in order,
    but only when validation itself succeeded."""
    calls = []
    monkeypatch.setattr(
        run_scheduler.PredictionValidator, "validate_finished",
        lambda self: (calls.append("validate") or 0),
    )
    monkeypatch.setattr(
        run_scheduler, "football_fetch_stats", lambda: calls.append("fetch_stats")
    )
    monkeypatch.setattr(
        run_scheduler, "football_retrain_check", lambda: calls.append("retrain_check")
    )
    run_scheduler.football_validate()

    assert calls == ["validate", "fetch_stats", "retrain_check"]
