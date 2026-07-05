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
from typing import Any

import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
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


class _LabelEncodedXGBClassifier(BaseEstimator, ClassifierMixin):  # type: ignore[misc]
    """XGBClassifier (xgboost>=2.0) only accepts integer class labels - no more
    use_label_encoder. Encode "HOME"/"DRAW"/"AWAY" internally, expose classes_
    as the original strings so ml/predict.py's model.classes_ lookup still works."""

    def __init__(
        self, n_estimators: int = 300, max_depth: int = 4,
        learning_rate: float = 0.05, eval_metric: str = "mlogloss",
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.eval_metric = eval_metric

    def fit(self, x: pd.DataFrame, y: pd.Series) -> _LabelEncodedXGBClassifier:
        self._label_encoder = LabelEncoder()
        y_encoded = self._label_encoder.fit_transform(y)
        self._model = XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            eval_metric=self.eval_metric,
        )
        self._model.fit(x, y_encoded)
        self.classes_ = self._label_encoder.classes_
        return self

    def predict_proba(self, x: pd.DataFrame) -> Any:
        return self._model.predict_proba(x)


def build_xgboost_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", _LabelEncodedXGBClassifier()),
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


def _resolve_algorithm(name: str) -> str:
    """Longest-prefix match against MODEL_REGISTRY (handles "random_forest"'s own '_')."""
    for key in sorted(MODEL_REGISTRY, key=len, reverse=True):
        if name == key or name.startswith(key + "_"):
            return key
    raise ValueError(f"Unknown model type in '{name}'; registry: {sorted(MODEL_REGISTRY)}")


def train_model(
    matches_df: pd.DataFrame,
    algorithm_name: str = MODEL_NAME,
    artifact_name: str | None = None,
    model_dir: str | None = None,
) -> Pipeline:
    """Train on finished matches in ``matches_df`` and persist the artifact.

    Args:
        matches_df: Matches with the columns required by
            :func:`footy.ml.features.compute_feature_frame`.
        algorithm_name: Key into ``MODEL_REGISTRY`` selecting which estimator
            to build.
        artifact_name: Registry name to save under. If omitted, ``algorithm_name``
            is treated as a legacy combined ``model_name`` (e.g.
            ``"xgboost_La_Liga"``): it becomes the artifact name, and the real
            algorithm is derived from it via longest-prefix match — same
            two-positional-arg call as before this split.
        model_dir: Passed through to :func:`footy.ml.registry.save_model`. If
            None (default), falls back to ``get_settings().model_dir`` exactly
            as before this parameter existed.

    Returns:
        The fitted pipeline.

    Raises:
        ValueError: if there are no finished matches to train on, or the
            algorithm isn't registered.
    """
    if artifact_name is None:
        artifact_name = algorithm_name
        algorithm_name = _resolve_algorithm(algorithm_name)
    elif algorithm_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model type in '{algorithm_name}'; registry: {sorted(MODEL_REGISTRY)}"
        )

    feats = compute_feature_frame(matches_df)
    played = feats[feats["result"].notna()]
    if played.empty:
        raise ValueError("No finished matches to train on.")

    x = played[list(FEATURE_COLUMNS)]
    y = played["result"].astype(str)
    pipe = MODEL_REGISTRY[algorithm_name]()
    pipe.fit(x, y)
    artifact = save_model(pipe, artifact_name, model_dir=model_dir)
    log.info(
        "Trained '%s' (%s) on %d matches -> %s",
        artifact_name, algorithm_name, len(played), artifact,
    )
    return pipe
