"""One-off: drop the legacy F1 tables left behind by the F1 module removal.

The F1 code was removed entirely (2026-07-05); schema.sql no longer creates
these tables, but an already-initialized database still has them. Run once
against such a database, then this script has nothing left to do (IF EXISTS
makes re-runs harmless). Not a scheduled job.

Usage:
    python scripts/drop_f1_tables.py
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from footy.db import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.drop_f1_tables")


def main() -> None:
    # One statement per table, children before parent (both FK to f1_sessions),
    # so no CASCADE is needed and the syntax works on SQLite too, not just
    # Postgres (multi-table DROP is a Postgres extension - caught in testing).
    with get_engine().begin() as conn:
        for table in ("f1_predictions", "f1_entries", "f1_sessions"):
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
    log.info("Dropped f1_predictions, f1_entries, f1_sessions (if they existed)")


if __name__ == "__main__":
    main()
