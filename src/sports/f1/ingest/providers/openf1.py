"""OpenF1 (api.openf1.org) adapter - free, no API key, no auth.

Verified live against the real API (2026-07-05):
- GET /v1/sessions?year=Y&session_type=Race returns BOTH the Sprint and the
  full Race for sprint-format weekends, distinguished only by session_name
  ("Race" vs "Sprint") - session_type alone is not enough, hence the
  session_name post-filter below.
- The `limit=` query param is NOT supported - passing it causes a 404 on
  some endpoints (position, starting_grid, session_result, drivers) even
  though the same request without it returns 200. Never send `limit=`.
- `starting_grid` returned "No results found" for every session tried (2023
  and 2024 races) - grid position is not reliably available via this API.
  ponytail: omit grid_position from features until a working source is found;
  MVP trains on rolling form + circuit history only.
- `session_result` is the real endpoint for finishing position/points/DNF
  (not "position", which is a lap-by-lap time series, not a final result).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sports.f1.ingest.providers.base import ProviderError
from sports.f1.ingest.schemas import EntryDTO, SessionDTO

_BASE = "https://api.openf1.org/v1"

_OUR_TO_OPENF1_TYPE = {"QUALIFYING": "Qualifying", "RACE": "Race", "SPRINT": "Race"}
_SESSION_NAME_FOR = {"RACE": "Race", "SPRINT": "Sprint", "QUALIFYING": "Qualifying"}

http_retry = retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)


class OpenF1Provider:
    name = "openf1"

    @http_retry
    def _get(self, path: str, **params: str | int) -> list[dict[str, Any]]:
        resp = httpx.get(f"{_BASE}/{path}", params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    def get_sessions(self, season: int, session_type: str = "RACE") -> list[SessionDTO]:
        if session_type not in _OUR_TO_OPENF1_TYPE:
            raise ProviderError(f"Unknown session_type '{session_type}'")
        raw = self._get("sessions", year=season, session_type=_OUR_TO_OPENF1_TYPE[session_type])
        want_name = _SESSION_NAME_FOR[session_type]
        return [
            SessionDTO(
                external_session_id=s["session_key"],
                season=s["year"],
                round=s["meeting_key"],
                circuit=s["circuit_short_name"],
                session_type=session_type,
                start_time=datetime.fromisoformat(s["date_start"]),
                finished=datetime.fromisoformat(s["date_end"]).timestamp()
                < datetime.now().timestamp(),
            )
            for s in raw
            if s["session_name"] == want_name and not s.get("is_cancelled", False)
        ]

    def get_entries(self, external_session_id: int) -> list[EntryDTO]:
        drivers = self._get("drivers", session_key=external_session_id)
        results = self._get("session_result", session_key=external_session_id)
        if not results:
            return []
        team_by_driver = {d["driver_number"]: d for d in drivers}

        entries = []
        for r in results:
            driver = team_by_driver.get(r["driver_number"], {})
            if r.get("dsq"):
                status = "DSQ"
            elif r.get("dns"):
                status = "DNS"
            elif r.get("dnf"):
                status = "DNF"
            else:
                status = "FINISHED"
            entries.append(
                EntryDTO(
                    external_session_id=external_session_id,
                    driver_number=r["driver_number"],
                    driver_name=driver.get("full_name", f"#{r['driver_number']}"),
                    team=driver.get("team_name", "Unknown"),
                    finish_position=r["position"] if status == "FINISHED" else None,
                    status=status,
                    points=r.get("points"),
                )
            )
        return entries
