"""Leakage-safe F1 feature engineering."""

from __future__ import annotations

import pandas as pd

from sports.f1.ml.features import FEATURE_COLUMNS, compute_feature_frame


def _entries_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"entry_id": 1, "session_id": 1, "start_time": "2024-01-01", "circuit": "Bahrain",
             "season": 2024, "round": 1, "driver_number": 1, "driver_name": "A", "team": "Red Bull",
             "finish_position": 1, "status": "FINISHED", "points": 25.0},
            {"entry_id": 2, "session_id": 1, "start_time": "2024-01-01", "circuit": "Bahrain",
             "season": 2024, "round": 1, "driver_number": 2, "driver_name": "B", "team": "Ferrari",
             "finish_position": 2, "status": "FINISHED", "points": 18.0},
            {"entry_id": 3, "session_id": 2, "start_time": "2024-01-15", "circuit": "Jeddah",
             "season": 2024, "round": 2, "driver_number": 1, "driver_name": "A", "team": "Red Bull",
             "finish_position": 1, "status": "FINISHED", "points": 25.0},
            {"entry_id": 4, "session_id": 3, "start_time": "2024-02-01", "circuit": "Bahrain",
             "season": 2024, "round": 3, "driver_number": 1, "driver_name": "A", "team": "Red Bull",
             "finish_position": None, "status": "SCHEDULED", "points": None},
        ]
    )


def test_first_entry_has_no_history() -> None:
    feats = compute_feature_frame(_entries_df())
    row = feats.loc[1]
    assert row["driver_form_pos"] == 15.0  # default, no prior races
    assert row["driver_form_points"] == 0.0
    assert row["label"] == 1.0


def test_second_race_reflects_first_race_history() -> None:
    feats = compute_feature_frame(_entries_df())
    row = feats.loc[3]  # driver 1's 2nd race, after finishing P1 in race 1
    assert row["driver_form_pos"] == 1.0
    assert row["driver_form_points"] == 25.0


def test_circuit_history_is_per_driver_per_circuit() -> None:
    feats = compute_feature_frame(_entries_df())
    # entry_id 4: driver 1 back at Bahrain (raced there in entry 1, finished P1)
    row = feats.loc[4]
    assert row["circuit_history_pos"] == 1.0


def test_unfinished_entry_has_no_label() -> None:
    feats = compute_feature_frame(_entries_df())
    assert pd.isna(feats.loc[4, "label"])


def test_all_feature_columns_present() -> None:
    feats = compute_feature_frame(_entries_df())
    for col in FEATURE_COLUMNS:
        assert col in feats.columns
