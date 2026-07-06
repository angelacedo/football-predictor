"""Load DB rows into pandas frames for the ML layer."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from footy.db import session_scope
from footy.orm import Match, Prediction

MATCH_COLUMNS = (
    "id", "kickoff", "league", "season", "home_team", "away_team", "home_goals", "away_goals",
    "xg_home", "xg_away", "possession_home", "possession_away",
)
_STATS_COLUMNS = ("xg_home", "xg_away", "possession_home", "possession_away")


def matches_dataframe(league: str | None = None) -> pd.DataFrame:
    """Return matches as a DataFrame with the columns the feature builder needs.

    Args:
        league: If given, only matches in this league.
    """
    query = select(
        Match.id, Match.kickoff, Match.league, Match.season, Match.home_team,
        Match.away_team, Match.home_goals, Match.away_goals,
        Match.xg_home, Match.xg_away, Match.possession_home, Match.possession_away,
    )
    if league is not None:
        query = query.where(Match.league == league)
    with session_scope() as session:
        rows = session.execute(query).all()
    df = pd.DataFrame(rows, columns=list(MATCH_COLUMNS))
    # to_numeric not astype(float): most matches have NULL stats (no stats
    # job has run for them yet, or the fetch found nothing) - astype(float)
    # raises on None, to_numeric coerces it to NaN like every other null
    # column here.
    for col in _STATS_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def validated_predictions_dataframe() -> pd.DataFrame:
    """Return validated predictions joined to their match league/model/kickoff,
    for metrics (kickoff is used to window current-vs-baseline periods for
    degradation checks, not just to display)."""
    with session_scope() as session:
        rows = session.execute(
            select(
                Prediction.prob_home_win, Prediction.prob_draw, Prediction.prob_away_win,
                Prediction.actual_result, Prediction.is_correct,
                Prediction.brier_score, Prediction.log_loss, Match.league,
                Prediction.model_name, Match.kickoff,
            )
            .join(Match, Prediction.match_id == Match.id)
            .where(Prediction.validated_at.is_not(None))
        ).all()
    df = pd.DataFrame(
        rows,
        columns=[
            "prob_home_win", "prob_draw", "prob_away_win", "actual_result",
            "is_correct", "brier_score", "log_loss", "league", "model_name", "kickoff",
        ],
    )
    for col in ("prob_home_win", "prob_draw", "prob_away_win", "brier_score", "log_loss"):
        df[col] = df[col].astype(float)
    return df
