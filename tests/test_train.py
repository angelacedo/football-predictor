"""Algorithm/artifact dispatch in ml/train.py."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from footy.ml.train import MODEL_REGISTRY, _resolve_algorithm, train_model


def _matches_df() -> pd.DataFrame:
    rows = [
        {
            "id": i, "kickoff": f"2024-01-{(i % 28) + 1:02d}", "league": "La Liga",
            "home_team": f"T{i % 4}", "away_team": f"T{(i + 1) % 4}",
            "home_goals": i % 3, "away_goals": (i + 1) % 3,
        }
        for i in range(1, 30)
    ]
    return pd.DataFrame(rows)


def test_resolve_algorithm_random_forest_not_truncated_to_random() -> None:
    """random_forest has its own underscore - a naive split("_")[0] would
    misroute "random_forest_La_Liga" to "random", which isn't in the registry."""
    assert _resolve_algorithm("random_forest_La_Liga") == "random_forest"
    assert _resolve_algorithm("random_forest") == "random_forest"


def test_resolve_algorithm_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown model type"):
        _resolve_algorithm("nope")


def test_train_model_legacy_two_arg_random_forest_compat(model_dir: Path) -> None:
    """2-arg legacy call train_model(df, "random_forest_<league>") must still
    resolve to the random_forest algorithm and save under that exact name."""
    train_model(_matches_df(), "random_forest_La_Liga")
    assert (model_dir / "random_forest_La_Liga_latest").exists()


def test_train_model_explicit_algorithm_and_artifact(model_dir: Path) -> None:
    train_model(_matches_df(), "xgboost", "xgboost_La_Liga")
    assert (model_dir / "xgboost_La_Liga_latest").exists()


def test_train_model_unknown_algorithm_with_explicit_artifact_raises(model_dir: Path) -> None:
    with pytest.raises(ValueError, match="Unknown model type"):
        train_model(_matches_df(), "nope", "nope_La_Liga")


def test_model_registry_has_all_three_algorithms() -> None:
    assert set(MODEL_REGISTRY) == {"baseline", "xgboost", "random_forest"}
