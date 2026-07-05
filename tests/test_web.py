"""web/app.py - read-only dashboard routes. No DB/network: in-memory SQLite via ORM metadata.

Skipped entirely if the optional `web` extra isn't installed (pip install -e ".[web]"),
since web/ is a separate deployable with its own dependency group.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/web_test.db")
    import footy.config as config
    import footy.db as db

    # get_engine()/_session_factory() are lru_cache'd process-wide - clearing
    # only get_settings() leaves every test after the first reusing the prior
    # test's (deleted) tmp sqlite file, since the cached engine never noticed
    # DATABASE_URL changed.
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()

    from footy.db import get_engine, session_scope
    from footy.orm import Base, Match, Prediction

    Base.metadata.create_all(get_engine())

    with session_scope() as session:
        scheduled = Match(
            api_fixture_id=1, league="La Liga", season=2026, home_team="Real Madrid",
            away_team="Barcelona", kickoff=datetime(2026, 8, 20), status="SCHEDULED",
        )
        finished = Match(
            api_fixture_id=2, league="La Liga", season=2025, home_team="Sevilla",
            away_team="Betis", kickoff=datetime(2025, 9, 1), status="FINISHED",
            home_goals=2, away_goals=1,
        )
        session.add_all([scheduled, finished])
        session.flush()
        session.add(Prediction(
            match_id=scheduled.id, model_name="xgboost_La_Liga",
            prob_home_win=Decimal("0.55"), prob_draw=Decimal("0.25"), prob_away_win=Decimal("0.20"),
        ))
        session.add(Prediction(
            match_id=finished.id, model_name="baseline_La_Liga",
            prob_home_win=Decimal("0.5"), prob_draw=Decimal("0.3"), prob_away_win=Decimal("0.2"),
            actual_result="HOME", is_correct=True, brier_score=Decimal("0.14"),
            log_loss=Decimal("0.36"), validated_at=datetime.now(),
        ))

    import app as web_app

    yield TestClient(web_app.app)
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_shows_counts_and_league(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "La Liga" in resp.text


def test_predictions_shows_scheduled_match_and_model(client: TestClient) -> None:
    resp = client.get("/predictions")
    assert resp.status_code == 200
    assert "Real Madrid" in resp.text
    assert "Barcelona" in resp.text
    assert "xgboost_La_Liga" in resp.text
    assert "Sevilla" not in resp.text  # FINISHED match, not scheduled


def test_predictions_league_filter(client: TestClient) -> None:
    resp = client.get("/predictions", params={"league": "Bundesliga"})
    assert resp.status_code == 200
    assert "Real Madrid" not in resp.text


def test_models_shows_brier_comparison(client: TestClient) -> None:
    resp = client.get("/models")
    assert resp.status_code == 200
    assert "baseline_La_Liga" in resp.text
    assert "0.1400" in resp.text
