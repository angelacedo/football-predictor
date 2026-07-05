"""Load DB rows into pandas frames for the ML layer."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from footy.db import session_scope
from footy.orm import Match, Prediction

MATCH_COLUMNS = (
    "id", "kickoff", "league", "home_team", "away_team", "home_goals", "away_goals"
)


def matches_dataframe(league: str | None = None) -> pd.DataFrame:
    """Return matches as a DataFrame with the columns the feature builder needs.

    Args:
        league: If given, only matches in this league.
    """
    query = select(
        Match.id, Match.kickoff, Match.league, Match.home_team,
        Match.away_team, Match.home_goals, Match.away_goals,
    )
    if league is not None:
        query = query.where(Match.league == league)
    with session_scope() as session:
        rows = session.execute(query).all()
    return pd.DataFrame(rows, columns=list(MATCH_COLUMNS))


def validated_predictions_dataframe() -> pd.DataFrame:
    """Return validated predictions joined to their match league, for metrics."""
    with session_scope() as session:
        rows = session.execute(
            select(
                Prediction.prob_home_win, Prediction.prob_draw, Prediction.prob_away_win,
                Prediction.actual_result, Prediction.is_correct,
                Prediction.brier_score, Prediction.log_loss, Match.league,
            )
            .join(Match, Prediction.match_id == Match.id)
            .where(Prediction.validated_at.is_not(None))
        ).all()
    df = pd.DataFrame(
        rows,
        columns=[
            "prob_home_win", "prob_draw", "prob_away_win", "actual_result",
            "is_correct", "brier_score", "log_loss", "league",
        ],
    )
    for col in ("prob_home_win", "prob_draw", "prob_away_win", "brier_score", "log_loss"):
        df[col] = df[col].astype(float)
    return df
