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

from footy.domain import result_from_goals

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
    "home_xg_form",
    "away_xg_form",
    "home_possession_form",
    "away_possession_form",
)


_XG_DEFAULT = 1.3  # ponytail: rough league-average per-team xG; not fit from
                     # real data, just a plausible cold-start value - revisit
                     # if it skews early-season predictions.
_POSSESSION_DEFAULT = 50.0  # neutral - no basis to assume either side dominates
                            # the ball with zero history.


def _avg(values: Sequence[float], default: float = 0.0) -> float:
    return sum(values) / len(values) if values else default


def compute_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Compute leakage-safe features for every row in ``df``.

    Args:
        df: Matches with columns ``id, kickoff, league, home_team, away_team,
            home_goals, away_goals``, plus optionally ``xg_home, xg_away,
            possession_home, possession_away`` (from footy.ingest.stats -
            populated only for finished matches once a separate stats job has
            run; missing columns or null cells are "no stats yet", not an
            error - callers that don't supply them still work). Rows with
            null goals (unplayed) get features from prior history and a null
            ``result``.

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
    xg_for: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    possession: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
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
                "home_xg_form": _avg(list(xg_for[home]), default=_XG_DEFAULT),
                "away_xg_form": _avg(list(xg_for[away]), default=_XG_DEFAULT),
                "home_possession_form": _avg(
                    list(possession[home]), default=_POSSESSION_DEFAULT
                ),
                "away_possession_form": _avg(
                    list(possession[away]), default=_POSSESSION_DEFAULT
                ),
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

        # xG/possession update independently of goals: a separate daily job
        # fetches stats after validate, so a just-finished match may have
        # goals but no stats yet - only real values ever get appended, a
        # lagging fetch just means this match doesn't contribute this round.
        if pd.notna(rec.get("xg_home")):
            xg_for[home].append(float(rec["xg_home"]))
        if pd.notna(rec.get("xg_away")):
            xg_for[away].append(float(rec["xg_away"]))
        if pd.notna(rec.get("possession_home")):
            possession[home].append(float(rec["possession_home"]))
        if pd.notna(rec.get("possession_away")):
            possession[away].append(float(rec["possession_away"]))

    return pd.DataFrame(rows).set_index("id")
