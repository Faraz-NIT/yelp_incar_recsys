"""Shared utilities: logging, persistence, timing."""

from __future__ import annotations

import json
import logging
import pickle
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger("yelp_recsys")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@contextmanager
def timed(label: str) -> Iterator[None]:
    """Log how long a block of code takes."""
    start = time.perf_counter()
    logger.info("▶ %s ...", label)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("✓ %s done in %.2fs", label, elapsed)


def save_pickle(obj: Any, path: Path) -> None:
    """Persist a Python object to disk via pickle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    logger.info("Saved object to %s (%.1f KB)", path, path.stat().st_size / 1024)


def load_pickle(path: Path) -> Any:
    """Load a pickled Python object from disk."""
    with open(path, "rb") as f:
        return pickle.load(f)


def save_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_business_photos(raw_dir: Path) -> dict[str, list[str]]:
    """Return business_id → [photo_id, ...] from Yelp photo.json (NDJSON).

    Tries several common filenames. Returns empty dict if no file found.
    """
    candidates = [
        raw_dir / "photos.json",
        raw_dir / "photo.json",
        raw_dir / "yelp_academic_dataset_photo.json",
    ]
    photo_json: Path | None = next((p for p in candidates if p.exists()), None)
    if photo_json is None:
        return {}

    mapping: dict[str, list[str]] = {}
    with open(photo_json, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                bid = rec.get("business_id", "")
                pid = rec.get("photo_id", "")
                if bid and pid:
                    mapping.setdefault(bid, []).append(pid)
            except json.JSONDecodeError:
                continue
    logger.info("Loaded photo index: %d businesses with photos", len(mapping))
    return mapping


def safe_get(d: dict | None, *keys: str, default: Any = None) -> Any:
    """Drill into nested dicts safely; return default when any key is missing."""
    if d is None:
        return default
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d
