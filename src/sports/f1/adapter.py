"""F1Module: implements the cross-sport SportModule contract."""

from __future__ import annotations

from typing import Any

import pandas as pd

from sports.f1.domain import DriverRanking
from sports.f1.ingest.sessions import sync_season
from sports.f1.ml.features import compute_feature_frame
from sports.f1.ml.predict import predict_session
from sports.f1.ml.train import MODEL_NAME, train_model


class F1Module:
    """SportModule implementation for Formula 1. No SupportsValueBetting -
    no odds data source is scoped for F1 (see contract.py's docstring)."""

    name = "f1"

    def sync(self, season: int, provider: Any | None = None, **kwargs: Any) -> int:
        session_type = kwargs.get("session_type", "RACE")
        return sync_season(season, session_type=session_type, provider=provider)

    def compute_features(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        # Contract names this param "features_df", but - same as football's
        # train_model - it's actually raw entries; features are computed here.
        return compute_feature_frame(raw_df)

    def train(
        self,
        features_df: pd.DataFrame,
        algorithm_name: str,
        artifact_name: str | None = None,
        model_dir: str | None = None,
    ) -> Any:
        return train_model(features_df, algorithm_name, artifact_name, model_dir)

    def predict(
        self, features_df: pd.DataFrame, entity_id: int, model: Any | None = None
    ) -> DriverRanking:
        return predict_session(features_df, entity_id, model, model_name=MODEL_NAME)
