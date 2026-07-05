"""footy.data: matches_dataframe's stats-column coercion (NULL/Decimal -> float/NaN)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

import pandas as pd
import pytest

from footy.data import matches_dataframe
from footy.db import session_scope
from footy.orm import Base, Match


@pytest.fixture
def data_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/data_test.db")
    import footy.config as config
    import footy.db as db

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()

    Base.metadata.create_all(db.get_engine())
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


def test_matches_dataframe_includes_stats_columns(data_db: None) -> None:
    with session_scope() as session:
        session.add(Match(
            api_fixture_id=1, league="La Liga", season=2025, home_team="A", away_team="B",
            kickoff=datetime(2025, 1, 1), status="FINISHED", home_goals=2, away_goals=0,
            xg_home=Decimal("2.10"), xg_away=Decimal("0.40"),
            possession_home=Decimal("58.00"), possession_away=Decimal("42.00"),
        ))

    df = matches_dataframe("La Liga")
    row = df.iloc[0]
    assert row["xg_home"] == pytest.approx(2.10)
    assert row["possession_away"] == pytest.approx(42.00)
    assert isinstance(row["xg_home"], float)


def test_matches_dataframe_null_stats_become_nan_not_error(data_db: None) -> None:
    with session_scope() as session:
        session.add(Match(
            api_fixture_id=2, league="La Liga", season=2025, home_team="C", away_team="D",
            kickoff=datetime(2025, 1, 2), status="FINISHED", home_goals=1, away_goals=1,
        ))

    df = matches_dataframe("La Liga")
    assert pd.isna(df.iloc[0]["xg_home"])
    assert pd.isna(df.iloc[0]["possession_home"])
