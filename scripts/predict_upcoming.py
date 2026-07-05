"""Predict all SCHEDULED matches and record the predictions.

Idempotent: re-running skips matches already predicted by this model.

Per league, uses the best validated ``train_all``-produced artifact (e.g.
``xgboost_La_Liga``) if it has enough validated history to trust; otherwise
falls back to the single global ``baseline`` model trained across every
league. A league never in ``settings.leagues`` (World Cup, by design - see
``run_scheduler.py``) is never trained by ``train_all``, so no such artifact
file exists on disk for it in practice - the ``FileNotFoundError`` catch below
is what actually guarantees the baseline fallback, not any league-name check
here (``best_model_per_league`` has no awareness of ``settings.leagues`` at
all; it just reads whatever's in ``validated_predictions_dataframe()``).

Usage:
    python scripts/predict_upcoming.py
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from footy.data import matches_dataframe, validated_predictions_dataframe
from footy.db import session_scope
from footy.ml.predict import predict_match
from footy.ml.registry import load_latest
from footy.ml.train import MODEL_NAME
from footy.orm import Match
from footy.predictions.metrics import best_model_per_league, breakdown_by_league_and_model
from footy.predictions.tracker import PredictionTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.predict_upcoming")

MIN_VALIDATED_TO_TRUST = 10


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
    for match_id, league in scheduled:
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
