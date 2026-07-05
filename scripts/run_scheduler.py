"""Long-running scheduler process - runs sync/train/predict/validate for both
football and F1 in-process, on a schedule. The ONE exception to "scripts/ are
one-shot CLI jobs" (see README) - this one never exits.

Usage:
    python scripts/run_scheduler.py
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

import predict_f1
import predict_upcoming
import run_backtest
import train_all
from footy.betting.backtest import backtest
from footy.config import f1_current_season, football_current_season, get_settings
from footy.db import get_engine, session_scope
from footy.ingest.matches import sync_league
from footy.predictions.validator import PredictionValidator
from joblog import JobLogBase, record
from sports.f1.ingest.sessions import sync_season as f1_sync_season
from sports.f1.orm import F1Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("run_scheduler")

_F1_BASELINE = timedelta(hours=24)

_last_f1_run: datetime | None = None


def football_sync_predict() -> None:
    """Sync every configured league (both the nominal current season and the
    next one - during the Jun-Aug gap the "current" season by the Aug-cutover
    rule has no more fixtures to sync, while the upcoming season's calendar
    is often already published; syncing both is cheap and avoids needing the
    cutover rule to be exactly right for this job to work correctly). One
    misconfigured league's missing league_id must never block the rest."""
    settings = get_settings()
    season = football_current_season()
    for league in settings.leagues:
        league_id = settings.league_ids.get(league)
        if league_id is None:
            record("football_sync", "ERROR", f"{league}: no league_id configured, skipped")
            log.error("No league_id configured for '%s', skipping", league)
            continue
        try:
            for s in (season, season + 1):
                sync_league(league_id, s)
            record("football_sync", "SUCCESS", f"{league}: seasons {season},{season + 1}")
        except Exception as exc:
            record("football_sync", "ERROR", f"{league}: {exc}")
            log.exception("Football sync failed for '%s'", league)

    try:
        predict_upcoming.main()
        record("football_predict", "SUCCESS")
    except Exception as exc:
        record("football_predict", "ERROR", str(exc))
        log.exception("football_predict failed")


def football_validate() -> None:
    try:
        n = PredictionValidator().validate_finished()
        record("football_validate", "SUCCESS", f"{n} validated")
    except Exception as exc:
        record("football_validate", "ERROR", str(exc))
        log.exception("football_validate failed")


def football_train() -> None:
    try:
        code = train_all.main()
        record("football_train", "SUCCESS" if code == 0 else "ERROR",
               "see container logs for per-(league,algorithm) results")
    except Exception as exc:
        record("football_train", "ERROR", str(exc))
        log.exception("football_train failed")


def football_backtest() -> None:
    try:
        bets = run_backtest.build_settled_bets()
        report = backtest(bets)
        record("football_backtest", "SUCCESS", repr(report))
    except Exception as exc:
        record("football_backtest", "ERROR", str(exc))
        log.exception("football_backtest failed")


def _f1_interval(next_start: datetime | None, now: datetime) -> timedelta:
    """Ramp-up tiers, explicit (not a lookup table - a table shape here
    previously got the >72h case backwards, caught by test_scheduler.py):
    >72h out = baseline; 6-72h = 2h; 0-6h = 1h; started <4h ago = 15min;
    anything else (no upcoming session, or started >4h ago) = baseline."""
    if next_start is None:
        return _F1_BASELINE
    hours_until = (next_start - now).total_seconds() / 3600
    if hours_until > 72:
        return _F1_BASELINE
    if hours_until > 6:
        return timedelta(hours=2)
    if hours_until > 0:
        return timedelta(hours=1)
    if hours_until > -4:
        return timedelta(minutes=15)
    return _F1_BASELINE


def f1_tick() -> None:
    """Runs every 15 min; self-throttles to the ramp-up interval computed
    from the nearest SCHEDULED session, rather than reprogramming APScheduler
    jobs dynamically. Never auto-seeds entries from Qualifying - that stays a
    manual, explicit, per-incident judgment call (see 2026-07-05 incident)."""
    global _last_f1_run
    now = datetime.now(UTC)
    with session_scope() as session:
        next_session = session.scalar(
            select(F1Session)
            .where(F1Session.status == "SCHEDULED")
            .order_by(F1Session.start_time)
        )
    next_start = next_session.start_time.replace(tzinfo=UTC) if next_session else None
    interval = _f1_interval(next_start, now)

    if _last_f1_run is not None and now - _last_f1_run < interval:
        return

    try:
        for session_type in ("RACE", "QUALIFYING", "SPRINT"):
            f1_sync_season(f1_current_season(), session_type=session_type)
        predict_f1.main()
        record("f1_tick", "SUCCESS", f"interval={interval}")
    except Exception as exc:
        record("f1_tick", "ERROR", str(exc))
        log.exception("f1_tick failed")
    finally:
        _last_f1_run = now


def main() -> None:
    JobLogBase.metadata.create_all(get_engine())
    record("scheduler_startup", "SUCCESS", "scheduler process (re)started, last_f1_run reset")

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        football_sync_predict, "cron", hour=4, minute=0, id="football_sync_predict"
    )
    scheduler.add_job(football_validate, "cron", hour=6, minute=0, id="football_validate")
    scheduler.add_job(
        football_train, "cron", day_of_week="mon", hour=5, minute=0, id="football_train"
    )
    scheduler.add_job(
        football_backtest, "cron", day_of_week="mon", hour=6, minute=0, id="football_backtest"
    )
    scheduler.add_job(
        f1_tick, "interval", minutes=15, id="f1_tick", next_run_time=datetime.now()
    )
    log.info("Scheduler starting - jobs: %s", [j.id for j in scheduler.get_jobs()])
    scheduler.start()


if __name__ == "__main__":
    main()
