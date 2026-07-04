"""Common contract every data provider adapter satisfies.

A provider does not have to support all three capabilities (e.g. The Odds API
has no fixtures endpoint). Adapters that skip a capability inherit
:class:`UnsupportedProviderMixin`'s default, which raises :class:`ProviderError`
naming the gap — callers see one exception type whether a provider errored or
simply doesn't do that job.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from footy.ingest.schemas import AdvancedStatsDTO, FixtureDTO, OddsDTO, OddsQuery


def to_naive_utc(dt: datetime) -> datetime:
    """Normalize a datetime to naive UTC for cross-provider comparison.

    ``matches.kickoff`` is stored as a naive ``TIMESTAMP`` (see schema.sql), but
    provider JSON often carries a tz-aware kickoff/commence time. Comparing the
    two directly raises ``TypeError: can't subtract offset-naive and
    offset-aware datetimes`` — normalize both sides through this first.
    """
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo is not None else dt


# Shared retry policy for adapter HTTP calls: 3 attempts, exponential backoff,
# only on transport/5xx-class failures. Apply as a decorator on each adapter's
# network method, e.g. ``@http_retry`` above a ``def _get(...)``.
http_retry = retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)


class ProviderError(Exception):
    """A provider call failed, or the provider doesn't support the capability."""


class Provider(Protocol):
    """Structural contract for a data-provider adapter."""

    name: str

    def get_fixtures(self, league_id: int, season: int) -> list[FixtureDTO]:
        """Return fixtures for a league/season."""
        ...

    def get_odds(self, query: OddsQuery) -> list[OddsDTO]:
        """Return 1X2 odds (all bookmakers) for a fixture."""
        ...

    def get_advanced_stats(self, external_fixture_id: int) -> AdvancedStatsDTO | None:
        """Return xG/possession for a fixture, or None if unavailable."""
        ...


class UnsupportedProviderMixin:
    """Default 'not supported by this provider' implementations.

    Concrete adapters mix this in and override only the capabilities they
    actually have, keeping each adapter file focused on what its API offers.
    """

    name: str

    def get_fixtures(self, league_id: int, season: int) -> list[FixtureDTO]:
        raise ProviderError(f"{self.name} does not support fixtures")

    def get_odds(self, query: OddsQuery) -> list[OddsDTO]:
        raise ProviderError(f"{self.name} does not support odds")

    def get_advanced_stats(self, external_fixture_id: int) -> AdvancedStatsDTO | None:
        raise ProviderError(f"{self.name} does not support advanced stats")
