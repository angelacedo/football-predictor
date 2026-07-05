"""Aggregate metrics over validated predictions."""

from __future__ import annotations

import pandas as pd
import pytest

from footy.predictions.metrics import (
    best_model_per_league,
    breakdown_by,
    breakdown_by_league_and_model,
    mean_brier,
    overall_accuracy,
    pairs_needing_retrain,
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


def _row(league: str, model_name: str, n: float, brier: float) -> dict[str, str | float]:
    return {"league": league, "model_name": model_name, "n": n, "accuracy": 0.0,
            "brier": brier, "log_loss": 0.0}


def test_best_model_per_league_picks_lowest_brier_meeting_min_n() -> None:
    rows = [
        _row("La Liga", "baseline_La_Liga", 15, 0.60),
        _row("La Liga", "xgboost_La_Liga", 15, 0.55),
        _row("La Liga", "random_forest_La_Liga", 3, 0.10),  # below min_n - ignored
        _row("Premier League", "baseline_Premier_League", 12, 0.62),
    ]
    assert best_model_per_league(rows, min_n=10) == {
        "La Liga": "xgboost_La_Liga",
        "Premier League": "baseline_Premier_League",
    }


def test_best_model_per_league_empty_when_nothing_qualifies() -> None:
    rows = [_row("La Liga", "baseline_La_Liga", 3, 0.10)]
    assert best_model_per_league(rows, min_n=10) == {}


def test_pairs_needing_retrain_flags_real_degradation() -> None:
    current = [_row("La Liga", "xgboost_La_Liga", 8, 0.75)]
    baseline = [_row("La Liga", "xgboost_La_Liga", 30, 0.65)]
    result = pairs_needing_retrain(current, baseline, degradation=0.05)
    assert result == [
        {"league": "La Liga", "model_name": "xgboost_La_Liga",
         "current_brier": 0.75, "baseline_brier": 0.65}
    ]


def test_pairs_needing_retrain_ignores_noise_within_margin() -> None:
    current = [_row("La Liga", "xgboost_La_Liga", 8, 0.68)]
    baseline = [_row("La Liga", "xgboost_La_Liga", 30, 0.65)]
    assert pairs_needing_retrain(current, baseline, degradation=0.05) == []


def test_pairs_needing_retrain_skips_insufficient_baseline() -> None:
    current = [_row("La Liga", "xgboost_La_Liga", 8, 0.90)]
    baseline = [_row("La Liga", "xgboost_La_Liga", 5, 0.65)]  # below min_baseline
    assert pairs_needing_retrain(current, baseline) == []


def test_pairs_needing_retrain_skips_insufficient_current() -> None:
    current = [_row("La Liga", "xgboost_La_Liga", 2, 0.90)]
    baseline = [_row("La Liga", "xgboost_La_Liga", 30, 0.65)]
    assert pairs_needing_retrain(current, baseline) == []


def test_pairs_needing_retrain_skips_pair_with_no_baseline_at_all() -> None:
    current = [_row("Ligue 1", "xgboost_Ligue_1", 8, 0.90)]
    baseline: list[dict[str, str | float]] = []
    assert pairs_needing_retrain(current, baseline) == []
