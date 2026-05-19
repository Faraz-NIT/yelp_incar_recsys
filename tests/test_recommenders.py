"""Smoke tests for the recommenders.

These run on a tiny synthetic dataset so they execute in seconds. They're
not benchmarks — they verify each recommender fits and returns a
well-formed DataFrame with the agreed interface.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import PipelineConfig
from src.recommenders import (
    BaseRecommender,
    ContentBasedRecommender,
    HybridRecommender,
    ItemCFRecommender,
    MatrixFactorizationRecommender,
    PopularityRecommender,
    UserCFRecommender,
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def synthetic_data() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(42)
    n_users, n_biz = 25, 40

    user_ids = [f"u{i:03d}" for i in range(n_users)]
    biz_ids = [f"b{i:03d}" for i in range(n_biz)]
    cuisines = ["Italian", "Japanese", "Mexican", "Indian", "Burgers"]

    businesses = pd.DataFrame(
        {
            "business_id": biz_ids,
            "name": [f"Place {i}" for i in range(n_biz)],
            "categories": [
                f"Restaurants, {rng.choice(cuisines)}, {rng.choice(cuisines)}"
                for _ in range(n_biz)
            ],
            "stars": rng.uniform(2.5, 5.0, n_biz).round(1),
            "review_count": rng.integers(10, 500, n_biz),
            "latitude": 40.0 + rng.uniform(-0.1, 0.1, n_biz),
            "longitude": -75.0 + rng.uniform(-0.1, 0.1, n_biz),
            "city": "Philadelphia",
            "price_level": rng.integers(1, 5, n_biz),
            "takeout": rng.choice([True, False], n_biz),
            "delivery": rng.choice([True, False], n_biz),
            "outdoor": rng.choice([True, False], n_biz),
            "kids": rng.choice([True, False], n_biz),
        }
    )

    rows = []
    for u in user_ids:
        n = rng.integers(4, 10)
        chosen = rng.choice(biz_ids, size=n, replace=False)
        for b in chosen:
            rows.append(
                {
                    "user_id": u,
                    "business_id": b,
                    "rating": float(rng.choice([3, 4, 4, 5, 5])),
                }
            )
    interactions = pd.DataFrame(rows)
    return {"businesses": businesses, "interactions": interactions}


# ---------------------------------------------------------------------------
# Per-recommender smoke tests
# ---------------------------------------------------------------------------
def test_popularity_recommender(synthetic_data):
    rec = PopularityRecommender().fit(
        synthetic_data["interactions"], businesses=synthetic_data["businesses"]
    )
    out = rec.recommend(
        user_id=None, candidates=synthetic_data["businesses"], top_n=5
    )
    assert len(out) == 5
    assert "score" in out.columns
    assert out["score"].between(0, 1).all()


def test_content_recommender(synthetic_data):
    rec = ContentBasedRecommender(PipelineConfig()).fit(
        synthetic_data["interactions"], businesses=synthetic_data["businesses"]
    )
    user = synthetic_data["interactions"]["user_id"].iloc[0]
    out = rec.recommend(user, synthetic_data["businesses"], top_n=5)
    assert len(out) <= 5
    assert "score" in out.columns


def test_item_cf(synthetic_data):
    rec = ItemCFRecommender(k_neighbors=5).fit(
        synthetic_data["interactions"], businesses=synthetic_data["businesses"]
    )
    user = synthetic_data["interactions"]["user_id"].iloc[0]
    out = rec.recommend(user, synthetic_data["businesses"], top_n=5)
    assert isinstance(out, pd.DataFrame)
    assert out["score"].between(0, 1).all()


def test_user_cf(synthetic_data):
    rec = UserCFRecommender(k_neighbors=5).fit(
        synthetic_data["interactions"], businesses=synthetic_data["businesses"]
    )
    user = synthetic_data["interactions"]["user_id"].iloc[0]
    out = rec.recommend(user, synthetic_data["businesses"], top_n=5)
    assert isinstance(out, pd.DataFrame)
    assert out["score"].between(0, 1).all()


def test_rating_score_normalization_clips_bounds():
    scores = BaseRecommender.normalize_rating_scores([0.5, 1.0, 3.0, 5.0, 6.0])
    assert np.allclose(scores, [0.0, 0.0, 0.5, 1.0, 1.0])


def test_matrix_factorization(synthetic_data):
    cfg = PipelineConfig(mf_n_factors=8, mf_n_epochs=3)
    rec = MatrixFactorizationRecommender(cfg).fit(
        synthetic_data["interactions"], businesses=synthetic_data["businesses"]
    )
    user = synthetic_data["interactions"]["user_id"].iloc[0]
    out = rec.recommend(user, synthetic_data["businesses"], top_n=5)
    assert len(out) <= 5


def test_hybrid_end_to_end(synthetic_data):
    cfg = PipelineConfig(mf_n_factors=8, mf_n_epochs=3)
    hybrid = HybridRecommender(config=cfg).fit(
        synthetic_data["interactions"], businesses=synthetic_data["businesses"]
    )
    cand = synthetic_data["businesses"].copy()
    cand["distance_km"] = np.random.uniform(0.5, 10, len(cand))

    user = synthetic_data["interactions"]["user_id"].iloc[0]
    out = hybrid.recommend(user, cand, top_n=5)
    assert len(out) == 5
    assert "score" in out.columns
    # Component scores must be present
    for col in ("personalised_score", "content_score", "popularity_score", "distance_score"):
        assert col in out.columns
    # Scores must be sorted descending
    assert (out["score"].diff().dropna() <= 0).all()


def test_hybrid_cold_start(synthetic_data):
    """A user not in training should still produce ranked candidates."""
    hybrid = HybridRecommender(config=PipelineConfig(mf_n_factors=8, mf_n_epochs=3)).fit(
        synthetic_data["interactions"], businesses=synthetic_data["businesses"]
    )
    cand = synthetic_data["businesses"].copy()
    cand["distance_km"] = np.random.uniform(0.5, 10, len(cand))
    out = hybrid.recommend(user_id="brand_new_user", candidates=cand, top_n=5)
    assert len(out) == 5
    assert out["score"].notna().all()
