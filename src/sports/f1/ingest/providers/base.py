"""Common contract every F1 data-provider adapter satisfies.

Mirrors footy.ingest.providers.base's Protocol+mixin pattern, but with F1's
own DTO shape - not reused from footy, since F1 fixtures/results aren't 1X2.
"""

from __future__ import annotations

from typing import Protocol

from sports.f1.ingest.schemas import EntryDTO, SessionDTO


class ProviderError(Exception):
    """An F1 provider call failed, or the provider doesn't support the capability."""


class F1Provider(Protocol):
    """Structural contract for an F1 data-provider adapter."""

    name: str

    def get_sessions(self, season: int, session_type: str = "Race") -> list[SessionDTO]:
        """Return sessions for a season (session_type: Race|Qualifying|Sprint)."""
        ...

    def get_entries(self, external_session_id: int) -> list[EntryDTO]:
        """Return each driver's entry/result for one session."""
        ...
