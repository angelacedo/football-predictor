"""Train models for multiple leagues/model types in parallel.

Usage:
    python scripts/train_all.py --leagues "La Liga" "Premier League" \\
        --models baseline xgboost --workers 4
"""

from __future__ import annotations

import argparse
import logging

from sqlalchemy import select

from footy.db import session_scope
from footy.ml.train_parallel import train_all_parallel
from footy.orm import Match

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _all_leagues() -> list[str]:
    with session_scope() as session:
        return sorted(session.scalars(select(Match.league).distinct()).all())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leagues", nargs="+", default=None)
    parser.add_argument("--models", nargs="+", default=["baseline", "xgboost"])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    leagues = args.leagues or _all_leagues()
    results = train_all_parallel(leagues, args.models, workers=args.workers)

    width = max(len(k) for k in results) if results else 0
    for key, result in sorted(results.items()):
        print(f"{key.ljust(width)}  {result}")


if __name__ == "__main__":
    main()
