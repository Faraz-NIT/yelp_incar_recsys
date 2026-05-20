"""Sentiment-aware rating enrichment.

Yelp ratings are integer stars, but the review text often disagrees with the
star — for example, a 4-star review that nonetheless drips with sarcasm, or a
3-star review that's actually glowing in tone. Many recommender papers
(Kim et al. 2014, He et al. 2018, et al.) show that blending textual sentiment
into the implicit rating signal improves both ranking and cold-start.

We use VADER because it's lexicon-based, fast, and well-tuned for English
short-form text like reviews. The compound score is in [-1, 1]; we rescale it
into a 1-5 star equivalent and blend with the explicit star via ``alpha``:

    effective_rating = alpha * stars + (1 - alpha) * sentiment_star
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError as exc:  # pragma: no cover - import surfacing
    raise ImportError(
        "vaderSentiment is required. Install with `pip install vaderSentiment`."
    ) from exc

from src.utils import logger, timed


def compound_to_star(compound: float) -> float:
    """Map a VADER compound score in [-1, 1] to a star score in [1, 5]."""
    # Linear map: -1 -> 1, 0 -> 3, +1 -> 5
    return 1.0 + (compound + 1.0) * 2.0


def add_sentiment(
    reviews: pd.DataFrame,
    text_col: str = "text",
    alpha: float = 0.7,
    progress_cb: Callable[[float, str], Any] | None = None,
    batch_size: int = 5_000,
) -> pd.DataFrame:
    """Add ``sentiment_compound``, ``sentiment_star`` and ``effective_rating`` columns.

    Parameters
    ----------
    reviews
        DataFrame containing at least ``stars`` and ``text_col``.
    alpha
        Weight on the explicit star. Sentiment-derived star gets (1 - alpha).
        ``alpha=1.0`` ignores sentiment; ``alpha=0.0`` ignores explicit star.
    """
    if reviews.empty:
        # Still emit the expected columns so downstream code can groupby on them
        out = reviews.copy()
        for col in ("sentiment_compound", "sentiment_star", "effective_rating"):
            out[col] = pd.Series(dtype="float32")
        out["sentiment_label"] = pd.Series(dtype="object")
        return out

    df = reviews.copy()
    if text_col not in df.columns:
        df[text_col] = ""

    analyzer = SentimentIntensityAnalyzer()
    n = len(df)
    compounds = np.zeros(n, dtype=np.float32)

    with timed(f"VADER sentiment on {n:,} reviews"):
        texts = df[text_col].fillna("").astype(str).tolist()
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            for i in range(start, end):
                compounds[i] = analyzer.polarity_scores(texts[i])["compound"]
            if progress_cb is not None:
                progress_cb(end / n, f"Sentiment {end:,}/{n:,}")

    df["sentiment_compound"] = compounds
    df["sentiment_star"] = compound_to_star(df["sentiment_compound"])
    df["effective_rating"] = (
        alpha * df["stars"].astype(float) + (1.0 - alpha) * df["sentiment_star"]
    ).clip(1.0, 5.0)

    # Bucket sentiment for analytics
    df["sentiment_label"] = pd.cut(
        df["sentiment_compound"],
        bins=[-1.01, -0.5, -0.05, 0.05, 0.5, 1.01],
        labels=["very_negative", "negative", "neutral", "positive", "very_positive"],
    )

    logger.info(
        "Sentiment: mean=%.3f, median=%.3f, |diff vs star|=%.3f",
        df["sentiment_compound"].mean(),
        df["sentiment_compound"].median(),
        (df["effective_rating"] - df["stars"]).abs().mean(),
    )
    return df


def aggregate_business_sentiment(reviews: pd.DataFrame) -> pd.DataFrame:
    """Per-business sentiment summary (used for ranking and explanations)."""
    if "sentiment_compound" not in reviews.columns:
        raise ValueError("Run add_sentiment() first.")
    agg = (
        reviews.groupby("business_id")
        .agg(
            n_reviews=("review_id", "count"),
            mean_star=("stars", "mean"),
            mean_sentiment=("sentiment_compound", "mean"),
            mean_effective=("effective_rating", "mean"),
            pct_positive=(
                "sentiment_label",
                lambda s: (s.isin(["positive", "very_positive"])).mean(),
            ),
        )
        .reset_index()
    )
    return agg
