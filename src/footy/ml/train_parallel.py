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


def _train_one(league: str, algorithm: str, df: pd.DataFrame, model_dir: str) -> tuple[str, str]:
    """Run in a worker process — receives an already-filtered DataFrame and the
    model_dir to use, no DB access and no get_settings() call at all in this
    process (a SQLAlchemy engine/session isn't safe to carry across a process
    boundary, and the parent already resolved model_dir once for every worker
    to share). train_model() now takes model_dir directly, so it no longer
    falls back to get_settings() internally either.
    """
    key = f"{algorithm}_{league.replace(' ', '_')}"
    log.info("worker start: %s", key)
    try:
        train_model(df, algorithm, key, model_dir=model_dir)
        pointer = Path(model_dir) / f"{key}_latest"
        result = str(Path(model_dir) / pointer.read_text(encoding="utf-8").strip())
    except Exception as exc:
        result = f"ERROR: {exc}"
    log.info("worker end: %s -> %s", key, result)
    return key, result


def train_all_parallel(
    leagues: list[str], algorithms: list[str], workers: int = 4
) -> dict[str, str]:
    """Train every (league, algorithm) pair, one worker process per pair.

    Matches are fetched per league here, in the parent process; workers only
    ever see the resulting DataFrame and a pre-resolved model_dir.

    Returns:
        Mapping of ``"{algorithm}_{league}"`` to its artifact path, or an
        ``"ERROR: ..."`` string if that combination failed.
    """
    league_frames = {league: matches_dataframe(league=league) for league in leagues}
    model_dir = get_settings().model_dir

    results: dict[str, str] = {}
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _train_one, league, algorithm, league_frames[league], model_dir
            ): (league, algorithm)
            for league in leagues
            for algorithm in algorithms
        }
        for future in as_completed(futures):
            key, result = future.result()
            results[key] = result
    return results
