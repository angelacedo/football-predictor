"""Produce 1X2 probabilities from a trained model.

Example:
    >>> probs = MatchProbs(0.6, 0.25, 0.15)
    >>> probs.confidence
    0.6
    >>> round(sum(probs.as_tuple()), 4)
    1.0
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from footy.domain import RESULT_CLASSES, MatchProbs
from footy.ml.features import FEATURE_COLUMNS, compute_feature_frame
from footy.ml.registry import load_latest

log = logging.getLogger("footy.ml.predict")


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


def predict_ensemble(
    match_features_df: pd.DataFrame, league: str, model_types: list[str]
) -> dict[str, Any]:
    """Average predict_proba across each model type's per-league model.

    Args:
        match_features_df: A single-row feature frame (already built by
            :func:`compute_feature_frame`), with :data:`FEATURE_COLUMNS`.
        league: League name; models are registered as ``f"{model_type}_{league}"``
            with spaces replaced by underscores.
        model_types: Model types to ensemble, e.g. ``["baseline", "xgboost"]``.

    Returns:
        ``{"HOME": float, "DRAW": float, "AWAY": float, "models_used": [str]}``,
        equal-weight average over whichever models were actually found.

    Raises:
        ValueError: if none of ``model_types`` has a registered model for ``league``.
    """
    key_suffix = league.replace(" ", "_")
    home_probs: list[float] = []
    draw_probs: list[float] = []
    away_probs: list[float] = []
    models_used: list[str] = []

    for model_type in model_types:
        key = f"{model_type}_{key_suffix}"
        try:
            model = load_latest(key)
        except FileNotFoundError:
            log.warning("No model registered for '%s', skipping", key)
            continue
        probs = _probs_from_model(model, match_features_df)
        home_probs.append(probs.home)
        draw_probs.append(probs.draw)
        away_probs.append(probs.away)
        models_used.append(key)

    if not models_used:
        raise ValueError(f"No models available for league '{league}' among {model_types}")

    return {
        "HOME": sum(home_probs) / len(models_used),
        "DRAW": sum(draw_probs) / len(models_used),
        "AWAY": sum(away_probs) / len(models_used),
        "models_used": models_used,
    }


def predict_ensemble_from_history(
    matches_df: pd.DataFrame, match_id: int, league: str, model_types: list[str]
) -> dict[str, Any]:
    """Like :func:`predict_ensemble`, but from raw match history (as :func:`predict_match`
    takes) instead of an already-computed feature frame.

    Args:
        matches_df: The target match plus its prior history (finished matches).
        match_id: ``id`` of the row to predict.
        league: Passed through to :func:`predict_ensemble`.
        model_types: Passed through to :func:`predict_ensemble`.

    Returns:
        Same as :func:`predict_ensemble`.
    """
    feats = compute_feature_frame(matches_df)
    row = feats.loc[[match_id]]
    return predict_ensemble(row, league, model_types)
