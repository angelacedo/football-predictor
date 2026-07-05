"""predict_ensemble / predict_ensemble_from_history."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from footy.ml.features import FEATURE_COLUMNS
from footy.ml.predict import predict_ensemble, predict_ensemble_from_history
from footy.ml.registry import save_model


def _fit_dummy() -> DummyClassifier:
    x = pd.DataFrame([[0.0] * len(FEATURE_COLUMNS)] * 3, columns=list(FEATURE_COLUMNS))
    return DummyClassifier(strategy="uniform").fit(x, ["HOME", "DRAW", "AWAY"])


def _matches_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": 1, "kickoff": "2024-01-01", "league": "La Liga", "home_team": "A",
             "away_team": "B", "home_goals": 2, "away_goals": 0},
            {"id": 2, "kickoff": "2024-01-08", "league": "La Liga", "home_team": "A",
             "away_team": "C", "home_goals": None, "away_goals": None},
        ]
    )


def test_predict_ensemble_averages_found_models_and_skips_missing(model_dir: Path) -> None:
    save_model(_fit_dummy(), "baseline_La_Liga")
    save_model(_fit_dummy(), "xgboost_La_Liga")
    row = pd.DataFrame([[0.0] * len(FEATURE_COLUMNS)], columns=list(FEATURE_COLUMNS))

    result = predict_ensemble(row, "La Liga", ["baseline", "xgboost", "random_forest"])

    assert result["models_used"] == ["baseline_La_Liga", "xgboost_La_Liga"]
    assert result["HOME"] == pytest.approx(1 / 3)
    assert result["HOME"] + result["DRAW"] + result["AWAY"] == pytest.approx(1.0)


def test_predict_ensemble_no_models_raises(model_dir: Path) -> None:
    row = pd.DataFrame([[0.0] * len(FEATURE_COLUMNS)], columns=list(FEATURE_COLUMNS))
    with pytest.raises(ValueError, match="No models available"):
        predict_ensemble(row, "Bundesliga", ["baseline"])


def test_predict_ensemble_from_history_matches_direct_ensemble(model_dir: Path) -> None:
    """Same result whether called from raw history (match_id=2, unplayed) or a
    precomputed feature frame for that same match - the two APIs must agree."""
    save_model(_fit_dummy(), "baseline_La_Liga")
    matches_df = _matches_df()

    from_history = predict_ensemble_from_history(matches_df, 2, "La Liga", ["baseline"])

    from footy.ml.features import compute_feature_frame
    feats = compute_feature_frame(matches_df)
    direct = predict_ensemble(feats.loc[[2]], "La Liga", ["baseline"])

    assert from_history == direct
