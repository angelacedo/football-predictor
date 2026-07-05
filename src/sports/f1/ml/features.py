"""Feature engineering for F1 finishing-position prediction.

Leakage-safe by construction, same discipline as footy.ml.features: sweep
entries in start_time order, snapshot each driver's/team's rolling history
*before* recording the current result, then append after.

ponytail: grid_position is NOT included - OpenF1's starting_grid endpoint
returned no data for every session tried (see ingest/providers/openf1.py's
docstring). Add it once a working grid-position source is found; until then
this trains on rolling form + circuit history only.
"""

from __future__ import annotations

from collections import defaultdict, deque

import pandas as pd

WINDOW = 5  # ponytail: same rolling-window knob as footy.ml.features; tune if underperforming.

FEATURE_COLUMNS: tuple[str, ...] = (
    "driver_form_pos",
    "driver_form_points",
    "circuit_history_pos",
    "team_form_pos",
    "driver_rest_days",
)


def _avg(values: list[float], default: float = 15.0) -> float:
    """Default 15.0 ~= mid-grid finishing position for a driver/circuit with no history."""
    return sum(values) / len(values) if values else default


def compute_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Compute leakage-safe features for every entry in ``df``.

    Args:
        df: Entries with columns ``entry_id, session_id, start_time, circuit,
            season, round, driver_number, driver_name, team, finish_position,
            status, points`` (see sports.f1.data.entries_dataframe).

    Returns:
        DataFrame indexed by ``entry_id`` with :data:`FEATURE_COLUMNS` plus a
        ``label`` column (finish_position, or null for unfinished/future entries).
    """
    data = df.copy()
    data["start_time"] = pd.to_datetime(data["start_time"])
    data = data.sort_values(["start_time", "driver_number"]).reset_index(drop=True)

    driver_pos: dict[int, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    driver_pts: dict[int, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    circuit_pos: dict[tuple[int, str], deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    team_pos: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    last_date: dict[int, pd.Timestamp] = {}

    rows: list[dict[str, object]] = []
    for rec in data.to_dict("records"):
        driver = rec["driver_number"]
        team = rec["team"]
        circuit = rec["circuit"]
        start_time = rec["start_time"]
        rest_days = (start_time - last_date[driver]).days if driver in last_date else WINDOW * 21

        rows.append(
            {
                "entry_id": rec["entry_id"],
                "driver_form_pos": _avg(list(driver_pos[driver])),
                "driver_form_points": _avg(list(driver_pts[driver]), default=0.0),
                "circuit_history_pos": _avg(list(circuit_pos[(driver, circuit)])),
                "team_form_pos": _avg(list(team_pos[team])),
                "driver_rest_days": float(rest_days),
                "label": None,
            }
        )

        if rec["status"] == "FINISHED" and pd.notna(rec["finish_position"]):
            pos = float(rec["finish_position"])
            pts = float(rec["points"]) if pd.notna(rec["points"]) else 0.0
            rows[-1]["label"] = pos
            driver_pos[driver].append(pos)
            driver_pts[driver].append(pts)
            circuit_pos[(driver, circuit)].append(pos)
            team_pos[team].append(pos)
            last_date[driver] = start_time

    return pd.DataFrame(rows).set_index("entry_id")
