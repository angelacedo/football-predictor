"""Feature builder: shape, columns, and no look-ahead leakage."""

from __future__ import annotations

import pandas as pd

from footy.ml.features import FEATURE_COLUMNS, compute_feature_frame, result_from_goals


def _matches() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": 1, "kickoff": "2024-01-01", "league": "L", "home_team": "A",
             "away_team": "B", "home_goals": 2, "away_goals": 0},
            {"id": 2, "kickoff": "2024-01-08", "league": "L", "home_team": "A",
             "away_team": "C", "home_goals": 1, "away_goals": 1},
            {"id": 3, "kickoff": "2024-01-15", "league": "L", "home_team": "B",
             "away_team": "A", "home_goals": None, "away_goals": None},
        ]
    )


def test_result_from_goals() -> None:
    assert result_from_goals(2, 0) == "HOME"
    assert result_from_goals(0, 2) == "AWAY"
    assert result_from_goals(1, 1) == "DRAW"


def test_columns_and_shape() -> None:
    feats = compute_feature_frame(_matches())
    assert set(FEATURE_COLUMNS).issubset(feats.columns)
    assert len(feats) == 3


def test_first_match_has_no_history() -> None:
    feats = compute_feature_frame(_matches())
    first = feats.loc[1]
    # No prior matches -> all rolling form features are zero.
    assert first["home_form_pts"] == 0.0
    assert first["away_gf"] == 0.0


def test_no_leakage_result_column() -> None:
    feats = compute_feature_frame(_matches())
    # Match 1 was a home win; match 2 uses A's history from match 1 only.
    assert feats.loc[1, "result"] == "HOME"
    assert pd.isna(feats.loc[3, "result"])  # unplayed
    # A won match 1 -> A's form before match 2 reflects 3 points.
    assert feats.loc[2, "home_form_pts"] == 3.0
