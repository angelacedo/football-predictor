"""Train the baseline 1X2 model.

Baseline is a scaled multinomial logistic regression — cheap, gives calibrated-ish
probabilities, and is a proper reference before reaching for gradient boosting.
``ponytail:`` swap in XGBoost only once the baseline Brier is measured and found
lacking.

Example:
    >>> pipe = train_model(finished_matches_df, "baseline")  # doctest: +SKIP
"""

from __future__ import annotations

import logging

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from footy.ml.features import FEATURE_COLUMNS, compute_feature_frame
from footy.ml.registry import save_model

log = logging.getLogger("footy.ml.train")

MODEL_NAME = "baseline"


def build_pipeline() -> Pipeline:
    """Return an untrained scaler + multinomial logistic-regression pipeline."""
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),  # multinomial by default
        ]
    )


def build_xgboost_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "clf",
                XGBClassifier(
                    n_estimators=300,
                    max_depth=4,
                    learning_rate=0.05,
                    eval_metric="mlogloss",
                ),
            ),
        ]
    )


def build_random_forest_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=200, random_state=42)),
        ]
    )


MODEL_REGISTRY = {
    "baseline": build_pipeline,
    "xgboost": build_xgboost_pipeline,
    "random_forest": build_random_forest_pipeline,
}


def _resolve_builder(model_name: str) -> Pipeline:
    for key in sorted(MODEL_REGISTRY, key=len, reverse=True):
        if model_name == key or model_name.startswith(key + "_"):
            return MODEL_REGISTRY[key]()
    raise ValueError(f"Unknown model type in '{model_name}'; registry: {sorted(MODEL_REGISTRY)}")


def train_model(matches_df: pd.DataFrame, model_name: str = MODEL_NAME) -> Pipeline:
    """Train on finished matches in ``matches_df`` and persist the artifact.

    Args:
        matches_df: Matches with the columns required by
            :func:`footy.ml.features.compute_feature_frame`.
        model_name: Registry name to save under.

    Returns:
        The fitted pipeline.

    Raises:
        ValueError: if there are no finished matches to train on.
    """
    feats = compute_feature_frame(matches_df)
    played = feats[feats["result"].notna()]
    if played.empty:
        raise ValueError("No finished matches to train on.")

    x = played[list(FEATURE_COLUMNS)]
    y = played["result"].astype(str)
    pipe = _resolve_builder(model_name)
    pipe.fit(x, y)
    artifact = save_model(pipe, model_name)
    log.info("Trained '%s' on %d matches -> %s", model_name, len(played), artifact)
    return pipe
