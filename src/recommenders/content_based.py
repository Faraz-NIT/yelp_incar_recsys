"""Content-based recommender.

Each restaurant is represented as a TF-IDF vector over a synthetic
"description" built from its categories, price, and key attributes. We then
compute cosine similarity in one of two modes:

1. ``user_id`` known and has rated items: build a user profile vector as the
   rating-weighted average of items they liked, then score all candidates by
   cosine similarity to that profile (this is the classic Rocchio-style
   approach).
2. ``user_id`` is None (cold start): the caller supplies a seed list of
   preferred cuisines via :meth:`set_preferences`. We then build a profile
   vector from the cuisine tokens directly and rank candidates against it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import ATTRIBUTE_LABELS, PipelineConfig
from src.recommenders.base import BaseRecommender


def _build_description(row: pd.Series) -> str:
    """Construct a description text from the restaurant's structured fields."""
    cats = (row.get("categories") or "").replace(",", " ")
    tokens: list[str] = [cats]
    price = row.get("price_level")
    if isinstance(price, (int, float)) and not pd.isna(price):
        tokens.append("price_" + "$" * int(price))
    for attr_key, label in ATTRIBUTE_LABELS.items():
        attr_col = {
            "RestaurantsTakeOut": "takeout",
            "RestaurantsDelivery": "delivery",
            "RestaurantsReservations": "reservations",
            "OutdoorSeating": "outdoor",
            "GoodForKids": "kids",
            "WheelchairAccessible": "wheelchair",
        }.get(attr_key)
        if attr_col is None or attr_col not in row:
            continue
        if row.get(attr_col) is True:
            tokens.append(label.replace(" ", "_"))
    return " ".join(t for t in tokens if t)


class ContentBasedRecommender(BaseRecommender):
    """TF-IDF cosine recommender with a Rocchio-style user profile."""

    name = "content_based"
    needs_user_history = False  # works in cold-start mode too

    def __init__(self, config: PipelineConfig | None = None) -> None:
        cfg = config or PipelineConfig()
        self.vectorizer = TfidfVectorizer(
            max_features=cfg.content_max_features,
            ngram_range=cfg.content_ngram_range,
            stop_words="english",
            lowercase=True,
        )
        self.item_matrix_: np.ndarray | None = None
        self.business_ids_: list[str] = []
        self.index_: dict[str, int] = {}
        self._user_profiles: dict[str, np.ndarray] = {}
        self._interactions: pd.DataFrame | None = None

    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "ContentBasedRecommender":
        if businesses is None or businesses.empty:
            raise ValueError("ContentBasedRecommender requires businesses.")
        descriptions = businesses.apply(_build_description, axis=1).tolist()
        matrix = self.vectorizer.fit_transform(descriptions)
        self.item_matrix_ = matrix
        self.business_ids_ = businesses["business_id"].tolist()
        self.index_ = {bid: i for i, bid in enumerate(self.business_ids_)}
        self._interactions = interactions
        return self

    # ------------------------------------------------------------------
    # User profile construction
    # ------------------------------------------------------------------
    def _user_profile(self, user_id: str) -> np.ndarray | None:
        if self.item_matrix_ is None or self._interactions is None:
            return None
        if user_id in self._user_profiles:
            return self._user_profiles[user_id]
        hist = self._interactions[self._interactions["user_id"] == user_id]
        if hist.empty:
            return None
        weights: list[float] = []
        rows: list[int] = []
        rating_col = "rating"
        for _, r in hist.iterrows():
            bid = r["business_id"]
            if bid not in self.index_:
                continue
            rows.append(self.index_[bid])
            weights.append(float(r[rating_col]) - 3.0)  # centre on neutral
        if not rows:
            return None
        weights_arr = np.array(weights, dtype=np.float32).reshape(1, -1)
        sub = self.item_matrix_[rows]
        profile = weights_arr @ sub  # (1, n_features)
        norm = np.linalg.norm(profile)
        if norm > 0:
            profile = profile / norm
        self._user_profiles[user_id] = profile
        return profile

    def build_preference_profile(
        self, cuisines: list[str], attributes: list[str] | None = None
    ) -> np.ndarray:
        """Cold-start: build a profile vector from explicit preferences."""
        tokens = " ".join(c.replace(" ", "_") for c in cuisines)
        if attributes:
            tokens += " " + " ".join(a.replace(" ", "_") for a in attributes)
        vec = self.vectorizer.transform([tokens])
        norm = np.linalg.norm(vec.toarray())
        return vec / norm if norm > 0 else vec

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _score_profile(
        self, profile: np.ndarray, candidate_idx: list[int]
    ) -> np.ndarray:
        if self.item_matrix_ is None:
            raise RuntimeError("Call fit() first.")
        sims = cosine_similarity(profile, self.item_matrix_[candidate_idx])
        return sims.ravel().clip(0.0, 1.0)

    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
        preference_profile: np.ndarray | None = None,
    ) -> pd.DataFrame:
        if self.item_matrix_ is None:
            raise RuntimeError("Call fit() first.")
        cand = candidates[["business_id"]].copy()
        cand_idx = [self.index_.get(b, -1) for b in cand["business_id"]]
        mask = [i >= 0 for i in cand_idx]
        cand = cand[mask].reset_index(drop=True)
        cand_idx = [i for i in cand_idx if i >= 0]
        if not cand_idx:
            cand["score"] = []
            return cand

        if preference_profile is not None:
            profile = preference_profile
        elif user_id is not None:
            profile = self._user_profile(user_id)
            if profile is None:
                cand["score"] = 0.0
                return cand.head(top_n)
        else:
            cand["score"] = 0.0
            return cand.head(top_n)

        scores = self._score_profile(profile, cand_idx)
        cand["score"] = scores
        return cand.sort_values("score", ascending=False).head(top_n).reset_index(
            drop=True
        )

    def similar_items(self, business_id: str, top_n: int = 10) -> pd.DataFrame:
        """Find restaurants most similar to a given one (used in the UI)."""
        if business_id not in self.index_:
            return pd.DataFrame(columns=["business_id", "score"])
        idx = self.index_[business_id]
        sims = cosine_similarity(
            self.item_matrix_[idx], self.item_matrix_
        ).ravel()
        sims[idx] = -1  # exclude self
        top = np.argsort(-sims)[:top_n]
        return pd.DataFrame(
            {
                "business_id": [self.business_ids_[i] for i in top],
                "score": sims[top].clip(0, 1),
            }
        )
