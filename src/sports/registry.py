"""Build a sport module by name. Mirrors footy.ingest.providers.registry's pattern."""

from __future__ import annotations

from collections.abc import Callable

from sports.contract import SportModule
from sports.f1.adapter import F1Module
from sports.football.adapter import FootballModule

_SPORTS: dict[str, Callable[[], SportModule]] = {
    "f1": F1Module,
    "football": FootballModule,
}


def register_sport(name: str, builder: Callable[[], SportModule]) -> None:
    """Register (or override) a sport module builder under ``name``."""
    _SPORTS[name] = builder


def get_sport(name: str) -> SportModule:
    """Construct the sport module registered under ``name``.

    Raises:
        KeyError: if ``name`` isn't a registered sport.
    """
    builder = _SPORTS.get(name)
    if builder is None:
        raise KeyError(f"Unknown sport '{name}'; known: {sorted(_SPORTS)}")
    return builder()
