"""Base abstract recommender class.

All concrete recommenders implement:
- ``fit(interactions, businesses=None, reviews=None)``: build internal state.
- ``recommend(user_id, candidates, top_n=10)``: return a ranked DataFrame
  with at least ``business_id`` and ``score`` columns.

By keeping a single interface, the hybrid recommender can compose them and the
Streamlit page can switch between them with a single dropdown.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseRecommender(ABC):
    """Common interface for every recommender in this project."""

    name: str = "base"
    needs_user_history: bool = True

    @abstractmethod
    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "BaseRecommender":
        ...

    @abstractmethod
    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
    ) -> pd.DataFrame:
        ...

    def score_pairs(
        self, user_id: str | None, business_ids: list[str]
    ) -> pd.Series:
        """Return raw scores for a list of business IDs.

        Default implementation falls back to ``recommend``. Concrete classes
        should override when they can score directly without ranking.
        """
        cand = pd.DataFrame({"business_id": business_ids})
        result = self.recommend(user_id, cand, top_n=len(business_ids))
        return result.set_index("business_id")["score"].reindex(business_ids).fillna(0)
