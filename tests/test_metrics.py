"""Aggregate metrics over validated predictions."""

from __future__ import annotations

import pandas as pd
import pytest

from footy.predictions.metrics import (
    breakdown_by,
    breakdown_by_league_and_model,
    mean_brier,
    overall_accuracy,
    summary,
)


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "prob_home_win": [0.6, 0.3, 0.5],
            "prob_draw": [0.25, 0.4, 0.3],
            "prob_away_win": [0.15, 0.3, 0.2],
            "actual_result": ["HOME", "AWAY", "HOME"],
            "is_correct": [True, False, True],
            "brier_score": [0.14, 0.9, 0.3],
            "log_loss": [0.5, 1.2, 0.7],
            "league": ["EPL", "EPL", "LaLiga"],
            "model_name": ["baseline", "baseline", "xgboost"],
        }
    )


def test_overall_accuracy() -> None:
    assert overall_accuracy(_df()) == pytest.approx(2 / 3)


def test_mean_brier() -> None:
    assert mean_brier(_df()) == pytest.approx((0.14 + 0.9 + 0.3) / 3)


def test_summary_keys() -> None:
    s = summary(_df())
    assert s["n"] == 3
    assert set(s) == {"n", "accuracy", "brier", "log_loss"}


def test_breakdown_by_league() -> None:
    bd = breakdown_by(_df(), "league")
    assert bd["EPL"]["n"] == 2
    assert bd["LaLiga"]["accuracy"] == pytest.approx(1.0)


def test_breakdown_by_league_and_model() -> None:
    rows = breakdown_by_league_and_model(_df())
    assert rows == [
        {"league": "EPL", "model_name": "baseline", **summary(_df().iloc[[0, 1]])},
        {"league": "LaLiga", "model_name": "xgboost", **summary(_df().iloc[[2]])},
    ]


def test_breakdown_by_league_and_model_empty() -> None:
    assert breakdown_by_league_and_model(_df().iloc[0:0]) == []
