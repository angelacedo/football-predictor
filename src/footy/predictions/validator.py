"""Validate predictions against real results post-match.

Example:
    >>> PredictionValidator().validate_finished()  # doctest: +SKIP
    3
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from footy.db import session_scope
from footy.domain import result_from_goals
from footy.orm import Match, Prediction
from footy.predictions.metrics import brier_score, log_loss_single, predicted_result

log = logging.getLogger("footy.predictions.validator")


class PredictionValidator:
    """Score every unvalidated prediction whose match has finished."""

    def validate_finished(self) -> int:
        """Validate all pending predictions for finished matches.

        For each: computes Brier score, log loss, the actual 1X2 result and whether
        the argmax prediction was correct, then stamps ``validated_at``.

        Returns:
            Number of predictions validated.
        """
        count = 0
        with session_scope() as session:
            stmt = (
                select(Prediction, Match)
                .join(Match, Prediction.match_id == Match.id)
                .where(Prediction.validated_at.is_(None))
                .where(Match.status == "FINISHED")
                .where(Match.home_goals.is_not(None))
                .where(Match.away_goals.is_not(None))
            )
            for prediction, match in session.execute(stmt).all():
                assert match.home_goals is not None and match.away_goals is not None
                probs = (
                    float(prediction.prob_home_win),
                    float(prediction.prob_draw),
                    float(prediction.prob_away_win),
                )
                actual = result_from_goals(match.home_goals, match.away_goals)

                prediction.actual_score_home = match.home_goals
                prediction.actual_score_away = match.away_goals
                prediction.actual_result = actual
                prediction.brier_score = Decimal(str(round(brier_score(probs, actual), 6)))
                prediction.log_loss = Decimal(str(round(log_loss_single(probs, actual), 6)))
                prediction.is_correct = predicted_result(probs) == actual
                prediction.validated_at = datetime.now(UTC)
                count += 1

        log.info("Validated %d prediction(s)", count)
        return count

    def __repr__(self) -> str:
        return "<PredictionValidator>"
