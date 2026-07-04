"""Validate predictions for finished matches. Run ~2h after kickoff via cron.

Usage:
    python scripts/validate_predictions.py
"""

from __future__ import annotations

import logging

from footy.predictions.validator import PredictionValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    n = PredictionValidator().validate_finished()
    logging.getLogger("footy.validate").info("Done — %d validated", n)


if __name__ == "__main__":
    main()
