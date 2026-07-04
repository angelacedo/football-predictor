"""Fetch fixtures/results from API-Football and upsert into ``matches``.

Example:
    >>> parse_fixture(sample)["home_team"]   # doctest: +SKIP
    'Arsenal'
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

from footy.db import session_scope
from footy.ingest.client import ApiFootball
from footy.orm import Match

log = logging.getLogger("footy.ingest.matches")

FINISHED_STATUSES = {"FT", "AET", "PEN"}


def parse_fixture(item: dict[str, Any]) -> dict[str, Any]:
    """Map an API-Football fixture object to ``matches`` column values."""
    fixture = item["fixture"]
    league = item["league"]
    teams = item["teams"]
    goals = item["goals"]
    status_short = fixture["status"]["short"]
    finished = status_short in FINISHED_STATUSES
    return {
        "api_fixture_id": fixture["id"],
        "league": league["name"],
        "season": league["season"],
        "home_team": teams["home"]["name"],
        "away_team": teams["away"]["name"],
        "kickoff": datetime.fromisoformat(fixture["date"].replace("Z", "+00:00")),
        "status": "FINISHED" if finished else "SCHEDULED",
        "home_goals": goals["home"] if finished else None,
        "away_goals": goals["away"] if finished else None,
    }


def upsert_matches(rows: list[dict[str, Any]]) -> int:
    """Insert new matches or update existing ones (keyed by ``api_fixture_id``).

    Returns:
        Number of rows written (inserted or updated).
    """
    written = 0
    with session_scope() as session:
        for values in rows:
            existing = session.scalar(
                select(Match).where(Match.api_fixture_id == values["api_fixture_id"])
            )
            if existing is None:
                session.add(Match(**values))
            else:
                for key, val in values.items():
                    setattr(existing, key, val)
            written += 1
    log.info("Upserted %d match(es)", written)
    return written


def sync_league(league_id: int, season: int, client: ApiFootball | None = None) -> int:
    """Fetch all fixtures for a league/season and upsert them."""
    api = client or ApiFootball()
    items = api.get("fixtures", {"league": league_id, "season": season})
    return upsert_matches([parse_fixture(i) for i in items])
