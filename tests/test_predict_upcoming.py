"""predict_upcoming.py: per-league best-model selection with baseline fallback."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta

import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

import predict_upcoming
from footy.db import session_scope
from footy.ml.features import FEATURE_COLUMNS
from footy.ml.features_worldcup import FEATURE_COLUMNS_WORLDCUP
from footy.ml.registry import save_model
from footy.ml.train import MODEL_NAME
from footy.orm import Base, Match, Prediction


@pytest.fixture
def predict_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/predict_test.db")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "models"))
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


def _dummy(label: str) -> DummyClassifier:
    x = pd.DataFrame([[0.0] * len(FEATURE_COLUMNS)] * 3, columns=list(FEATURE_COLUMNS))
    return DummyClassifier(strategy="constant", constant=label).fit(x, ["HOME", "DRAW", "AWAY"])


def _dummy_worldcup(label: str) -> DummyClassifier:
    cols = list(FEATURE_COLUMNS_WORLDCUP)
    x = pd.DataFrame([[0.0] * len(cols)] * 3, columns=cols)
    return DummyClassifier(strategy="constant", constant=label).fit(x, ["HOME", "DRAW", "AWAY"])


def _add_scheduled_match(league: str, api_fixture_id: int) -> int:
    with session_scope() as session:
        match = Match(
            api_fixture_id=api_fixture_id, league=league, season=2026,
            home_team="A", away_team="B", kickoff=datetime.now(), status="SCHEDULED",
        )
        session.add(match)
        session.flush()
        return match.id


def _add_validated_predictions(
    league: str, model_name: str, n: int, brier: float, kickoff_days_ago: int = 30
) -> None:
    with session_scope() as session:
        for i in range(n):
            m = Match(
                api_fixture_id=10_000 + hash((league, model_name, i)) % 10_000,
                league=league, season=2025, home_team="X", away_team="Y",
                kickoff=datetime.now() - timedelta(days=kickoff_days_ago),
                status="FINISHED", home_goals=1, away_goals=0,
            )
            session.add(m)
            session.flush()
            session.add(
                Prediction(
                    match_id=m.id, model_name=model_name,
                    prob_home_win=0.5, prob_draw=0.3, prob_away_win=0.2,
                    actual_result="HOME", is_correct=True,
                    brier_score=brier, log_loss=0.5,
                    validated_at=datetime.now(),
                )
            )


def test_uses_best_league_model_when_enough_validated_history(predict_db: None) -> None:
    save_model(_dummy("HOME"), MODEL_NAME)
    save_model(_dummy("AWAY"), "xgboost_La_Liga")
    _add_validated_predictions("La Liga", "xgboost_La_Liga", n=10, brier=0.5)

    match_id = _add_scheduled_match("La Liga", api_fixture_id=1)
    predict_upcoming.main()

    with session_scope() as session:
        pred = session.query(Prediction).filter(Prediction.match_id == match_id).one()
    assert pred.model_name == "xgboost_La_Liga"


def test_falls_back_to_baseline_without_enough_validated_history(predict_db: None) -> None:
    save_model(_dummy("HOME"), MODEL_NAME)
    save_model(_dummy("AWAY"), "xgboost_La_Liga")
    _add_validated_predictions("La Liga", "xgboost_La_Liga", n=3, brier=0.1)  # below min_n

    match_id = _add_scheduled_match("La Liga", api_fixture_id=2)
    predict_upcoming.main()

    with session_scope() as session:
        pred = session.query(Prediction).filter(Prediction.match_id == match_id).one()
    assert pred.model_name == MODEL_NAME


def test_world_cup_falls_back_to_baseline_when_no_artifact_file_exists(predict_db: None) -> None:
    """World Cup is never in settings.leagues/train_all, so train_all never
    writes a 'xgboost_World_Cup'-style artifact to disk. If validated rows
    happen to exist under that league/model_name anyway (best_model_per_league
    has no settings.leagues awareness - see predict_upcoming.py docstring),
    the FileNotFoundError catch is what actually protects the fallback."""
    save_model(_dummy("HOME"), MODEL_NAME)
    # Deliberately NOT saving a "xgboost_World_Cup" artifact - matches reality.
    _add_validated_predictions("World Cup", "xgboost_World_Cup", n=10, brier=0.1)

    match_id = _add_scheduled_match("World Cup", api_fixture_id=3)
    predict_upcoming.main()

    with session_scope() as session:
        pred = session.query(Prediction).filter(Prediction.match_id == match_id).one()
    assert pred.model_name == MODEL_NAME


def test_world_cup_uses_its_own_model_when_artifact_exists(predict_db: None) -> None:
    """Once scripts/train_world_cup.py has run, World Cup must use its own
    ranking/host-nation model - not the club baseline, not best_by_league."""
    save_model(_dummy("HOME"), MODEL_NAME)
    save_model(_dummy_worldcup("AWAY"), "baseline_World_Cup")

    match_id = _add_scheduled_match("World Cup", api_fixture_id=4)
    predict_upcoming.main()

    with session_scope() as session:
        pred = session.query(Prediction).filter(Prediction.match_id == match_id).one()
    assert pred.model_name == "baseline_World_Cup"
    # DummyClassifier(constant="AWAY") -> prob_away_win should be the max.
    assert float(pred.prob_away_win) > float(pred.prob_home_win)


def test_world_cup_new_model_replaces_stale_fallback_prediction(predict_db: None) -> None:
    """Real bug found live: a match predicted once via the club-baseline
    fallback, then again later via baseline_World_Cup once trained, must end
    up with exactly one prediction row - not both stacked side by side."""
    save_model(_dummy("HOME"), MODEL_NAME)

    match_id = _add_scheduled_match("World Cup", api_fixture_id=5)
    with session_scope() as session:
        session.add(Prediction(
            match_id=match_id, model_name=MODEL_NAME,
            prob_home_win=0.4, prob_draw=0.3, prob_away_win=0.3,
        ))

    save_model(_dummy_worldcup("AWAY"), "baseline_World_Cup")
    predict_upcoming.main()

    with session_scope() as session:
        preds = session.query(Prediction).filter(Prediction.match_id == match_id).all()
    assert len(preds) == 1
    assert preds[0].model_name == "baseline_World_Cup"
