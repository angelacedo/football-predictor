"""Predict a driver finishing-position ranking for one F1 session."""

from __future__ import annotations

from typing import Any

import pandas as pd

from footy.ml.registry import load_latest
from sports.f1.domain import DriverRanking
from sports.f1.ml.features import FEATURE_COLUMNS, compute_feature_frame
from sports.f1.ml.train import F1_MODEL_DIR, MODEL_NAME


def predict_session(
    entries_df: pd.DataFrame,
    session_id: int,
    model: Any | None = None,
    model_name: str = MODEL_NAME,
    model_dir: str | None = None,
) -> DriverRanking:
    """Predict finishing positions for every driver in ``session_id``.

    Args:
        entries_df: The target session's entries plus prior history (finished
            entries), same shape as :func:`sports.f1.data.entries_dataframe`.
        session_id: Internal ``F1Session.id`` (not the provider's external id).
        model: A fitted estimator; if None, the latest registered ``model_name``
            is loaded from ``model_dir`` (or F1's own model_dir namespace).
        model_name: Registry name used when ``model`` is None.
        model_dir: Defaults to F1_MODEL_DIR when None - same override pattern
            as ml.train.train_model, so tests can point both at a tmp dir.

    Returns:
        DriverRanking for every driver entered in that session.
    """
    est = model if model is not None else load_latest(
        model_name, model_dir=model_dir or F1_MODEL_DIR
    )
    feats = compute_feature_frame(entries_df)
    raw = entries_df.set_index("entry_id")
    target_ids = raw.index[raw["session_id"] == session_id]

    rows = feats.loc[target_ids]
    preds = est.predict(rows[list(FEATURE_COLUMNS)])
    driver_numbers = raw.loc[target_ids, "driver_number"]

    return DriverRanking(
        predicted_position=dict(zip(driver_numbers, (float(p) for p in preds), strict=True))
    )
