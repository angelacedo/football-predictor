"""Predict all SCHEDULED matches and record the predictions.

Idempotent: re-running skips matches already predicted by this model.

Usage:
    python scripts/predict_upcoming.py
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from footy.data import matches_dataframe
from footy.db import session_scope
from footy.ml.predict import predict_match
from footy.ml.registry import load_latest
from footy.ml.train import MODEL_NAME
from footy.orm import Match
from footy.predictions.tracker import PredictionTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.predict_upcoming")


def main() -> None:
    with session_scope() as session:
        scheduled = session.scalars(
            select(Match.id).where(Match.status == "SCHEDULED")
        ).all()

    if not scheduled:
        log.info("No scheduled matches to predict.")
        return

    df = matches_dataframe()
    model = load_latest(MODEL_NAME)
    tracker = PredictionTracker()
    for match_id in scheduled:
        probs = predict_match(df, match_id, model=model, model_name=MODEL_NAME)
        tracker.record(match_id, MODEL_NAME, probs)


if __name__ == "__main__":
    main()
