"""Cross-sport contract every sport module satisfies.

Deliberately loose typing at this boundary (``Any`` on predict's return, on
sync's kwargs) - different sports return genuinely different prediction
shapes (football's MatchProbs vs. e.g. a future sport's ranking type). Each
concrete sport module keeps its own mypy-strict internal types; only this
cross-sport layer sees ``Any``.
"""

from __future__ import annotations

from typing import Any, Protocol

import pandas as pd


class SportModule(Protocol):
    """Structural contract for a sport's data/ML pipeline."""

    name: str

    def sync(self, season: int, provider: Any | None = None, **kwargs: Any) -> int:
        """Fetch and upsert raw results for a season. Returns rows written."""
        ...

    def compute_features(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Turn raw synced rows into a leakage-safe feature frame."""
        ...

    def train(
        self,
        features_df: pd.DataFrame,
        algorithm_name: str,
        artifact_name: str | None = None,
        model_dir: str | None = None,
    ) -> Any:
        """Train and persist a model, return the fitted estimator."""
        ...

    def predict(
        self, features_df: pd.DataFrame, entity_id: int, model: Any | None = None
    ) -> Any:
        """Predict an outcome for one entity (a match id, a session id, ...)."""
        ...


class SupportsValueBetting(Protocol):
    """Optional capability - NOT part of SportModule.

    Football implements this (real 1X2 bookmaker odds exist). A sport without
    a 1X2-shaped market does not: this repo's odds/bets tables are hardcoded
    to 3-way 1X2.
    """

    def find_value_bet(self, prediction: Any, market_odds: Any, threshold: float) -> Any | None:
        ...
