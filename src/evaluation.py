"""Recommender evaluation: error-based and ranking-based metrics.

- ``rmse`` / ``mae``: prediction error on held-out (user, item, rating) triples.
- ``precision_at_k`` / ``recall_at_k`` / ``ndcg_at_k``: ranking quality at the
  top-K for each user, treating ratings >= ``relevance_threshold`` as relevant.

Use ``train_test_split_interactions`` for a reproducible per-user holdout split
that guarantees every test user also appears in training (so user-CF/MF can
score them).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.recommenders.base import BaseRecommender


# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------
def train_test_split_interactions(
    interactions: pd.DataFrame,
    test_size: float = 0.2,
    min_user_interactions: int = 4,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-user holdout split.

    Users with fewer than ``min_user_interactions`` ratings are kept entirely
    in the training set so CF can still learn them.
    """
    rng = np.random.default_rng(random_state)
    train_rows: list[pd.DataFrame] = []
    test_rows: list[pd.DataFrame] = []
    for _, group in interactions.groupby("user_id"):
        n = len(group)
        if n < min_user_interactions:
            train_rows.append(group)
            continue
        idx = rng.permutation(n)
        cutoff = max(1, int(n * test_size))
        test_rows.append(group.iloc[idx[:cutoff]])
        train_rows.append(group.iloc[idx[cutoff:]])
    train = pd.concat(train_rows, ignore_index=True)
    test = pd.concat(test_rows, ignore_index=True) if test_rows else interactions.iloc[
        :0
    ].copy()
    return train, test


# ---------------------------------------------------------------------------
# Error metrics
# ---------------------------------------------------------------------------
@dataclass
class ErrorMetrics:
    rmse: float
    mae: float
    n: int

    def as_dict(self) -> dict[str, float | int]:
        return {"rmse": self.rmse, "mae": self.mae, "n": self.n}


def evaluate_error(
    model: BaseRecommender,
    test: pd.DataFrame,
    rating_col: str = "rating",
) -> ErrorMetrics:
    """RMSE / MAE on a held-out (user, item, rating) frame."""
    if test.empty:
        return ErrorMetrics(rmse=float("nan"), mae=float("nan"), n=0)
    preds: list[float] = []
    truths: list[float] = []
    for user_id, group in test.groupby("user_id"):
        biz_list = group["business_id"].tolist()
        scores = model.score_pairs(user_id, biz_list)
        # Recover star-scale prediction by inverting the (r-1)/4 normalisation
        # applied in score_pairs. Score 0 -> 1 star, 1 -> 5 stars.
        preds.extend((scores.values * 4.0 + 1.0).tolist())
        truths.extend(group[rating_col].tolist())
    preds_arr = np.array(preds, dtype=np.float32)
    truths_arr = np.array(truths, dtype=np.float32)
    rmse = float(np.sqrt(mean_squared_error(truths_arr, preds_arr)))
    mae = float(mean_absolute_error(truths_arr, preds_arr))
    return ErrorMetrics(rmse=rmse, mae=mae, n=len(preds))


# ---------------------------------------------------------------------------
# Ranking metrics
# ---------------------------------------------------------------------------
def precision_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = recommended[:k]
    if not top:
        return 0.0
    hits = sum(1 for r in top if r in relevant)
    return hits / k


def recall_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = recommended[:k]
    hits = sum(1 for r in top if r in relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    dcg = 0.0
    for i, item in enumerate(recommended[:k]):
        if item in relevant:
            dcg += 1.0 / np.log2(i + 2)  # ranks start at 1 -> log2(2)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / idcg if idcg > 0 else 0.0


@dataclass
class RankingMetrics:
    precision: float
    recall: float
    ndcg: float
    n_users: int
    k: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            f"precision@{self.k}": self.precision,
            f"recall@{self.k}": self.recall,
            f"ndcg@{self.k}": self.ndcg,
            "n_users_evaluated": self.n_users,
        }


def evaluate_ranking(
    model: BaseRecommender,
    train: pd.DataFrame,
    test: pd.DataFrame,
    businesses: pd.DataFrame,
    k: int = 10,
    relevance_threshold: float = 4.0,
    max_users: int | None = 500,
    rating_col: str = "rating",
) -> RankingMetrics:
    """Top-K ranking metrics by holding out high-rated items per user."""
    if test.empty:
        return RankingMetrics(precision=float("nan"), recall=float("nan"),
                              ndcg=float("nan"), n_users=0, k=k)
    all_biz = businesses["business_id"].tolist()
    precisions, recalls, ndcgs = [], [], []
    users_evaluated = 0

    user_groups: Iterable = test.groupby("user_id")
    if max_users is not None:
        user_groups = list(user_groups)[:max_users]

    for user_id, test_group in user_groups:
        relevant = set(
            test_group.loc[test_group[rating_col] >= relevance_threshold, "business_id"]
        )
        if not relevant:
            continue
        # Don't recommend items the user already rated in training
        seen = set(train.loc[train["user_id"] == user_id, "business_id"])
        cand_ids = [b for b in all_biz if b not in seen]
        if not cand_ids:
            continue
        cand_df = pd.DataFrame({"business_id": cand_ids})
        recs = model.recommend(user_id, cand_df, top_n=k)
        recommended = recs["business_id"].tolist()
        precisions.append(precision_at_k(recommended, relevant, k))
        recalls.append(recall_at_k(recommended, relevant, k))
        ndcgs.append(ndcg_at_k(recommended, relevant, k))
        users_evaluated += 1

    return RankingMetrics(
        precision=float(np.mean(precisions)) if precisions else 0.0,
        recall=float(np.mean(recalls)) if recalls else 0.0,
        ndcg=float(np.mean(ndcgs)) if ndcgs else 0.0,
        n_users=users_evaluated,
        k=k,
    )


def evaluate_all(
    models: dict[str, BaseRecommender],
    train: pd.DataFrame,
    test: pd.DataFrame,
    businesses: pd.DataFrame,
    k: int = 10,
    max_users: int | None = 500,
) -> pd.DataFrame:
    """Run every metric for every model and return one tidy DataFrame."""
    rows: list[dict] = []
    for name, model in models.items():
        err = evaluate_error(model, test)
        rank = evaluate_ranking(
            model, train, test, businesses, k=k, max_users=max_users
        )
        row = {"model": name, **err.as_dict(), **rank.as_dict()}
        rows.append(row)
    return pd.DataFrame(rows)
