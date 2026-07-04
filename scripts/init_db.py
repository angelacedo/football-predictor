"""Initialize the database by executing schema.sql.

Usage:
    python scripts/init_db.py
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text

from footy.db import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.init_db")

SCHEMA = Path(__file__).resolve().parent.parent / "schema.sql"


def main() -> None:
    sql = SCHEMA.read_text(encoding="utf-8")
    with get_engine().begin() as conn:
        conn.execute(text(sql))
    log.info("Schema applied from %s", SCHEMA)


if __name__ == "__main__":
    main()
