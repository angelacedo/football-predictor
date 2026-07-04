"""Record pre-match predictions, guarding against duplicates.

Example:
    >>> tracker = PredictionTracker()  # doctest: +SKIP
    >>> tracker.record(1, "baseline", MatchProbs(.6, .25, .15))  # doctest: +SKIP
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from footy.db import session_scope
from footy.ml.predict import MatchProbs
from footy.orm import Prediction

log = logging.getLogger("footy.predictions.tracker")


def _dec4(value: float) -> Decimal:
    return Decimal(str(round(value, 4)))


class PredictionTracker:
    """Persist model predictions, one per (match, model).

    The DB carries a ``UNIQUE(match_id, model_name)`` constraint; a duplicate
    ``record`` is logged and skipped rather than raised, so re-running a prediction
    job is idempotent.
    """

    def record(
        self,
        match_id: int,
        model_name: str,
        probs: MatchProbs,
        predicted_score_home: int | None = None,
        predicted_score_away: int | None = None,
    ) -> int | None:
        """Insert a prediction. Returns its id, or None if a duplicate was skipped."""
        prediction = Prediction(
            match_id=match_id,
            model_name=model_name,
            prob_home_win=_dec4(probs.home),
            prob_draw=_dec4(probs.draw),
            prob_away_win=_dec4(probs.away),
            predicted_score_home=predicted_score_home,
            predicted_score_away=predicted_score_away,
            confidence_score=_dec4(probs.confidence),
        )
        try:
            with session_scope() as session:
                session.add(prediction)
                session.flush()
                new_id = prediction.id
            log.info("Recorded prediction %d for match=%d model=%s", new_id, match_id, model_name)
            return new_id
        except IntegrityError:
            log.warning(
                "Duplicate prediction for match=%d model=%s — skipped", match_id, model_name
            )
            return None

    def __repr__(self) -> str:
        return "<PredictionTracker>"
