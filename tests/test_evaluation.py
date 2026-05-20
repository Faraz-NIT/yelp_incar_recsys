"""Tests for the recommender evaluation helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from src.evaluation import (catalog_coverage_at_k, evaluate_ranking,
                            train_test_split_interactions)
from src.recommenders.base import BaseRecommender


def _interactions_for_users(counts: dict[str, int]) -> pd.DataFrame:
    rows = []
    for user_id, n in counts.items():
        for i in range(n):
            rows.append(
                {
                    "user_id": user_id,
                    "business_id": f"{user_id}_b{i}",
                    "rating": 4.0,
                }
            )
    return pd.DataFrame(rows)


class FixedRankRecommender(BaseRecommender):
    """Deterministic ranker for evaluation metric tests."""

    def __init__(self, ranking: list[str]) -> None:
        self.ranking = ranking

    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "FixedRankRecommender":
        return self

    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
    ) -> pd.DataFrame:
        rank = {business_id: i for i, business_id in enumerate(self.ranking)}
        out = candidates[["business_id"]].copy()
        out["_rank"] = out["business_id"].map(rank).fillna(len(rank)).astype(int)
        out = (
            out.sort_values(["_rank", "business_id"]).head(top_n).drop(columns="_rank")
        )
        n = max(len(out), 1)
        out["score"] = [(n - i) / n for i in range(len(out))]
        return out.reset_index(drop=True)


def test_split_holds_out_one_interaction_per_eligible_user():
    interactions = _interactions_for_users({"u_many": 10, "u_min": 4, "u_sparse": 3})

    train, test = train_test_split_interactions(
        interactions,
        min_user_interactions=4,
        random_state=7,
    )

    assert test.groupby("user_id").size().to_dict() == {
        "u_many": 1,
        "u_min": 1,
    }
    assert "u_sparse" not in set(test["user_id"])
    assert train.groupby("user_id").size().to_dict() == {
        "u_many": 9,
        "u_min": 3,
        "u_sparse": 3,
    }


def test_split_can_still_use_percentage_holdout():
    interactions = _interactions_for_users({"u_many": 10})

    train, test = train_test_split_interactions(
        interactions,
        test_size=0.3,
        min_user_interactions=4,
        holdout_per_user=None,
        random_state=7,
    )

    assert len(test) == 3
    assert len(train) == 7


def test_split_rejects_invalid_holdout_count():
    interactions = _interactions_for_users({"u": 4})

    with pytest.raises(ValueError, match="holdout_per_user"):
        train_test_split_interactions(interactions, holdout_per_user=0)


def test_catalog_coverage_at_k_uses_unique_recommended_items():
    assert catalog_coverage_at_k({"b1", "b2"}, catalog_size=5) == 0.4
    assert catalog_coverage_at_k(set(), catalog_size=0) == 0.0


def test_evaluate_ranking_reports_catalog_coverage():
    businesses = pd.DataFrame({"business_id": ["b1", "b2", "b3", "b4", "b5"]})
    train = pd.DataFrame(
        [
            {"user_id": "u1", "business_id": "b4", "rating": 3.0},
            {"user_id": "u2", "business_id": "b5", "rating": 3.0},
        ]
    )
    test = pd.DataFrame(
        [
            {"user_id": "u1", "business_id": "b1", "rating": 5.0},
            {"user_id": "u2", "business_id": "b2", "rating": 5.0},
        ]
    )
    model = FixedRankRecommender(["b1", "b2", "b3", "b4", "b5"])

    metrics = evaluate_ranking(
        model,
        train,
        test,
        businesses,
        k=2,
        n_neg_samples=None,
    )

    assert metrics.coverage == 2 / 5
    assert metrics.as_dict()["coverage@2"] == 2 / 5
