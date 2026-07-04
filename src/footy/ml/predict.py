"""Produce 1X2 probabilities from a trained model.

Example:
    >>> probs = MatchProbs(0.6, 0.25, 0.15)
    >>> probs.confidence
    0.6
    >>> round(sum(probs.as_tuple()), 4)
    1.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from footy.ml.features import FEATURE_COLUMNS, RESULT_CLASSES, compute_feature_frame
from footy.ml.registry import load_latest


@dataclass(frozen=True)
class MatchProbs:
    """Calibrated 1X2 probabilities for a single match."""

    home: float
    draw: float
    away: float

    def as_tuple(self) -> tuple[float, float, float]:
        """Return probabilities in (HOME, DRAW, AWAY) order."""
        return (self.home, self.draw, self.away)

    @property
    def confidence(self) -> float:
        """Confidence signal = the largest class probability."""
        return max(self.as_tuple())

    def __repr__(self) -> str:
        return f"<MatchProbs H={self.home:.3f} D={self.draw:.3f} A={self.away:.3f}>"


def _probs_from_model(model: Any, features: pd.DataFrame) -> MatchProbs:
    """Run ``predict_proba`` on a single-row feature frame, ordered HOME/DRAW/AWAY."""
    raw = model.predict_proba(features[list(FEATURE_COLUMNS)])[0]
    by_class = dict(zip(model.classes_, raw, strict=True))
    return MatchProbs(
        home=float(by_class.get("HOME", 0.0)),
        draw=float(by_class.get("DRAW", 0.0)),
        away=float(by_class.get("AWAY", 0.0)),
    )


def predict_match(matches_df: pd.DataFrame, match_id: int, model: Any | None = None,
                  model_name: str = "baseline") -> MatchProbs:
    """Predict probabilities for ``match_id`` using leakage-safe history in ``matches_df``.

    Args:
        matches_df: The target match plus its prior history (finished matches).
        match_id: ``id`` of the row to predict.
        model: A fitted estimator; if None, the latest registered ``model_name`` is loaded.
        model_name: Registry name used when ``model`` is None.

    Returns:
        MatchProbs in HOME/DRAW/AWAY order.

    Note:
        Exact score (``predicted_score_*``) is not modelled by this 1X2 classifier;
        callers store None. ``ponytail:`` add a Poisson score model only if score
        prediction is actually needed.
    """
    assert set(RESULT_CLASSES) == {"HOME", "DRAW", "AWAY"}
    est = model if model is not None else load_latest(model_name)
    feats = compute_feature_frame(matches_df)
    row = feats.loc[[match_id]]
    return _probs_from_model(est, row)
