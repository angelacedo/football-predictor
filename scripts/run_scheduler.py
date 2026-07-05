"""Long-running scheduler process - runs sync/train/predict/validate for
football in-process, on a schedule. The ONE exception to "scripts/ are
one-shot CLI jobs" (see README) - this one never exits.

Usage:
    python scripts/run_scheduler.py
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

import predict_upcoming
import run_backtest
import train_all
from footy.betting.backtest import backtest
from footy.config import football_current_season, get_settings
from footy.data import matches_dataframe, validated_predictions_dataframe
from footy.db import get_engine, session_scope
from footy.ingest.matches import sync_league
from footy.ingest.providers.base import to_naive_utc
from footy.ingest.stats import fetch_stats
from footy.ml.train import train_model
from footy.orm import Match
from footy.predictions.metrics import breakdown_by_league_and_model, pairs_needing_retrain
from footy.predictions.validator import PredictionValidator
from joblog import JobLogBase, record

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("run_scheduler")


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
    football_fetch_stats()
    football_retrain_check()


def football_fetch_stats() -> None:
    """Backfill xG/possession for FINISHED matches missing them. Stats only
    exist post-match (confirmed live 2026-07-05 via API-Football's
    /fixtures/statistics), so this only ever touches FINISHED rows, and only
    ones still missing xg_home - already-populated matches are never
    refetched. Runs right after football_validate, same daily cadence."""
    with session_scope() as session:
        fixture_ids = session.scalars(
            select(Match.api_fixture_id).where(
                Match.status == "FINISHED", Match.xg_home.is_(None)
            )
        ).all()
    if not fixture_ids:
        record("football_fetch_stats", "SUCCESS", "no matches missing stats")
        return

    written, failed = 0, 0
    for fixture_id in fixture_ids:
        try:
            if fetch_stats(fixture_id):
                written += 1
        except Exception:
            failed += 1
            log.exception("Stats fetch failed for fixture %d", fixture_id)
    status = "SUCCESS" if failed == 0 else "ERROR"
    record(
        "football_fetch_stats", status,
        f"{written} written, {failed} failed, {len(fixture_ids)} candidates",
    )


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


def main() -> None:
    JobLogBase.metadata.create_all(get_engine())
    record("scheduler_startup", "SUCCESS", "scheduler process (re)started")

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
    log.info("Scheduler starting - jobs: %s", [j.id for j in scheduler.get_jobs()])
    scheduler.start()


if __name__ == "__main__":
    main()
