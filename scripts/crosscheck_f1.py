"""Standalone, manual: compare Jolpica vs OpenF1 RACE results for one season.

NOT wired to the scheduler - cross-checking two providers isn't time-sensitive
the way sync/predict are, and running it on every f1_tick would burn through
Jolpica's rate-limit budget for no operational benefit. Run by hand when you
want a second opinion on a season where both providers overlap (2023+).

Matches sessions by (season, round), not external_session_id - the two
providers use different id schemes (OpenF1's session_key vs Jolpica's
synthetic negative id), so round is the only shared key.

Usage:
    python scripts/crosscheck_f1.py <season>
"""

from __future__ import annotations

import logging
import sys

from sports.f1.ingest.providers.jolpica import JolpicaProvider
from sports.f1.ingest.providers.openf1 import OpenF1Provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("crosscheck_f1")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    season = int(sys.argv[1])

    openf1 = OpenF1Provider()
    jolpica = JolpicaProvider()

    openf1_sessions = {s.round: s for s in openf1.get_sessions(season, "RACE") if s.finished}
    jolpica_sessions = {s.round: s for s in jolpica.get_sessions(season, "RACE") if s.finished}
    shared_rounds = sorted(set(openf1_sessions) & set(jolpica_sessions))
    log.info("Season %d: %d shared finished round(s) to compare", season, len(shared_rounds))

    mismatches = 0
    for round_ in shared_rounds:
        of1_id = openf1_sessions[round_].external_session_id
        jol_id = jolpica_sessions[round_].external_session_id
        openf1_entries = {e.driver_number: e for e in openf1.get_entries(of1_id)}
        jolpica_entries = {e.driver_number: e for e in jolpica.get_entries(jol_id)}
        for driver_number, jol_entry in jolpica_entries.items():
            of1_entry = openf1_entries.get(driver_number)
            if of1_entry is None:
                log.warning(
                    "Round %d: driver #%d in Jolpica, missing from OpenF1", round_, driver_number
                )
                mismatches += 1
                continue
            if of1_entry.finish_position != jol_entry.finish_position:
                log.warning(
                    "Round %d driver #%d: OpenF1 pos=%s vs Jolpica pos=%s",
                    round_, driver_number, of1_entry.finish_position, jol_entry.finish_position,
                )
                mismatches += 1

    log.info("Done - %d mismatch(es) across %d round(s)", mismatches, len(shared_rounds))


if __name__ == "__main__":
    main()
