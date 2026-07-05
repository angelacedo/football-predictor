"""FootballModule: SportModule contract wraps existing footy.* functions, no logic duplication."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import sports.football.adapter as football_adapter
from sports.football.adapter import FootballModule
from sports.registry import get_sport


def _matches_df() -> pd.DataFrame:
    rows = [
        {
            "id": i, "kickoff": f"2024-01-{(i % 28) + 1:02d}", "league": "La Liga",
            "home_team": f"T{i % 4}", "away_team": f"T{(i + 1) % 4}",
            "home_goals": i % 3, "away_goals": (i + 1) % 3,
        }
        for i in range(1, 30)
    ]
    return pd.DataFrame(rows)


def test_get_sport_football_returns_football_module() -> None:
    module = get_sport("football")
    assert isinstance(module, FootballModule)
    assert module.name == "football"


def test_sync_delegates_to_sync_league_with_league_id_from_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setattr(
        football_adapter, "sync_league",
        lambda league_id, season, provider: calls.append((league_id, season, provider)) or 42,
    )
    written = FootballModule().sync(2025, provider=None, league_id=140)
    assert written == 42
    assert calls == [(140, 2025, None)]


def test_sync_without_league_id_raises() -> None:
    with pytest.raises(ValueError, match="league_id"):
        FootballModule().sync(2025)


def test_compute_features_delegates_to_compute_feature_frame() -> None:
    result = FootballModule().compute_features(_matches_df())
    from footy.ml.features import FEATURE_COLUMNS

    for col in FEATURE_COLUMNS:
        assert col in result.columns


def test_train_delegates_to_train_model(model_dir: Path) -> None:
    FootballModule().train(_matches_df(), "baseline", "baseline_test", model_dir=str(model_dir))
    assert (model_dir / "baseline_test_latest").exists()


def test_predict_delegates_to_predict_match(model_dir: Path) -> None:
    module = FootballModule()
    df = _matches_df()
    module.train(df, "baseline", "baseline", model_dir=str(model_dir))

    from footy.ml.registry import load_latest

    model = load_latest("baseline", model_dir=str(model_dir))
    probs = module.predict(df, entity_id=1, model=model)

    from footy.ml.predict import MatchProbs

    assert isinstance(probs, MatchProbs)
    assert round(sum(probs.as_tuple()), 4) == 1.0
