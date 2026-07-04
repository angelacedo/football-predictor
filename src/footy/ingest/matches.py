"""Upsert fixtures/results into ``matches``, provider-agnostic.

This module never touches a specific provider's JSON shape — it only consumes
:class:`footy.ingest.schemas.FixtureDTO`. Swap providers via
``FIXTURES_PROVIDER`` in ``.env``; nothing here changes.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from footy.config import get_settings
from footy.db import session_scope
from footy.ingest.providers.base import Provider
from footy.ingest.providers.registry import build_provider
from footy.ingest.schemas import FixtureDTO
from footy.orm import Match

log = logging.getLogger("footy.ingest.matches")


def upsert_matches(fixtures: list[FixtureDTO]) -> int:
    """Insert new matches or update existing ones (keyed by ``api_fixture_id``).

    Returns:
        Number of rows written (inserted or updated).
    """
    written = 0
    with session_scope() as session:
        for fx in fixtures:
            existing = session.scalar(
                select(Match).where(Match.api_fixture_id == fx.external_id)
            )
            values = {
                "api_fixture_id": fx.external_id,
                "league": fx.league,
                "season": fx.season,
                "home_team": fx.home_team,
                "away_team": fx.away_team,
                "kickoff": fx.kickoff,
                "status": "FINISHED" if fx.finished else "SCHEDULED",
                "home_goals": fx.home_goals,
                "away_goals": fx.away_goals,
            }
            if existing is None:
                session.add(Match(**values))
            else:
                for key, val in values.items():
                    setattr(existing, key, val)
            written += 1
    log.info("Upserted %d match(es)", written)
    return written


def sync_league(league_id: int, season: int, provider: Provider | None = None) -> int:
    """Fetch all fixtures for a league/season and upsert them.

    Args:
        league_id: Provider-specific league id.
        season: Season year.
        provider: Fixtures provider; defaults to ``settings.fixtures_provider``.
    """
    active = provider or build_provider(get_settings().fixtures_provider)
    fixtures = active.get_fixtures(league_id, season)
    return upsert_matches(fixtures)
