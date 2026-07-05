"""Train (league, model_type) combinations in parallel worker processes."""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from footy.config import get_settings
from footy.data import matches_dataframe
from footy.ml.train import train_model

log = logging.getLogger("footy.ml.train_parallel")


def _train_one(league: str, model_type: str) -> tuple[str, str]:
    key = f"{model_type}_{league.replace(' ', '_')}"
    log.info("worker start: %s", key)
    try:
        df = matches_dataframe(league=league)
        train_model(df, key)
        pointer = Path(get_settings().model_dir) / f"{key}_latest"
        result = str(Path(get_settings().model_dir) / pointer.read_text(encoding="utf-8").strip())
    except Exception as exc:
        result = f"ERROR: {exc}"
    log.info("worker end: %s -> %s", key, result)
    return key, result


def train_all_parallel(
    leagues: list[str], model_types: list[str], workers: int = 4
) -> dict[str, str]:
    """Train every (league, model_type) pair, one worker process per pair.

    Returns:
        Mapping of ``"{model_type}_{league}"`` to its artifact path, or an
        ``"ERROR: ..."`` string if that combination failed.
    """
    results: dict[str, str] = {}
    pairs = [(league, model_type) for league in leagues for model_type in model_types]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_train_one, league, model_type): (league, model_type)
            for league, model_type in pairs
        }
        for future in as_completed(futures):
            key, result = future.result()
            results[key] = result
    return results
