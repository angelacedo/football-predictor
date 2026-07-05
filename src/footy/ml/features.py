"""Feature engineering for 1X2 prediction.

Features are **leakage-safe by construction**: each match's features are built
only from matches that kicked off strictly earlier. We sweep matches in kickoff
order, snapshot each team's rolling form *before* recording the current result,
then append the result to team history.

Example:
    >>> import pandas as pd
    >>> df = pd.DataFrame([
    ...     {"id": 1, "kickoff": "2024-01-01", "league": "L", "home_team": "A",
    ...      "away_team": "B", "home_goals": 2, "away_goals": 0},
    ...     {"id": 2, "kickoff": "2024-01-08", "league": "L", "home_team": "A",
    ...      "away_team": "C", "home_goals": 1, "away_goals": 1},
    ... ])
    >>> feats = compute_feature_frame(df)
    >>> "home_form_pts" in feats.columns
    True
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Sequence

import pandas as pd

from footy.domain import RESULT_CLASSES, result_from_goals  # noqa: F401 - re-exported for compat

WINDOW = 5  # ponytail: rolling window; the one knob to tune if features underperform.

FEATURE_COLUMNS: tuple[str, ...] = (
    "home_form_pts",
    "away_form_pts",
    "home_gf",
    "home_ga",
    "away_gf",
    "away_ga",
    "home_rest_days",
    "away_rest_days",
)


def _avg(values: Sequence[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def compute_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Compute leakage-safe features for every row in ``df``.

    Args:
        df: Matches with columns ``id, kickoff, league, home_team, away_team,
            home_goals, away_goals``. Rows with null goals (unplayed) get features
            from prior history and a null ``result``.

    Returns:
        DataFrame indexed by match ``id`` with :data:`FEATURE_COLUMNS` plus a
        ``result`` column (1X2 label or ``None`` for unplayed matches).
    """
    data = df.copy()
    data["kickoff"] = pd.to_datetime(data["kickoff"])
    data = data.sort_values("kickoff").reset_index(drop=True)

    # Per-team rolling history: recent points, goals-for, goals-against, last date.
    pts: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    gf: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    ga: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    last_date: dict[str, pd.Timestamp] = {}

    rows: list[dict[str, object]] = []
    for rec in data.to_dict("records"):
        home: str = rec["home_team"]
        away: str = rec["away_team"]
        kickoff: pd.Timestamp = rec["kickoff"]
        h_rest = (kickoff - last_date[home]).days if home in last_date else WINDOW * 7
        a_rest = (kickoff - last_date[away]).days if away in last_date else WINDOW * 7

        rows.append(
            {
                "id": rec["id"],
                "home_form_pts": _avg(list(pts[home])),
                "away_form_pts": _avg(list(pts[away])),
                "home_gf": _avg(list(gf[home])),
                "home_ga": _avg(list(ga[home])),
                "away_gf": _avg(list(gf[away])),
                "away_ga": _avg(list(ga[away])),
                "home_rest_days": float(h_rest),
                "away_rest_days": float(a_rest),
                "result": None,
            }
        )

        # Record result into history *after* snapshotting (no leakage).
        if pd.notna(rec["home_goals"]) and pd.notna(rec["away_goals"]):
            hg, ag = int(rec["home_goals"]), int(rec["away_goals"])
            outcome = result_from_goals(hg, ag)
            rows[-1]["result"] = outcome
            points = {"HOME": (3.0, 0.0), "AWAY": (0.0, 3.0), "DRAW": (1.0, 1.0)}
            h_pts, a_pts = points[outcome]
            pts[home].append(h_pts)
            pts[away].append(a_pts)
            gf[home].append(hg)
            ga[home].append(ag)
            gf[away].append(ag)
            ga[away].append(hg)
            last_date[home] = kickoff
            last_date[away] = kickoff

    return pd.DataFrame(rows).set_index("id")
