"""Train (league, algorithm) combinations in parallel worker processes."""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from footy.config import get_settings
from footy.data import matches_dataframe
from footy.ml.train import train_model

log = logging.getLogger("footy.ml.train_parallel")


def _train_one(league: str, algorithm: str, df: pd.DataFrame) -> tuple[str, str]:
    """Run in a worker process — receives an already-filtered DataFrame, no DB access here
    (a SQLAlchemy engine/session isn't safe to carry across a process boundary)."""
    key = f"{algorithm}_{league.replace(' ', '_')}"
    log.info("worker start: %s", key)
    try:
        train_model(df, algorithm, key)
        pointer = Path(get_settings().model_dir) / f"{key}_latest"
        result = str(Path(get_settings().model_dir) / pointer.read_text(encoding="utf-8").strip())
    except Exception as exc:
        result = f"ERROR: {exc}"
    log.info("worker end: %s -> %s", key, result)
    return key, result


def train_all_parallel(
    leagues: list[str], algorithms: list[str], workers: int = 4
) -> dict[str, str]:
    """Train every (league, algorithm) pair, one worker process per pair.

    Matches are fetched per league here, in the parent process; workers only
    ever see the resulting DataFrame.

    Returns:
        Mapping of ``"{algorithm}_{league}"`` to its artifact path, or an
        ``"ERROR: ..."`` string if that combination failed.
    """
    league_frames = {league: matches_dataframe(league=league) for league in leagues}

    results: dict[str, str] = {}
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_train_one, league, algorithm, league_frames[league]): (
                league,
                algorithm,
            )
            for league in leagues
            for algorithm in algorithms
        }
        for future in as_completed(futures):
            key, result = future.result()
            results[key] = result
    return results
