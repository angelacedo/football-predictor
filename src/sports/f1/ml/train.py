"""Train an F1 finishing-position regression model.

ML approach: regression on finishing position (sort predictions to derive
race order), not listwise/pairwise ranking (XGBRanker/LambdaMART) - reuses the
existing sklearn-Pipeline shape and is simple to debug. Flagged in the plan as
a follow-up spike: compare against a real ranking model once there's enough
validated data to judge Spearman correlation, not decided here.

Reuses footy.ml.registry.save_model directly (pure joblib I/O, no football
logic in it) rather than duplicating that file for F1.
"""

from __future__ import annotations

import logging

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from footy.ml.registry import save_model
from sports.f1.ml.features import FEATURE_COLUMNS, compute_feature_frame

log = logging.getLogger("sports.f1.ml.train")

MODEL_NAME = "baseline"
F1_MODEL_DIR = "models/f1"  # separate namespace from footy's models/, no artifact-name collisions


def build_pipeline() -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("clf", LinearRegression())])


def build_xgboost_pipeline() -> Pipeline:
    return Pipeline(
        [("scale", StandardScaler()), ("clf", XGBRegressor(n_estimators=300, max_depth=4))]
    )


def build_random_forest_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", RandomForestRegressor(n_estimators=200, random_state=42)),
        ]
    )


MODEL_REGISTRY = {
    "baseline": build_pipeline,
    "xgboost": build_xgboost_pipeline,
    "random_forest": build_random_forest_pipeline,
}


def _resolve_algorithm(name: str) -> str:
    """Longest-prefix match against MODEL_REGISTRY (same fix as footy.ml.train's
    dispatch bug - "random_forest" has its own underscore, a naive
    name.split("_")[0] would misroute it to "random")."""
    for key in sorted(MODEL_REGISTRY, key=len, reverse=True):
        if name == key or name.startswith(key + "_"):
            return key
    raise ValueError(f"Unknown model type in '{name}'; registry: {sorted(MODEL_REGISTRY)}")


def train_model(
    entries_df: pd.DataFrame,
    algorithm_name: str = MODEL_NAME,
    artifact_name: str | None = None,
    model_dir: str | None = None,
) -> Pipeline:
    """Train on finished F1 entries and persist the artifact.

    Args:
        entries_df: Entries with the columns required by
            :func:`sports.f1.ml.features.compute_feature_frame`.
        algorithm_name: Key into MODEL_REGISTRY.
        artifact_name: Registry name to save under (defaults to algorithm_name).
        model_dir: Defaults to F1_MODEL_DIR (own namespace, not footy's).

    Returns:
        The fitted pipeline.

    Raises:
        ValueError: if there are no finished entries to train on, or the
            algorithm isn't registered.
    """
    if artifact_name is None:
        artifact_name = algorithm_name
        algorithm_name = _resolve_algorithm(algorithm_name)
    elif algorithm_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model type in '{algorithm_name}'; registry: {sorted(MODEL_REGISTRY)}"
        )

    feats = compute_feature_frame(entries_df)
    played = feats[feats["label"].notna()]
    if played.empty:
        raise ValueError("No finished entries to train on.")

    x = played[list(FEATURE_COLUMNS)]
    y = played["label"].astype(float)
    pipe = MODEL_REGISTRY[algorithm_name]()
    pipe.fit(x, y)
    artifact = save_model(pipe, artifact_name, model_dir=model_dir or F1_MODEL_DIR)
    log.info(
        "Trained '%s' (%s) on %d entries -> %s",
        artifact_name, algorithm_name, len(played), artifact,
    )
    return pipe
