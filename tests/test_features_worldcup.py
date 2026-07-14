"""World Cup feature builder: FIFA rank lookup, host-nation flag, no rolling
history (pure per-row static lookup - order-independence stands in for the
"leakage safety" check the club-football feature tests do, since there's no
chronological sweep here to leak across)."""

from __future__ import annotations

import pandas as pd

from footy.ml.features_worldcup import (
    _UNRANKED_DEFAULT,
    compute_feature_frame_worldcup,
)


def _matches() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": 1, "season": 2022, "home_team": "Qatar", "away_team": "Ecuador",
             "home_goals": 0, "away_goals": 2, "round": "Group Stage - 1",
             "winner_home": False, "winner_away": True},
            {"id": 2, "season": 2022, "home_team": "Brazil", "away_team": "Serbia",
             "home_goals": 2, "away_goals": 0, "round": "Group Stage - 1",
             "winner_home": True, "winner_away": False},
            {"id": 3, "season": 2026, "home_team": "United States", "away_team": "Wales",
             "home_goals": None, "away_goals": None, "round": "Round of 16",
             "winner_home": None, "winner_away": None},
            {"id": 4, "season": 2026, "home_team": "Freedonia", "away_team": "Brazil",
             "home_goals": None, "away_goals": None, "round": "Group Stage - 2",
             "winner_home": None, "winner_away": None},  # Freedonia: not in rankings at all
            # Real 2022 final: 3-3 (AET), Argentina (home) won on penalties -
            # goals tie but winner_home=True must override to HOME, not DRAW.
            {"id": 5, "season": 2022, "home_team": "Argentina", "away_team": "France",
             "home_goals": 3, "away_goals": 3, "round": "Final",
             "winner_home": True, "winner_away": False},
        ]
    )


def _rankings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"season": 2022, "team": "Qatar", "fifa_rank": 50},
            {"season": 2022, "team": "Ecuador", "fifa_rank": 44},
            {"season": 2022, "team": "Brazil", "fifa_rank": 1},
            {"season": 2022, "team": "Serbia", "fifa_rank": 21},
            {"season": 2026, "team": "United States", "fifa_rank": 11},
            {"season": 2026, "team": "Wales", "fifa_rank": 19},
            {"season": 2026, "team": "Brazil", "fifa_rank": 3},
            {"season": 2022, "team": "Argentina", "fifa_rank": 3},
            {"season": 2022, "team": "France", "fifa_rank": 4},
        ]
    )


def test_rank_lookup_uses_correct_season() -> None:
    feats = compute_feature_frame_worldcup(_matches(), _rankings())
    assert feats.loc[1, "fifa_rank_home"] == 50  # Qatar 2022
    assert feats.loc[1, "fifa_rank_away"] == 44  # Ecuador 2022
    # Brazil's rank differs by tournament (2022 vs 2026) - must not cross-contaminate.
    assert feats.loc[2, "fifa_rank_home"] == 1   # Brazil 2022
    assert feats.loc[4, "fifa_rank_away"] == 3   # Brazil 2026


def test_host_nation_flag_correct_per_tournament() -> None:
    feats = compute_feature_frame_worldcup(_matches(), _rankings())
    assert feats.loc[1, "is_host_home"] == 1.0   # Qatar was the real 2022 host
    assert feats.loc[1, "is_host_away"] == 0.0   # Ecuador was not
    assert feats.loc[2, "is_host_home"] == 0.0   # Brazil (2022) was not the host that year
    # 2026 is a tri-host tournament - all three host nations must flag True.
    tri_host = compute_feature_frame_worldcup(
        pd.DataFrame([
            {"id": 100, "season": 2026, "home_team": "United States", "away_team": "Canada",
             "home_goals": None, "away_goals": None},
        ]),
        _rankings(),
    )
    assert tri_host.loc[100, "is_host_home"] == 1.0
    assert tri_host.loc[100, "is_host_away"] == 1.0


def test_unranked_team_gets_default_worse_than_any_real_rank() -> None:
    feats = compute_feature_frame_worldcup(_matches(), _rankings())
    assert feats.loc[4, "fifa_rank_home"] == _UNRANKED_DEFAULT  # Freedonia: not in rankings
    assert feats["fifa_rank_home"].drop(4).max() < _UNRANKED_DEFAULT


def test_result_column_played_vs_unplayed() -> None:
    feats = compute_feature_frame_worldcup(_matches(), _rankings())
    assert feats.loc[1, "result"] == "AWAY"  # Qatar 0-2 Ecuador
    assert feats.loc[2, "result"] == "HOME"  # Brazil 2-0 Serbia
    assert pd.isna(feats.loc[3, "result"])   # unplayed


def test_knockout_tie_decided_by_penalties_uses_winner_flag() -> None:
    """Real bug: goals tied 3-3 (Argentina beat France on penalties, 2022
    final) must label HOME, not DRAW - result_from_goals alone would get
    this wrong since it only ever sees the AET score."""
    feats = compute_feature_frame_worldcup(_matches(), _rankings())
    assert feats.loc[5, "result"] == "HOME"


def test_is_knockout_flag_from_round() -> None:
    feats = compute_feature_frame_worldcup(_matches(), _rankings())
    assert feats.loc[1, "is_knockout"] == 0.0  # Group Stage - 1
    assert feats.loc[3, "is_knockout"] == 1.0  # Round of 16
    assert feats.loc[5, "is_knockout"] == 1.0  # Final
    # Missing round (not yet re-synced) must default to 0.0, never assumed knockout.
    no_round = compute_feature_frame_worldcup(
        pd.DataFrame([
            {"id": 200, "season": 2022, "home_team": "Qatar", "away_team": "Ecuador",
             "home_goals": None, "away_goals": None},
        ]),
        _rankings(),
    )
    assert no_round.loc[200, "is_knockout"] == 0.0


def test_row_order_independent() -> None:
    """No rolling sweep here - shuffling input rows must not change any
    row's own features, unlike footy.ml.features's chronological design."""
    matches = _matches()
    shuffled = matches.iloc[::-1].reset_index(drop=True)
    a = compute_feature_frame_worldcup(matches, _rankings())
    b = compute_feature_frame_worldcup(shuffled, _rankings())
    pd.testing.assert_frame_equal(a.sort_index(), b.sort_index())
