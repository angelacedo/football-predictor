"""Load F1 DB rows into pandas frames for the ML layer. Mirrors footy.data's pattern."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from footy.db import session_scope
from sports.f1.orm import F1Entry, F1Prediction, F1Session

ENTRY_COLUMNS = (
    "entry_id", "session_id", "start_time", "circuit", "season", "round",
    "driver_number", "driver_name", "team", "finish_position", "status", "points",
)


def entries_dataframe(season: int | None = None) -> pd.DataFrame:
    """Return F1 entries joined to their session, for feature engineering.

    Args:
        season: If given, only entries from this season.
    """
    query = select(
        F1Entry.id, F1Session.id, F1Session.start_time, F1Session.circuit,
        F1Session.season, F1Session.round, F1Entry.driver_number, F1Entry.driver_name,
        F1Entry.team, F1Entry.finish_position, F1Entry.status, F1Entry.points,
    ).join(F1Session, F1Entry.session_id == F1Session.id)
    if season is not None:
        query = query.where(F1Session.season == season)
    with session_scope() as session:
        rows = session.execute(query).all()
    return pd.DataFrame(rows, columns=list(ENTRY_COLUMNS))


def validated_predictions_dataframe() -> pd.DataFrame:
    """Return validated F1 predictions, for metrics."""
    with session_scope() as session:
        rows = session.execute(
            select(
                F1Prediction.model_name, F1Prediction.predicted_position,
                F1Prediction.actual_position, F1Prediction.mae_position,
                F1Session.circuit, F1Session.season,
            )
            .join(F1Session, F1Prediction.session_id == F1Session.id)
            .where(F1Prediction.validated_at.is_not(None))
        ).all()
    df = pd.DataFrame(
        rows,
        columns=["model_name", "predicted_position", "actual_position", "mae_position",
                 "circuit", "season"],
    )
    for col in ("predicted_position", "mae_position"):
        df[col] = df[col].astype(float)
    return df
