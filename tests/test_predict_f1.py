"""predict_f1.py: skips SCHEDULED sessions with no synced entries instead of crashing.

Real bug caught running this in production: a SCHEDULED session has zero
f1_entries rows (sync_season only fetches entries for finished sessions,
OpenF1 has no real lineup for a session that hasn't happened yet) - feeding
that empty slice straight to predict_session() crashed deep inside sklearn's
StandardScaler ("Found array with 0 sample(s)").
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

import predict_f1
from sports.f1.ml.train import train_model
from sports.f1.orm import F1Base, F1Entry, F1Session


@pytest.fixture
def f1_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/predict_f1_test.db")
    import footy.config as config
    import footy.db as db

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()

    F1Base.metadata.create_all(db.get_engine())
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


def test_predict_f1_skips_scheduled_session_with_no_entries(
    f1_db: None, model_dir: Path, caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from footy.db import session_scope

    with session_scope() as session:
        finished = F1Session(
            external_session_id=1, season=2026, round=1, circuit="Bahrain",
            session_type="RACE", start_time=datetime(2026, 3, 1), status="FINISHED",
        )
        session.add(finished)
        session.flush()
        for i in range(1, 5):
            session.add(F1Entry(
                session_id=finished.id, driver_number=i, driver_name=f"D{i}", team="T",
                finish_position=i, status="FINISHED", points=10.0,
            ))
        # The real bug scenario: SCHEDULED session, zero entries synced.
        session.add(F1Session(
            external_session_id=2, season=2026, round=2, circuit="Jeddah",
            session_type="RACE", start_time=datetime(2026, 8, 1), status="SCHEDULED",
        ))

    from sports.f1.data import entries_dataframe

    train_model(entries_dataframe(), "baseline", model_dir=str(model_dir))
    monkeypatch.setattr("sports.f1.ml.predict.F1_MODEL_DIR", str(model_dir))

    with caplog.at_level("WARNING"):
        predict_f1.main()  # must not raise

    assert "No entries synced yet for session" in caplog.text
