"""Tests for the recommender evaluation helpers."""
from __future__ import annotations

import pandas as pd
import pytest

from src.evaluation import train_test_split_interactions


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
