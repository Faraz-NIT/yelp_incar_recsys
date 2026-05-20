"""Content-based recommender.

Each restaurant is represented as a TF-IDF vector over a synthetic
"description" built from its categories, price, and key attributes. We then
compute cosine similarity in one of two modes:

1. ``user_id`` known and has rated items: build a user profile vector as the
   rating-weighted average of items they liked, then score all candidates by
   cosine similarity to that profile (this is the classic Rocchio-style
   approach).
2. ``user_id`` is None (cold start): the caller supplies a seed list of
   preferred cuisines, attributes, and price levels via
   :meth:`build_preference_profile`. We then build a profile vector from those
   tokens directly and rank candidates against it.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import ATTRIBUTE_LABELS, PipelineConfig
from src.recommenders.base import BaseRecommender


_ATTRIBUTE_COLUMNS = {
    "RestaurantsTakeOut": "takeout",
    "RestaurantsDelivery": "delivery",
    "RestaurantsReservations": "reservations",
    "OutdoorSeating": "outdoor",
    "GoodForKids": "kids",
    "WheelchairAccessible": "wheelchair",
}

_ATTRIBUTE_ALIASES = {
    "takeout": ["takeout", "takeout_available"],
    "delivery": ["delivery", "delivery_available"],
    "reservations": ["reservations", "takes_reservations"],
    "outdoor": ["outdoor", "outdoor_seating"],
    "kids": ["kids", "kid_friendly", "good_for_kids"],
    "wheelchair": ["wheelchair", "wheelchair_accessible"],
}


def _dedupe(tokens: Iterable[str]) -> list[str]:
    """Return tokens in original order without duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for token in tokens:
        token = token.strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _is_true(value: object) -> bool:
    """Return True for common boolean encodings from processed Yelp data."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value == 1)


def _phrase_tokens(value: object) -> list[str]:
    """Build raw and underscore-normalised variants for a label."""
    if value is None:
        return []
    text = str(value).replace("&", " ")
    for ch in ",/()[]{}":
        text = text.replace(ch, " ")
    text = " ".join(text.split()).lower()
    if not text:
        return []
    tokens = [text]
    underscored = text.replace(" ", "_")
    if underscored != text:
        tokens.append(underscored)
    return tokens


def _category_tokens(categories: object) -> list[str]:
    """Create tokens for each Yelp category phrase."""
    if categories is None:
        return []
    return _dedupe(
        token
        for category in str(categories).split(",")
        for token in _phrase_tokens(category)
    )


def _price_tokens(price_level: object) -> list[str]:
    """Create tokenizer-friendly price tokens for TF-IDF."""
    if price_level is None or pd.isna(price_level):
        return []
    try:
        level = int(price_level)
    except (TypeError, ValueError):
        return []
    if level <= 0:
        return []
    return [f"price_{level}", f"price_level_{level}", f"budget_{level}"]


def _preference_price_tokens(price_level: object) -> list[str]:
    """Create compact price tokens for cold-start preference profiles."""
    return _price_tokens(price_level)[:2]


def _attribute_tokens(attribute: str) -> list[str]:
    """Create canonical and label-based tokens for a dining attribute."""
    key = attribute.strip().lower()
    tokens = list(_ATTRIBUTE_ALIASES.get(key, [key]))
    tokens.extend(_phrase_tokens(key))
    return _dedupe(tokens)


def _build_description(row: pd.Series) -> str:
    """Construct a description text from the restaurant's structured fields."""
    tokens: list[str] = _category_tokens(row.get("categories"))
    tokens.extend(_price_tokens(row.get("price_level")))
    for attr_key, label in ATTRIBUTE_LABELS.items():
        attr_col = _ATTRIBUTE_COLUMNS.get(attr_key)
        if attr_col is None or attr_col not in row:
            continue
        if _is_true(row.get(attr_col)):
            tokens.extend(_attribute_tokens(attr_col))
            tokens.extend(_phrase_tokens(label))
    return " ".join(_dedupe(tokens))


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
        self,
        cuisines: list[str],
        attributes: list[str] | None = None,
        price_levels: list[int] | None = None,
    ) -> np.ndarray:
        """Cold-start: build a profile vector from explicit preferences."""
        tokens: list[str] = []
        for cuisine in cuisines:
            # Cuisine is the primary cold-start preference; keep price and
            # dining attributes as secondary tie-breakers.
            tokens.extend(_phrase_tokens(cuisine) * 3)
        if attributes:
            for attribute in attributes:
                tokens.extend(_attribute_tokens(attribute))
        if price_levels:
            for price_level in price_levels:
                tokens.extend(_preference_price_tokens(price_level))
        vec = self.vectorizer.transform([" ".join(tokens)])
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
