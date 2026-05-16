"""Popularity baseline using a Bayesian (smoothed) average.

A naive "highest stars" baseline is biased toward restaurants with a single
5-star review. We instead use the IMDB-style Bayesian average:

    score = (v / (v + m)) * R + (m / (v + m)) * C

where ``R`` is the restaurant's mean rating, ``v`` is its review count,
``C`` is the global mean rating, and ``m`` is a smoothing prior (e.g. the
median review count).

This is non-personalised, but it doubles as the cold-start fallback when we
have nothing else to go on.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.recommenders.base import BaseRecommender


class PopularityRecommender(BaseRecommender):
    """Smoothed popularity ranker."""

    name = "popularity"
    needs_user_history = False

    def __init__(self, smoothing_quantile: float = 0.5) -> None:
        self.smoothing_quantile = smoothing_quantile
        self.scores_: pd.Series | None = None
        self.global_mean_: float = 0.0
        self.prior_count_: float = 0.0

    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "PopularityRecommender":
        if businesses is None:
            raise ValueError("PopularityRecommender requires the businesses table.")

        rating_col = "effective_rating" if reviews is not None and \
            "effective_rating" in reviews.columns else None

        if rating_col and reviews is not None:
            agg = (
                reviews.groupby("business_id")
                .agg(R=(rating_col, "mean"), v=(rating_col, "count"))
                .reset_index()
            )
        else:
            agg = businesses[["business_id", "stars", "review_count"]].rename(
                columns={"stars": "R", "review_count": "v"}
            )

        C = float(agg["R"].mean())
        m = float(np.quantile(agg["v"], self.smoothing_quantile))

        bayes = (agg["v"] / (agg["v"] + m)) * agg["R"] + (m / (agg["v"] + m)) * C
        # Normalise to [0, 1] so it can be combined in the hybrid.
        scores = (bayes - 1.0) / 4.0  # stars are in [1, 5]
        self.scores_ = pd.Series(
            scores.values.astype(float), index=agg["business_id"], name="score"
        )
        self.global_mean_ = C
        self.prior_count_ = m
        return self

    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
    ) -> pd.DataFrame:
        if self.scores_ is None:
            raise RuntimeError("Call fit() first.")
        cand = candidates[["business_id"]].copy()
        cand["score"] = cand["business_id"].map(self.scores_).fillna(0.0)
        return cand.sort_values("score", ascending=False).head(top_n).reset_index(
            drop=True
        )

    def score_pairs(
        self, user_id: str | None, business_ids: list[str]
    ) -> pd.Series:
        if self.scores_ is None:
            raise RuntimeError("Call fit() first.")
        return self.scores_.reindex(business_ids).fillna(0.0)
