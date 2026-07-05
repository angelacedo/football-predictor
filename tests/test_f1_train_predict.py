"""F1 train_model()/predict_session() dispatch, compat, and end-to-end shape."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sports.f1.domain import DriverRanking
from sports.f1.ml.predict import predict_session
from sports.f1.ml.train import MODEL_REGISTRY, _resolve_algorithm, train_model


def _entries_df(n_sessions: int = 8) -> pd.DataFrame:
    rows = []
    entry_id = 1
    for s in range(1, n_sessions + 1):
        for driver in (1, 2, 3, 4):
            rows.append(
                {
                    "entry_id": entry_id, "session_id": s, "start_time": f"2024-{s:02d}-01",
                    "circuit": "Bahrain", "season": 2024, "round": s,
                    "driver_number": driver, "driver_name": f"D{driver}", "team": f"T{driver % 2}",
                    "finish_position": ((driver + s) % 4) + 1, "status": "FINISHED",
                    "points": 10.0,
                }
            )
            entry_id += 1
    return pd.DataFrame(rows)


def test_resolve_algorithm_random_forest_not_truncated() -> None:
    assert _resolve_algorithm("random_forest_2024") == "random_forest"
    assert _resolve_algorithm("random_forest") == "random_forest"


def test_resolve_algorithm_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown model type"):
        _resolve_algorithm("nope")


def test_model_registry_has_regression_algorithms() -> None:
    assert set(MODEL_REGISTRY) == {"baseline", "xgboost", "random_forest"}


def test_train_model_no_finished_entries_raises(model_dir: Path) -> None:
    df = _entries_df(n_sessions=1)
    df["status"] = "SCHEDULED"
    df["finish_position"] = None
    with pytest.raises(ValueError, match="No finished entries"):
        train_model(df, "baseline", model_dir=str(model_dir))


def test_train_and_predict_end_to_end(model_dir: Path) -> None:
    df = _entries_df(n_sessions=8)
    train_model(df, "baseline", "baseline_2024", model_dir=str(model_dir))
    assert (model_dir / "baseline_2024_latest").exists()

    ranking = predict_session(
        df, session_id=8, model_name="baseline_2024", model_dir=str(model_dir)
    )
    assert isinstance(ranking, DriverRanking)
    assert set(ranking.predicted_position) == {1, 2, 3, 4}
    order = ranking.ranking()
    assert set(order) == {1, 2, 3, 4}


def test_train_model_legacy_two_arg_compat(model_dir: Path) -> None:
    df = _entries_df(n_sessions=8)
    train_model(df, "xgboost_2024", model_dir=str(model_dir))
    assert (model_dir / "xgboost_2024_latest").exists()
