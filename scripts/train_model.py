"""Train the baseline model from matches in the DB.

Usage:
    python scripts/train_model.py
"""

from __future__ import annotations

import logging

from footy.data import matches_dataframe
from footy.ml.train import MODEL_NAME, train_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    df = matches_dataframe()
    train_model(df, MODEL_NAME)


if __name__ == "__main__":
    main()
