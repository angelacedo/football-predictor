"""Build an F1 provider instance by name. Mirrors footy.ingest.providers.registry."""

from __future__ import annotations

from collections.abc import Callable

from sports.f1.ingest.providers.base import F1Provider, ProviderError
from sports.f1.ingest.providers.openf1 import OpenF1Provider

_BUILDERS: dict[str, Callable[[], F1Provider]] = {
    "openf1": OpenF1Provider,
}


def build_provider(name: str) -> F1Provider:
    """Construct the F1 provider adapter registered under ``name``.

    Raises:
        ProviderError: if ``name`` isn't a known provider.
    """
    builder = _BUILDERS.get(name)
    if builder is None:
        raise ProviderError(f"Unknown F1 provider '{name}'; known: {sorted(_BUILDERS)}")
    return builder()
