"""Feature builder: shape, columns, and no look-ahead leakage."""

from __future__ import annotations

import pandas as pd

from footy.ml.features import (
    _POSSESSION_DEFAULT,
    _XG_DEFAULT,
    FEATURE_COLUMNS,
    compute_feature_frame,
    result_from_goals,
)


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


def test_xg_possession_default_when_columns_absent() -> None:
    """matches_dataframe() callers that don't supply xg/possession (or a stats
    job that hasn't run yet) must not crash - cold-start default, not KeyError."""
    feats = compute_feature_frame(_matches())
    first = feats.loc[1]
    assert first["home_xg_form"] == _XG_DEFAULT
    assert first["home_possession_form"] == _POSSESSION_DEFAULT


def _matches_with_stats() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": 1, "kickoff": "2024-01-01", "league": "L", "home_team": "A",
             "away_team": "B", "home_goals": 2, "away_goals": 0,
             "xg_home": 2.1, "xg_away": 0.4,
             "possession_home": 60.0, "possession_away": 40.0},
            {"id": 2, "kickoff": "2024-01-08", "league": "L", "home_team": "A",
             "away_team": "C", "home_goals": 1, "away_goals": 1,
             "xg_home": None, "xg_away": 1.0,  # stats job hasn't caught up for A yet
             "possession_home": None, "possession_away": 55.0},
        ]
    )


def test_xg_possession_rolls_forward_leakage_safe() -> None:
    feats = compute_feature_frame(_matches_with_stats())
    # Match 2's home team (A) form reflects ONLY match 1's real xG/possession.
    assert feats.loc[2, "home_xg_form"] == 2.1
    assert feats.loc[2, "home_possession_form"] == 60.0


def test_xg_possession_missing_stat_does_not_poison_history() -> None:
    """Match 2 has real goals but null xg_home/possession_home (stats job
    lagging) - A's own xg/possession history must simply not update from
    match 2, not silently record a null/zero as if it were real."""
    matches = _matches_with_stats()
    # Add a 3rd match for A at home, to observe what history it inherits.
    matches = pd.concat([matches, pd.DataFrame([
        {"id": 3, "kickoff": "2024-01-15", "league": "L", "home_team": "A",
         "away_team": "B", "home_goals": None, "away_goals": None,
         "xg_home": None, "xg_away": None,
         "possession_home": None, "possession_away": None},
    ])], ignore_index=True)
    feats = compute_feature_frame(matches)
    # A's xg_form going into match 3 is STILL just match 1's 2.1 (match 2
    # never contributed since its xg_home was null), not 0.0 or a NaN blend.
    assert feats.loc[3, "home_xg_form"] == 2.1
