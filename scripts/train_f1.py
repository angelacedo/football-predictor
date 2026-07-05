"""Train the F1 finishing-position model from synced sessions in the DB.

Usage:
    python scripts/train_f1.py [algorithm] [season]
    python scripts/train_f1.py baseline 2024
"""

from __future__ import annotations

import logging
import sys

from sports.f1.data import entries_dataframe
from sports.f1.ml.train import MODEL_NAME, train_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    algorithm = sys.argv[1] if len(sys.argv) > 1 else MODEL_NAME
    season = int(sys.argv[2]) if len(sys.argv) > 2 else None
    df = entries_dataframe(season=season)
    train_model(df, algorithm)


if __name__ == "__main__":
    main()
