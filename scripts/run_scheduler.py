"""Long-running scheduler process - runs sync/train/predict/validate for both
football and F1 in-process, on a schedule. The ONE exception to "scripts/ are
one-shot CLI jobs" (see README) - this one never exits.

Usage:
    python scripts/run_scheduler.py
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TypeGuard

import httpx
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

import predict_f1
import predict_upcoming
import run_backtest
import train_all
from footy.betting.backtest import backtest
from footy.config import f1_current_season, football_current_season, get_settings
from footy.data import matches_dataframe, validated_predictions_dataframe
from footy.db import get_engine, session_scope
from footy.ingest.matches import sync_league
from footy.ingest.providers.base import to_naive_utc
from footy.ml.train import train_model
from footy.predictions.metrics import breakdown_by_league_and_model, pairs_needing_retrain
from footy.predictions.validator import PredictionValidator
from joblog import JobLogBase, record
from sports.f1.ingest.sessions import sync_season as f1_sync_season
from sports.f1.orm import F1Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("run_scheduler")

_F1_BASELINE = timedelta(hours=24)
_LOCKOUT_MESSAGE = "Live F1 session in progress"

# Rough per-type duration for the "has this lockout gone on suspiciously
# long" check - OpenF1 documents live-window = 30min before start to 30min
# after end (github.com/br-g/openf1#280 shows it can drift past that once in
# a while, hence "unusually long" is a heads-up, not a hard alarm).
_ASSUMED_SESSION_DURATION = {
    "RACE": timedelta(hours=2),
    "QUALIFYING": timedelta(hours=1),
    "SPRINT": timedelta(hours=1),
}
_POST_SESSION_BUFFER = timedelta(minutes=30)

_last_f1_run: datetime | None = None
_lockout_streak: dict[int, int] = {}


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

    # World Cup 2026: kept OUT of settings.leagues on purpose (that list drives
    # train_all, which must not train a WC-specific model on ~4 games). We only
    # want its fixtures ingested so the club-trained model can predict them
    # (isolated block - a WC failure must never break club sync or predict).
    # WC season = calendar year in API-Football numbering, not the Aug-cutover
    # club season. Predictions are out-of-distribution - see predictions.html.
    wc_id = settings.league_ids.get("World Cup")
    if wc_id is not None:
        try:
            n = sync_league(wc_id, datetime.now(UTC).year)
            record("world_cup_sync", "SUCCESS", f"{n} fixture(s)")
        except Exception as exc:
            record("world_cup_sync", "ERROR", str(exc))
            log.exception("World Cup sync failed")

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
        return
    football_retrain_check()


_RETRAIN_CURRENT_WINDOW = timedelta(days=7)
_RETRAIN_BASELINE_WINDOW = timedelta(days=90)


def football_retrain_check() -> None:
    """Runs right after football_validate: compares each (league, algorithm)
    pair's brier over the last 7 days against its own prior 90-day baseline,
    and retrains immediately on real degradation instead of waiting for
    Monday's scheduled football_train.

    Deliberately relative, not an absolute quality bar - a real walk-forward
    backtest on this repo's live 2025 La Liga data showed brier ~0.65-0.72
    even for a working model (barely better than 0.667 uniform-guess; the
    feature set is weak, not broken). See pairs_needing_retrain's docstring.

    World Cup is excluded by construction: it's never in settings.leagues, so
    train_all never trains it and no artifact exists to retrain.
    """
    settings = get_settings()
    now = to_naive_utc(datetime.now(UTC))
    df = validated_predictions_dataframe()
    df = df[df["league"].isin(settings.leagues)]
    if df.empty:
        record("football_retrain_check", "SKIPPED", "no validated predictions for a trained league")
        return

    current = df[df["kickoff"] >= now - _RETRAIN_CURRENT_WINDOW]
    baseline = df[
        (df["kickoff"] >= now - _RETRAIN_BASELINE_WINDOW)
        & (df["kickoff"] < now - _RETRAIN_CURRENT_WINDOW)
    ]
    pairs = pairs_needing_retrain(
        breakdown_by_league_and_model(current), breakdown_by_league_and_model(baseline)
    )
    if not pairs:
        record("football_retrain_check", "SUCCESS", "no degraded pairs")
        return

    for pair in pairs:
        league, model_name = str(pair["league"]), str(pair["model_name"])
        try:
            train_model(matches_dataframe(league), model_name)
            record(
                "football_retrain_check", "SUCCESS",
                f"retrained {model_name}: brier {pair['baseline_brier']:.3f} "
                f"-> {pair['current_brier']:.3f}",
            )
        except Exception as exc:
            record("football_retrain_check", "ERROR", f"{model_name}: {exc}")
            log.exception("Retrain failed for '%s'", model_name)


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


def _expected_session_end(session: F1Session) -> datetime:
    duration = _ASSUMED_SESSION_DURATION.get(session.session_type, timedelta(hours=2))
    start = session.start_time.replace(tzinfo=UTC)
    return start + duration + _POST_SESSION_BUFFER


def _is_lockout(exc: Exception) -> TypeGuard[httpx.HTTPStatusError]:
    """True only for OpenF1's documented live-session lockout message - not
    a blanket "any 401 is fine". A different 401 (e.g. a bad/rotated key, if
    one is ever added) must still surface as a real ERROR, not get silently
    swallowed by this."""
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code == 401
        and _LOCKOUT_MESSAGE in exc.response.text
    )


def f1_tick() -> None:
    """Runs every 15 min; self-throttles to the ramp-up interval computed
    from the nearest SCHEDULED session, rather than reprogramming APScheduler
    jobs dynamically. Never auto-seeds entries from Qualifying - that stays a
    manual, explicit, per-incident judgment call (see 2026-07-05 incident).

    OpenF1 blocks its ENTIRE API (confirmed live 2026-07-05: even historical
    queries, even unrelated session types) for 30min before + 30min after any
    live session, any type - not just Race. That's SKIPPED, not ERROR: it's
    expected, not a failure. 3+ consecutive lockouts for the same session
    past its expected end escalate the detail text (not the status - still
    SKIPPED) so it's visible on /status without doing the arithmetic by hand.
    """
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
        if next_session is not None:
            _lockout_streak.pop(next_session.id, None)
    except Exception as exc:
        if _is_lockout(exc):
            detail = f"LOCKOUT: {exc.response.text.strip()}"
            if next_session is not None:
                streak = _lockout_streak.get(next_session.id, 0) + 1
                _lockout_streak[next_session.id] = streak
                expected_end = _expected_session_end(next_session)
                if streak >= 3 and now > expected_end:
                    minutes_over = int((now - expected_end).total_seconds() / 60)
                    detail = f"{detail} (unusually long - session ended ~{minutes_over}min ago)"
            record("f1_tick", "SKIPPED", detail)
        else:
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
