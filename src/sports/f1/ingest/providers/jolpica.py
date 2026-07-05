"""Jolpica-F1 (api.jolpi.ca) adapter - Ergast-compatible historical F1 data.

Confirmed live (2026-07-05): real data back to the 1950 season, unauthenticated
rate limit is 4 req/s burst / 500 req/hour sustained (per their own
docs/rate_limits.md - not their search-result summary, which understated it as
200/hour). No pricing tier exists; the docs warn limits "will decrease" once
token auth ships. Their own guidance: batch by season, not by round, and
cache - this adapter and its callers (scripts/backfill_f1_historical.py)
follow that.

Scope: RACE session_type only. Deepens circuit_history_pos (race finishing
position at a circuit across seasons) - the one feature this backfill exists
for. QUALIFYING/SPRINT schedule shapes for old seasons add real complexity
(sprints didn't exist before 2021; some old seasons' Ergast data omits
qualifying dates) for no feature that currently consumes them - out of scope,
get_sessions() raises for those types.

Scoped to 2014+ by design (see backfill_f1_historical.py): before 2014, F1 car
numbers weren't permanent - a number could mean a different driver season to
season, so merging pre-2014 rows into F1Entry.driver_number risks silently
conflating two drivers' histories. Not handled by this adapter; the caller
enforces the cutoff.

Synthetic external_session_id: OpenF1's real session_key is always positive
(session_key, confirmed via every real query this session), so any negative
value here is unambiguously Jolpica-sourced with zero lookup table needed -
no schema change, no new column. The tiering by session_type (_TYPE_ORDER/
_TIER_SIZE below) is deliberate forward-prep, not speculative: it MUST be
decided now, not added later. If RACE alone used `-(season*100+round)` today
and a future task added QUALIFYING under that same bare formula, a qualifying
session and a race session sharing the same (season, round) would collide -
one would silently overwrite the other in the DB (external_session_id is
UNIQUE). Retrofitting the offset after real rows exist would need an ID
migration; baking in the tier from the start costs four lines and avoids that
entirely. Only RACE's tier (0) is ever produced today - QUALIFYING/SPRINT
raise in get_sessions() until actually implemented - but the id space for
them is already reserved and collision-free.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sports.f1.ingest.providers.base import ProviderError
from sports.f1.ingest.schemas import EntryDTO, SessionDTO

_BASE = "https://api.jolpi.ca/ergast/f1"

# Tier index per session_type. base = season*100+round is always < 1_000_000
# (season <= 9999, round < 100), so tiers never overlap - see module docstring.
_TYPE_ORDER = ("RACE", "QUALIFYING", "SPRINT")
_TIER_SIZE = 1_000_000

http_retry = retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)


def jolpica_session_id(season: int, round_: int, session_type: str) -> int:
    """Synthetic F1Session.external_session_id for a Jolpica-sourced session."""
    if session_type not in _TYPE_ORDER:
        raise ProviderError(f"Unknown session_type '{session_type}'")
    tier = _TYPE_ORDER.index(session_type)
    base = season * 100 + round_
    return -(tier * _TIER_SIZE + base)


def decode_jolpica_session_id(external_session_id: int) -> tuple[int, int, str]:
    """Inverse of jolpica_session_id() - (season, round, session_type)."""
    if external_session_id >= 0:
        raise ProviderError(f"{external_session_id} is not a Jolpica-sourced id (must be < 0)")
    magnitude = -external_session_id
    tier, base = divmod(magnitude, _TIER_SIZE)
    season, round_ = divmod(base, 100)
    return season, round_, _TYPE_ORDER[tier]


def _normalize_status(raw_status: str) -> str:
    """Best-effort mapping of Ergast's free-text status field to our enum.

    Not exhaustive - Ergast has dozens of distinct retirement reasons
    ("Engine", "Gearbox", "Accident", ...) - anything not explicitly FINISHED/
    DSQ/DNS falls through to DNF, matching how OpenF1Provider treats any
    non-finish as DNF.
    """
    if raw_status == "Finished" or raw_status.startswith("+"):
        return "FINISHED"
    if raw_status == "Disqualified":
        return "DSQ"
    if raw_status in ("Did not qualify", "Did not start", "Withdrew"):
        return "DNS"
    return "DNF"


class JolpicaProvider:
    name = "jolpica"

    @http_retry
    def _get(self, path: str) -> dict[str, Any]:
        resp = httpx.get(f"{_BASE}/{path}", timeout=15.0)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    def get_sessions(self, season: int, session_type: str = "RACE") -> list[SessionDTO]:
        if session_type != "RACE":
            raise ProviderError(
                f"JolpicaProvider only supports RACE session_type, got '{session_type}'"
            )
        raw = self._get(f"{season}.json")
        races = raw["MRData"]["RaceTable"]["Races"]
        now = datetime.now()
        sessions = []
        for r in races:
            time_str = r.get("time", "00:00:00Z")
            start_time = datetime.fromisoformat(f"{r['date']}T{time_str.replace('Z', '+00:00')}")
            sessions.append(
                SessionDTO(
                    external_session_id=jolpica_session_id(season, int(r["round"]), "RACE"),
                    season=season,
                    round=int(r["round"]),
                    circuit=r["Circuit"]["circuitName"],
                    session_type="RACE",
                    start_time=start_time,
                    finished=start_time.timestamp() < now.timestamp(),
                )
            )
        return sessions

    def get_entries(self, external_session_id: int) -> list[EntryDTO]:
        season, round_, session_type = decode_jolpica_session_id(external_session_id)
        if session_type != "RACE":
            raise ProviderError(f"Unsupported Jolpica session_type '{session_type}'")
        raw = self._get(f"{season}/{round_}/results.json")
        races = raw["MRData"]["RaceTable"]["Races"]
        if not races:
            return []

        entries = []
        for res in races[0]["Results"]:
            driver = res["Driver"]
            status = _normalize_status(res["status"])
            # 2014+ scope only: permanentNumber is stable post-2014; fall back
            # to the race-specific "number" if a response ever omits it.
            driver_number = int(driver.get("permanentNumber") or res["number"])
            entries.append(
                EntryDTO(
                    external_session_id=external_session_id,
                    driver_number=driver_number,
                    driver_name=f"{driver['givenName']} {driver['familyName']}",
                    team=res["Constructor"]["name"],
                    finish_position=int(res["position"]) if status == "FINISHED" else None,
                    status=status,
                    points=float(res["points"]),
                    team_colour=None,  # Jolpica/Ergast has no team_colour field
                )
            )
        return entries
