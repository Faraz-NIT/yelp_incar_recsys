"""Hybrid recommender: the actual model used in the in-car demo.

Combines four signals into a single score in [0, 1]:

    final = w_p * personalised
          + w_c * content
          + w_o * popularity
          + w_d * distance

Each component recommender is fit independently on the same training data.
The hybrid wrapper simply orchestrates them and stitches the result.

When the active user has fewer than ``cold_start_review_threshold`` ratings
in the training set, the hybrid automatically rebalances toward content and
popularity (handled outside this class by ``cold_start.adjust_weights``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.config import PipelineConfig
from src.geo import distance_score
from src.recommenders.base import BaseRecommender
from src.recommenders.content_based import ContentBasedRecommender
from src.recommenders.matrix_factorization import \
    MatrixFactorizationRecommender
from src.recommenders.popularity import PopularityRecommender


@dataclass
class HybridWeights:
    personalized: float = 0.45
    content: float = 0.20
    popularity: float = 0.15
    distance: float = 0.20

    def as_array(self) -> np.ndarray:
        arr = np.array(
            [self.personalized, self.content, self.popularity, self.distance],
            dtype=np.float32,
        )
        s = arr.sum()
        return arr / s if s > 0 else arr


class HybridRecommender(BaseRecommender):
    """Late-fusion hybrid combining MF + content + popularity + distance."""

    name = "hybrid"
    needs_user_history = False  # falls back gracefully when cold

    def __init__(
        self,
        personalised: BaseRecommender | None = None,
        content: ContentBasedRecommender | None = None,
        popularity: PopularityRecommender | None = None,
        weights: HybridWeights | None = None,
        config: PipelineConfig | None = None,
    ) -> None:
        cfg = config or PipelineConfig()
        self.cfg = cfg
        self.personalised = personalised or MatrixFactorizationRecommender(cfg)
        self.content = content or ContentBasedRecommender(cfg)
        self.popularity = popularity or PopularityRecommender()
        self.weights = weights or HybridWeights(
            personalized=cfg.weight_personalized,
            content=cfg.weight_content,
            popularity=cfg.weight_popularity,
            distance=cfg.weight_distance,
        )

    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "HybridRecommender":
        self.personalised.fit(interactions, businesses, reviews)
        self.content.fit(interactions, businesses, reviews)
        self.popularity.fit(interactions, businesses, reviews)
        return self

    def _gather_component_scores(
        self,
        user_id: str | None,
        cand: pd.DataFrame,
        preference_profile: np.ndarray | None,
    ) -> pd.DataFrame:
        """Return per-candidate component scores in [0, 1]."""
        biz_ids = cand["business_id"].tolist()
        pers = self.personalised.score_pairs(user_id, biz_ids)
        if preference_profile is not None:
            # Cold start: use the explicit preference profile for content
            cont_df = self.content.recommend(
                user_id=None,
                candidates=cand,
                top_n=len(cand),
                preference_profile=preference_profile,
            )
            cont = cont_df.set_index("business_id")["score"].reindex(biz_ids).fillna(0)
        else:
            cont = self.content.score_pairs(user_id, biz_ids)
        pop = self.popularity.score_pairs(None, biz_ids)
        out = pd.DataFrame(
            {
                "business_id": biz_ids,
                "personalised_score": pers.values,
                "content_score": cont.values,
                "popularity_score": pop.values,
            }
        )
        if "distance_km" in cand.columns:
            out["distance_score"] = distance_score(
                cand["distance_km"].to_numpy(),
                decay_km=self.cfg.distance_decay_km,
            )
        else:
            out["distance_score"] = 1.0
        return out

    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
        weights: HybridWeights | None = None,
        preference_profile: np.ndarray | None = None,
    ) -> pd.DataFrame:
        """Rank candidates by the weighted blend.

        Parameters
        ----------
        candidates
            Must include ``business_id``; if ``distance_km`` is present it is
            used in the distance term, otherwise distance defaults to 1.0.
        weights
            Optional override of the four-way weight vector.
        preference_profile
            Cold-start profile from the content recommender (overrides the
            content signal for users with no history).
        """
        if candidates.empty:
            return candidates.assign(score=pd.Series(dtype=float))

        w = (weights or self.weights).as_array()
        comp = self._gather_component_scores(user_id, candidates, preference_profile)

        # Final weighted score
        score = (
            w[0] * comp["personalised_score"]
            + w[1] * comp["content_score"]
            + w[2] * comp["popularity_score"]
            + w[3] * comp["distance_score"]
        )
        comp["score"] = score
        # Merge with original candidate columns so downstream UI can show
        # everything (name, distance, etc.) without a second join.
        cols_to_drop = [
            "personalised_score",
            "content_score",
            "popularity_score",
            "distance_score",
            "score",
        ]
        merge_cols = [c for c in cols_to_drop if c in candidates.columns]
        cand_clean = candidates.drop(columns=merge_cols)
        merged = cand_clean.merge(comp, on="business_id", how="inner")
        return (
            merged.sort_values("score", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )
