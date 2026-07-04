"""Provider-agnostic DTOs.

``matches.py``/``odds.py``/``stats.py`` consume only these — never a specific
provider's raw JSON shape. Each provider adapter is responsible for mapping its
own API response into these types.

Example:
    >>> FixtureDTO(external_id=1, league="EPL", season=2024, home_team="A",
    ...             away_team="B", kickoff=None, finished=False,
    ...             home_goals=None, away_goals=None)  # doctest: +SKIP
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FixtureDTO:
    """A single fixture, normalized across providers."""

    external_id: int
    league: str
    season: int
    home_team: str
    away_team: str
    kickoff: datetime
    finished: bool
    home_goals: int | None
    away_goals: int | None


@dataclass(frozen=True)
class OddsQuery:
    """Lookup key for odds.

    Carries both the fixtures-provider's numeric id *and* team names/kickoff,
    because odds providers don't all share an id scheme with the fixtures
    provider. API-Football keys off ``external_fixture_id``; The Odds API has
    its own event ids and must match on team names + kickoff instead.
    Each adapter uses whichever field its API actually supports.
    """

    external_fixture_id: int
    home_team: str
    away_team: str
    kickoff: datetime


@dataclass(frozen=True)
class OddsDTO:
    """1X2 (Match Winner) decimal odds from one bookmaker for one fixture."""

    external_fixture_id: int
    bookmaker: str
    odds_home: float
    odds_draw: float
    odds_away: float
    is_closing: bool = False


@dataclass(frozen=True)
class AdvancedStatsDTO:
    """Advanced per-match stats (xG, possession). Any field may be unavailable."""

    external_fixture_id: int
    xg_home: float | None = None
    xg_away: float | None = None
    possession_home: float | None = None
    possession_away: float | None = None
