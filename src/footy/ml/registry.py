"""Model artifact storage and versioning (joblib).

Artifacts are named ``<model_name>_<UTC timestamp>.pkl`` and a ``<model_name>_latest``
symlink-style pointer file records the current version. This is the seed of the
Phase-3 versioning/rollback machinery.

Example:
    >>> from sklearn.dummy import DummyClassifier
    >>> import numpy as np
    >>> clf = DummyClassifier(strategy="uniform").fit(np.zeros((3, 2)), ["HOME", "DRAW", "AWAY"])
    >>> path = save_model(clf, "demo", model_dir="/tmp/footy-models")  # doctest: +SKIP
    >>> load_latest("demo", model_dir="/tmp/footy-models")  # doctest: +SKIP
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from footy.config import get_settings


def _dir(model_dir: str | None) -> Path:
    path = Path(model_dir or get_settings().model_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_model(model: Any, model_name: str, model_dir: str | None = None) -> Path:
    """Persist ``model`` under a timestamped name and update the ``_latest`` pointer.

    Returns:
        Path to the written artifact.
    """
    root = _dir(model_dir)
    version = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact = root / f"{model_name}_{version}.pkl"
    joblib.dump(model, artifact)
    (root / f"{model_name}_latest").write_text(artifact.name, encoding="utf-8")
    return artifact


def load_latest(model_name: str, model_dir: str | None = None) -> Any:
    """Load the current version of ``model_name``.

    Raises:
        FileNotFoundError: if no model has been saved yet.
    """
    root = _dir(model_dir)
    pointer = root / f"{model_name}_latest"
    if not pointer.exists():
        raise FileNotFoundError(f"No model registered for '{model_name}' in {root}")
    artifact = root / pointer.read_text(encoding="utf-8").strip()
    return joblib.load(artifact)
