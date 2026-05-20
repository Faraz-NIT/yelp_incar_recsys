"""Streaming preprocessor for the Yelp Open Dataset.

The raw Yelp files (notably ``yelp_academic_dataset_review.json``) are large
enough that you cannot load them with ``pd.read_json`` directly. This module
streams them line by line, filters by city, and writes compact parquet files
that subsequent stages consume.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (BUSINESS_PARQUET, INTERACTION_PARQUET, PROCESSED_DIR,
                        RAW_DIR, REVIEW_PARQUET, USER_PARQUET,
                        YELP_BUSINESS_JSON, YELP_REVIEW_JSON, YELP_USER_JSON,
                        PipelineConfig)
from src.utils import logger, safe_get, timed


# ---------------------------------------------------------------------------
# Streaming readers
# ---------------------------------------------------------------------------
def stream_jsonl(
    path: Path,
    keep: Callable[[dict], bool] | None = None,
    fields: list[str] | None = None,
) -> Iterator[dict]:
    """Yield JSON objects from a JSON-lines file, optionally filtered/projected."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing Yelp file: {path}. "
            "Download the dataset from https://www.yelp.com/dataset "
            f"and place it under {RAW_DIR}/."
        )
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if keep is not None and not keep(row):
                continue
            if fields is not None:
                row = {k: row.get(k) for k in fields}
            yield row


def to_dataframe(rows: Iterable[dict], chunk_size: int = 100_000) -> pd.DataFrame:
    """Materialise an iterable of dicts into a DataFrame in chunks."""
    chunks: list[pd.DataFrame] = []
    buffer: list[dict] = []
    for i, row in enumerate(rows, 1):
        buffer.append(row)
        if i % chunk_size == 0:
            chunks.append(pd.DataFrame(buffer))
            buffer.clear()
    if buffer:
        chunks.append(pd.DataFrame(buffer))
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


# ---------------------------------------------------------------------------
# Business preprocessing
# ---------------------------------------------------------------------------
def _is_restaurant(row: dict) -> bool:
    cats = row.get("categories") or ""
    if not cats:
        return False
    cats_lower = cats.lower()
    return "restaurant" in cats_lower or "food" in cats_lower


def _extract_price(attrs: dict | None) -> int | None:
    raw = safe_get(attrs, "RestaurantsPriceRange2")
    if raw is None:
        return None
    try:
        return int(str(raw).strip("'\""))
    except (ValueError, TypeError):
        return None


def _extract_bool_attr(attrs: dict | None, key: str) -> bool | None:
    raw = safe_get(attrs, key)
    if raw is None:
        return None
    val = str(raw).strip("'\"").lower()
    if val in {"true", "1", "yes"}:
        return True
    if val in {"false", "0", "no", "none"}:
        return False
    return None


def load_businesses(cities: list[str], config: PipelineConfig) -> pd.DataFrame:
    """Stream the business file, keeping only restaurants in the target cities."""
    target_cities = {c.strip().lower() for c in cities}
    path = RAW_DIR / YELP_BUSINESS_JSON

    def keep(row: dict) -> bool:
        if not _is_restaurant(row):
            return False
        if row.get("is_open") != 1:
            return False
        city = (row.get("city") or "").strip().lower()
        return city in target_cities

    rows: list[dict] = []
    for row in stream_jsonl(path, keep=keep):
        attrs = row.get("attributes") or {}
        rows.append(
            {
                "business_id": row.get("business_id"),
                "name": row.get("name"),
                "address": row.get("address"),
                "city": row.get("city"),
                "state": row.get("state"),
                "postal_code": row.get("postal_code"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "stars": row.get("stars"),
                "review_count": row.get("review_count", 0),
                "categories": row.get("categories") or "",
                "price_level": _extract_price(attrs),
                "takeout": _extract_bool_attr(attrs, "RestaurantsTakeOut"),
                "delivery": _extract_bool_attr(attrs, "RestaurantsDelivery"),
                "reservations": _extract_bool_attr(attrs, "RestaurantsReservations"),
                "outdoor": _extract_bool_attr(attrs, "OutdoorSeating"),
                "kids": _extract_bool_attr(attrs, "GoodForKids"),
                "wheelchair": _extract_bool_attr(attrs, "WheelchairAccessible"),
                "hours": json.dumps(row.get("hours") or {}),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(
            f"No restaurants found for cities {cities}. "
            "Check spelling against the dataset (e.g. 'Philadelphia', 'Tampa')."
        )

    # Drop those below minimum review threshold
    df = df[df["review_count"] >= config.min_business_reviews].copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude", "business_id"]).reset_index(
        drop=True
    )
    logger.info("Kept %d restaurants across %s", len(df), cities)
    return df


# ---------------------------------------------------------------------------
# Review preprocessing
# ---------------------------------------------------------------------------
def load_reviews(business_ids: set[str], config: PipelineConfig) -> pd.DataFrame:
    """Stream reviews for the given set of business IDs."""
    path = RAW_DIR / YELP_REVIEW_JSON

    def keep(row: dict) -> bool:
        return row.get("business_id") in business_ids

    fields = [
        "review_id",
        "user_id",
        "business_id",
        "stars",
        "date",
        "text",
        "useful",
    ]

    rows: list[dict] = []
    sample_cap = config.review_sample_size
    for row in stream_jsonl(path, keep=keep, fields=fields):
        rows.append(row)
        if sample_cap is not None and len(rows) >= sample_cap:
            break

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No reviews found for the selected restaurants.")
    df["stars"] = pd.to_numeric(df["stars"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["stars", "user_id", "business_id"]).reset_index(drop=True)
    logger.info("Loaded %d reviews", len(df))
    return df


def load_users(user_ids: set[str]) -> pd.DataFrame:
    """Stream user metadata for relevant users only."""
    path = RAW_DIR / YELP_USER_JSON

    def keep(row: dict) -> bool:
        return row.get("user_id") in user_ids

    fields = ["user_id", "name", "review_count", "average_stars", "yelping_since"]
    df = to_dataframe(stream_jsonl(path, keep=keep, fields=fields))
    logger.info("Loaded %d users", len(df))
    return df


# ---------------------------------------------------------------------------
# Iterative pruning + interaction matrix
# ---------------------------------------------------------------------------
def prune_sparse(
    reviews: pd.DataFrame,
    min_user_reviews: int,
    min_business_reviews: int,
    max_iter: int = 5,
) -> pd.DataFrame:
    """Iteratively drop users/businesses with too few interactions (k-core style)."""
    df = reviews.copy()
    for _ in range(max_iter):
        before = len(df)
        user_counts = df["user_id"].value_counts()
        biz_counts = df["business_id"].value_counts()
        df = df[
            df["user_id"].isin(user_counts[user_counts >= min_user_reviews].index)
            & df["business_id"].isin(
                biz_counts[biz_counts >= min_business_reviews].index
            )
        ]
        if len(df) == before:
            break
    logger.info(
        "Pruned reviews: %d -> %d (users=%d, businesses=%d)",
        len(reviews),
        len(df),
        df["user_id"].nunique(),
        df["business_id"].nunique(),
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# End-to-end orchestration
# ---------------------------------------------------------------------------
def run_preprocessing(
    config: PipelineConfig,
    progress_cb: Callable[[float, str], Any] | None = None,
) -> dict[str, Path]:
    """Run the full preprocessing pipeline and write parquet files."""

    def report(p: float, msg: str) -> None:
        logger.info("[%.0f%%] %s", p * 100, msg)
        if progress_cb is not None:
            progress_cb(p, msg)

    report(0.05, f"Loading businesses for {config.cities} ...")
    with timed("load_businesses"):
        businesses = load_businesses(config.cities, config)
    biz_path = PROCESSED_DIR / BUSINESS_PARQUET
    businesses.to_parquet(biz_path, index=False)

    report(0.30, f"Streaming reviews for {len(businesses):,} restaurants ...")
    with timed("load_reviews"):
        reviews = load_reviews(set(businesses["business_id"]), config)

    report(0.55, "Pruning sparse users and businesses ...")
    reviews = prune_sparse(
        reviews,
        min_user_reviews=config.min_user_reviews,
        min_business_reviews=config.min_business_reviews,
    )
    # Keep businesses that survived pruning
    surviving_biz = set(reviews["business_id"])
    businesses = businesses[businesses["business_id"].isin(surviving_biz)].reset_index(
        drop=True
    )
    businesses.to_parquet(biz_path, index=False)

    review_path = PROCESSED_DIR / REVIEW_PARQUET
    reviews.to_parquet(review_path, index=False)

    report(0.75, "Loading user metadata ...")
    with timed("load_users"):
        users = load_users(set(reviews["user_id"]))
    user_path = PROCESSED_DIR / USER_PARQUET
    if not users.empty:
        users.to_parquet(user_path, index=False)

    report(0.90, "Building user-item interaction table ...")
    interactions = (
        reviews.groupby(["user_id", "business_id"], as_index=False)
        .agg(stars=("stars", "mean"), n=("stars", "count"))
        .rename(columns={"stars": "rating"})
    )
    inter_path = PROCESSED_DIR / INTERACTION_PARQUET
    interactions.to_parquet(inter_path, index=False)

    report(1.0, "Preprocessing complete.")
    return {
        "businesses": biz_path,
        "reviews": review_path,
        "users": user_path,
        "interactions": inter_path,
    }


def load_processed() -> dict[str, pd.DataFrame]:
    """Helper to load all processed parquet tables for downstream consumers."""
    out: dict[str, pd.DataFrame] = {}
    for key, fname in [
        ("businesses", BUSINESS_PARQUET),
        ("reviews", REVIEW_PARQUET),
        ("users", USER_PARQUET),
        ("interactions", INTERACTION_PARQUET),
    ]:
        path = PROCESSED_DIR / fname
        if path.exists():
            out[key] = pd.read_parquet(path)
    return out
