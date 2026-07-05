"""Train models for multiple leagues/algorithms in parallel.

Usage:
    python scripts/train_all.py --leagues "La Liga" "Premier League" \\
        --algorithms baseline xgboost --workers 4
"""

from __future__ import annotations

import argparse
import logging

from footy.config import get_settings
from footy.ml.train_parallel import train_all_parallel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--leagues", nargs="+", default=settings.leagues)
    parser.add_argument("--algorithms", nargs="+", default=settings.active_algorithms)
    parser.add_argument("--workers", type=int, default=settings.train_workers)
    args = parser.parse_args()

    results = train_all_parallel(args.leagues, args.algorithms, workers=args.workers)

    width = max(len(k) for k in results) if results else 0
    for key, result in sorted(results.items()):
        print(f"{key.ljust(width)}  {result}")


if __name__ == "__main__":
    main()
