"""FootballModule: implements the cross-sport SportModule contract.

Pure wrapper - delegates to existing footy.* functions only, zero logic
duplication, zero changes to any src/footy/* file.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from footy.domain import MatchProbs
from footy.ingest.matches import sync_league
from footy.ml.features import compute_feature_frame
from footy.ml.predict import predict_match
from footy.ml.train import MODEL_NAME, train_model


class FootballModule:
    """SportModule implementation for football (league or World Cup - same
    1X2 pipeline, competition format is metadata, not a code fork).

    predict() wraps predict_match(), not predict_ensemble() - the latter
    requires `league: str` and `model_types: list[str]`, neither of which fit
    SportModule.predict()'s (features_df, entity_id, model) shape without an
    awkward forced mapping. Ensemble prediction stays available directly via
    footy.ml.predict.predict_ensemble*() for callers who need it; it's simply
    not exposed through this generic single-model contract yet.
    """

    name = "football"

    def sync(self, season: int, provider: Any | None = None, **kwargs: Any) -> int:
        """Sync one league's fixtures/results for ``season``.

        Requires ``league_id: int`` in kwargs (sync_league's own first
        positional arg) - SportModule.sync()'s generic (season, provider,
        **kwargs) shape doesn't have a dedicated slot for it.

        Raises:
            ValueError: if kwargs["league_id"] is missing.
        """
        if "league_id" not in kwargs:
            raise ValueError("FootballModule.sync() requires league_id in kwargs")
        return sync_league(kwargs["league_id"], season, provider)

    def compute_features(self, raw_df: pd.DataFrame) -> pd.DataFrame:
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
    ) -> MatchProbs:
        return predict_match(features_df, entity_id, model=model, model_name=MODEL_NAME)
