"""Predict all SCHEDULED matches and record the predictions.

Idempotent: re-running skips matches already predicted by this model.

Per league, uses the best validated ``train_all``-produced artifact (e.g.
``xgboost_La_Liga``) if it has enough validated history to trust; otherwise
falls back to the single global ``baseline`` model trained across every
league. A league never in ``settings.leagues`` is never trained by
``train_all``, so no such artifact file exists on disk for it in practice -
the ``FileNotFoundError`` catch below is what actually guarantees the
baseline fallback, not any league-name check here (``best_model_per_league``
has no awareness of ``settings.leagues`` at all; it just reads whatever's in
``validated_predictions_dataframe()``).

World Cup is the one explicit exception: it gets its own purpose-built
model/features (FIFA ranking + host-nation, see
footy.ml.features_worldcup's docstring for why club-football's rolling-form
features don't transfer) rather than falling back to the club baseline. If
that artifact hasn't been trained yet (scripts/train_world_cup.py, a manual
one-off), World Cup matches fall back to the same baseline as everything
else - never a hard failure.

Usage:
    python scripts/predict_upcoming.py
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from sqlalchemy import delete, select

from footy.data import matches_dataframe, validated_predictions_dataframe
from footy.db import session_scope
from footy.domain import MatchProbs
from footy.ml.features_worldcup import (
    FEATURE_COLUMNS_WORLDCUP,
    compute_feature_frame_worldcup,
    load_rankings,
)
from footy.ml.predict import predict_match
from footy.ml.registry import load_latest
from footy.ml.train import MODEL_NAME
from footy.orm import Match, Prediction
from footy.predictions.metrics import best_model_per_league, breakdown_by_league_and_model
from footy.predictions.tracker import PredictionTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.predict_upcoming")

MIN_VALIDATED_TO_TRUST = 10
WORLD_CUP_LEAGUE = "World Cup"
WORLD_CUP_MODEL_NAME = "baseline_World_Cup"


def _clear_other_model_predictions(match_id: int, keep_model_name: str) -> None:
    """Delete any other model's prediction row for this match.

    Real bug found live (2026-07-06): Prediction only has UNIQUE(match_id,
    model_name), not "one current prediction per match" - when the World Cup
    model went from missing (fallback to "baseline") to trained
    ("baseline_World_Cup"), the dashboard showed BOTH rows side by side for
    the same match, since neither insert was a duplicate of the other. A
    match should show its one current prediction, not accumulate a row per
    model that's ever predicted it.
    """
    with session_scope() as session:
        session.execute(
            delete(Prediction).where(
                Prediction.match_id == match_id, Prediction.model_name != keep_model_name
            )
        )


def _probs_from_worldcup_model(model: Any, features: pd.DataFrame) -> MatchProbs:
    """Same shape as footy.ml.predict._probs_from_model, but reads
    FEATURE_COLUMNS_WORLDCUP - kept separate rather than parameterizing the
    shared one, matching features_worldcup.py's isolation-over-branching call."""
    raw = model.predict_proba(features[list(FEATURE_COLUMNS_WORLDCUP)])[0]
    by_class = dict(zip(model.classes_, raw, strict=True))
    return MatchProbs(
        home=float(by_class.get("HOME", 0.0)),
        draw=float(by_class.get("DRAW", 0.0)),
        away=float(by_class.get("AWAY", 0.0)),
    )


def _zero_out_draw(probs: MatchProbs) -> MatchProbs:
    """A knockout match always has a real winner (ET/penalties decide any
    tie) - a draw is structurally impossible, regardless of what residual
    probability the model assigns it (see features_worldcup.py's module
    docstring: the training-label fix alone doesn't guarantee this, since a
    classifier fit on both group and knockout rows can still learn some
    nonzero draw weight). Redistribute proportionally rather than dropping
    the model's home/away split."""
    total = probs.home + probs.away
    if total <= 0:
        return MatchProbs(home=0.5, draw=0.0, away=0.5)
    return MatchProbs(home=probs.home / total, draw=0.0, away=probs.away / total)


def main() -> None:
    with session_scope() as session:
        scheduled = session.execute(
            select(Match.id, Match.league).where(Match.status == "SCHEDULED")
        ).all()

    if not scheduled:
        log.info("No scheduled matches to predict.")
        return

    rows = breakdown_by_league_and_model(validated_predictions_dataframe())
    best_by_league = best_model_per_league(rows, min_n=MIN_VALIDATED_TO_TRUST)

    df = matches_dataframe()
    tracker = PredictionTracker()
    models: dict[str, object] = {MODEL_NAME: load_latest(MODEL_NAME)}

    wc_model: Any | None = None
    wc_feats: pd.DataFrame | None = None
    if any(league == WORLD_CUP_LEAGUE for _match_id, league in scheduled):
        try:
            wc_model = load_latest(WORLD_CUP_MODEL_NAME)
            wc_feats = compute_feature_frame_worldcup(
                matches_dataframe(WORLD_CUP_LEAGUE), load_rankings()
            )
        except FileNotFoundError:
            log.warning(
                "No '%s' artifact yet (run scripts/train_world_cup.py) - "
                "World Cup matches fall back to baseline", WORLD_CUP_MODEL_NAME,
            )

    for match_id, league in scheduled:
        if league == WORLD_CUP_LEAGUE and wc_model is not None and wc_feats is not None:
            probs = _probs_from_worldcup_model(wc_model, wc_feats.loc[[match_id]])
            if wc_feats.loc[match_id, "is_knockout"] == 1.0:
                probs = _zero_out_draw(probs)
            _clear_other_model_predictions(match_id, WORLD_CUP_MODEL_NAME)
            tracker.record(match_id, WORLD_CUP_MODEL_NAME, probs)
            continue

        model_name = best_by_league.get(league, MODEL_NAME)
        if model_name not in models:
            try:
                models[model_name] = load_latest(model_name)
            except FileNotFoundError:
                log.warning("No artifact for '%s' despite validated history - using baseline",
                            model_name)
                model_name = MODEL_NAME
        probs = predict_match(df, match_id, model=models[model_name], model_name=model_name)
        tracker.record(match_id, model_name, probs)


if __name__ == "__main__":
    main()
