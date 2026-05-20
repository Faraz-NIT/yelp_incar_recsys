"""Cold-start handling.

We distinguish three regimes for a candidate user:

- ``new``        : the user is not in the training set at all
- ``light``      : the user has < ``cold_start_review_threshold`` ratings
- ``established``: the user has enough history that CF/MF are reliable

The strategy by regime:

- ``new``        : build a content profile from explicit cuisine + attribute
                   preferences and shift hybrid weights toward content +
                   popularity.
- ``light``      : keep CF in the mix but down-weight it (mostly content +
                   popularity).
- ``established``: standard hybrid weights.

For new *items* (a restaurant with no reviews yet), CF/MF can't score them.
The content recommender still can, and the popularity score falls back to the
Bayesian prior, so the hybrid degrades gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from src.config import PipelineConfig
from src.recommenders.hybrid import HybridWeights

UserRegime = Literal["new", "light", "established"]


@dataclass
class ColdStartProfile:
    """Captured from the cold-start onboarding wizard in the UI."""

    cuisines: list[str]
    attributes: list[str]
    price_levels: list[int]
    radius_km: float


def classify_user(
    user_id: str | None, interactions: pd.DataFrame, threshold: int = 3
) -> UserRegime:
    """Bucket a user into one of three cold-start regimes."""
    if user_id is None:
        return "new"
    n = int((interactions["user_id"] == user_id).sum())
    if n == 0:
        return "new"
    if n < threshold:
        return "light"
    return "established"


def adjust_weights(base: HybridWeights, regime: UserRegime) -> HybridWeights:
    """Return rebalanced hybrid weights for the given regime."""
    if regime == "established":
        return base
    if regime == "light":
        # Slightly down-weight personalised, up content/popularity
        return HybridWeights(
            personalized=base.personalized * 0.6,
            content=base.content + 0.10,
            popularity=base.popularity + 0.10,
            distance=base.distance,
        )
    # new user: drop personalised entirely, lean on content + popularity
    return HybridWeights(
        personalized=0.0,
        content=base.content + 0.25,
        popularity=base.popularity + 0.20,
        distance=base.distance,
    )


def filter_by_profile(
    businesses: pd.DataFrame, profile: ColdStartProfile | None
) -> pd.DataFrame:
    """Apply hard filters from the cold-start onboarding wizard."""
    if profile is None:
        return businesses
    df = businesses.copy()
    if profile.price_levels:
        df = df[df["price_level"].isin(profile.price_levels) | df["price_level"].isna()]
    if profile.attributes:
        # Each attribute is the column name (takeout, delivery, etc.)
        for attr in profile.attributes:
            if attr in df.columns:
                df = df[df[attr] == True]  # noqa: E712
    return df.reset_index(drop=True)


def get_cold_start_explanation(regime: UserRegime, n_history: int) -> str:
    """Human-readable explanation of why we're in this mode."""
    if regime == "new":
        return (
            "🆕 No rating history found — using your stated cuisine preferences "
            "plus the most popular nearby restaurants."
        )
    if regime == "light":
        return (
            f"🌱 Only {n_history} ratings in history — blending your stated "
            "preferences with collaborative filtering."
        )
    return (
        f"🟢 {n_history} ratings on record — full hybrid model with "
        "collaborative filtering at the centre."
    )


def default_config_threshold(config: PipelineConfig) -> int:
    return config.cold_start_review_threshold
