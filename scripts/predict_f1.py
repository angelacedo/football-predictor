"""Predict all SCHEDULED F1 sessions and record the predictions.

Idempotent: unique(session_id, driver_number, model_name) dup-guards re-runs.

Usage:
    python scripts/predict_f1.py
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from footy.db import session_scope
from sports.f1.data import entries_dataframe
from sports.f1.ml.predict import predict_session
from sports.f1.ml.train import MODEL_NAME
from sports.f1.orm import F1Prediction, F1Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("sports.f1.predict_f1")


def main() -> None:
    with session_scope() as session:
        scheduled = session.scalars(
            select(F1Session.id).where(F1Session.status == "SCHEDULED")
        ).all()

    if not scheduled:
        log.info("No scheduled F1 sessions to predict.")
        return

    df = entries_dataframe()
    for session_id in scheduled:
        if not (df["session_id"] == session_id).any():
            # OpenF1 only has a real driver lineup once a session actually
            # starts/finishes - sync_season() only fetches entries for
            # finished sessions by design (see its docstring), so a SCHEDULED
            # session has zero f1_entries rows until then. Root cause, not a
            # workaround: skip cleanly instead of feeding predict_session() an
            # empty frame (crashes deep inside sklearn otherwise).
            log.warning("No entries synced yet for session %d, skipping", session_id)
            continue
        ranking = predict_session(df, session_id, model_name=MODEL_NAME)
        with session_scope() as session:
            for driver_number, predicted_position in ranking.predicted_position.items():
                try:
                    with session.begin_nested():
                        session.add(
                            F1Prediction(
                                session_id=session_id,
                                driver_number=driver_number,
                                model_name=MODEL_NAME,
                                predicted_position=Decimal(str(round(predicted_position, 3))),
                            )
                        )
                except IntegrityError:
                    log.info(
                        "Prediction already recorded: session=%d driver=%d model=%s",
                        session_id, driver_number, MODEL_NAME,
                    )


if __name__ == "__main__":
    main()
