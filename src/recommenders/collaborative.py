"""Nearest-neighbour collaborative filtering.

Implements both user-based and item-based CF on a sentiment-blended sparse
rating matrix. We use scikit-learn's NearestNeighbors with cosine distance on
mean-centred ratings, which is equivalent to adjusted cosine similarity for
the user-item case.

For predicting a (user, item) pair:
    pred(u, i) = bar(r_u) + sum_{j in N(i)} sim(i, j) * (r_uj - bar(r_u))
                          / sum_{j in N(i)} |sim(i, j)|
where ``N(i)`` is the set of i's neighbours that user ``u`` has rated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.neighbors import NearestNeighbors

from src.recommenders.base import BaseRecommender
from src.utils import logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_sparse_matrix(
    interactions: pd.DataFrame,
    rating_col: str = "rating",
) -> tuple[sp.csr_matrix, dict[str, int], dict[str, int]]:
    """Build a sparse user x item matrix and index dictionaries."""
    users = interactions["user_id"].astype("category")
    items = interactions["business_id"].astype("category")
    user_to_idx = {u: i for i, u in enumerate(users.cat.categories)}
    item_to_idx = {b: i for i, b in enumerate(items.cat.categories)}
    matrix = sp.csr_matrix(
        (
            interactions[rating_col].astype(np.float32).to_numpy(),
            (users.cat.codes.to_numpy(), items.cat.codes.to_numpy()),
        ),
        shape=(len(user_to_idx), len(item_to_idx)),
    )
    logger.info(
        "Built rating matrix: %d users x %d items, density=%.4f%%",
        matrix.shape[0],
        matrix.shape[1],
        100 * matrix.nnz / max(matrix.shape[0] * matrix.shape[1], 1),
    )
    return matrix, user_to_idx, item_to_idx


def _mean_center_rows(matrix: sp.csr_matrix) -> tuple[sp.csr_matrix, np.ndarray]:
    """Subtract each row's mean (over non-zero entries) and return both."""
    matrix = matrix.tolil()
    means = np.zeros(matrix.shape[0], dtype=np.float32)
    for i in range(matrix.shape[0]):
        row = matrix.rows[i]
        data = matrix.data[i]
        if not row:
            continue
        m = float(np.mean(data))
        means[i] = m
        matrix.data[i] = [v - m for v in data]
    return matrix.tocsr(), means


# ---------------------------------------------------------------------------
# Item-based CF
# ---------------------------------------------------------------------------
class ItemCFRecommender(BaseRecommender):
    """Item-based CF with cosine similarity on centred ratings."""

    name = "item_cf"
    needs_user_history = True

    def __init__(self, k_neighbors: int = 30) -> None:
        self.k = k_neighbors
        self.user_to_idx: dict[str, int] = {}
        self.item_to_idx: dict[str, int] = {}
        self.idx_to_item: list[str] = []
        self.matrix_: sp.csr_matrix | None = None
        self.centred_T_: sp.csr_matrix | None = None
        self.user_means_: np.ndarray | None = None
        self.nn_: NearestNeighbors | None = None

    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "ItemCFRecommender":
        matrix, user_to_idx, item_to_idx = _build_sparse_matrix(interactions)
        centred, user_means = _mean_center_rows(matrix)
        # Transpose so each row is an item; cosine similarity on item rows.
        self.matrix_ = matrix
        self.centred_T_ = centred.T.tocsr()
        self.user_means_ = user_means
        self.user_to_idx = user_to_idx
        self.item_to_idx = item_to_idx
        self.idx_to_item = [None] * len(item_to_idx)  # type: ignore[list-item]
        for b, i in item_to_idx.items():
            self.idx_to_item[i] = b
        k = min(self.k + 1, self.centred_T_.shape[0])
        self.nn_ = NearestNeighbors(
            metric="cosine", algorithm="brute", n_neighbors=k
        )
        self.nn_.fit(self.centred_T_)
        return self

    def _predict_for_user(
        self, user_idx: int, candidate_idx: np.ndarray
    ) -> np.ndarray:
        """Predict centred scores for ``user_idx`` over ``candidate_idx``."""
        assert self.nn_ is not None and self.centred_T_ is not None
        assert self.user_means_ is not None and self.matrix_ is not None

        # Items the user has rated (after centring)
        user_row = self.matrix_.getrow(user_idx)
        rated_idx = user_row.indices
        if len(rated_idx) == 0:
            return np.zeros(len(candidate_idx), dtype=np.float32)
        rated_values = user_row.data - self.user_means_[user_idx]

        # KNN for each candidate item -> distances + indices of similar items.
        distances, neighbors = self.nn_.kneighbors(
            self.centred_T_[candidate_idx], return_distance=True
        )
        sims = 1.0 - distances  # cosine sim

        # For each candidate, sum sim(i, j) * (r_uj - mean_u) where j in neighbours
        rated_set = {idx: v for idx, v in zip(rated_idx, rated_values)}
        preds = np.zeros(len(candidate_idx), dtype=np.float32)
        for row, (sim_row, nbr_row) in enumerate(zip(sims, neighbors)):
            num, den = 0.0, 0.0
            for s, j in zip(sim_row, nbr_row):
                if j in rated_set and s > 0:
                    num += s * rated_set[j]
                    den += abs(s)
            preds[row] = num / den if den > 0 else 0.0
        return preds + self.user_means_[user_idx]

    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
    ) -> pd.DataFrame:
        if user_id is None or user_id not in self.user_to_idx:
            cand = candidates[["business_id"]].copy()
            cand["score"] = 0.0
            return cand.head(top_n)
        user_idx = self.user_to_idx[user_id]

        cand = candidates[["business_id"]].copy()
        cand_idx = np.array(
            [self.item_to_idx[b] for b in cand["business_id"] if b in self.item_to_idx]
        )
        cand = cand[cand["business_id"].isin(self.item_to_idx)].reset_index(drop=True)
        if cand.empty:
            cand["score"] = []
            return cand
        raw = self._predict_for_user(user_idx, cand_idx)
        cand["score"] = self.normalize_rating_scores(raw)
        return cand.sort_values("score", ascending=False).head(top_n).reset_index(
            drop=True
        )

    def score_pairs(
        self, user_id: str | None, business_ids: list[str]
    ) -> pd.Series:
        out = pd.Series(0.0, index=business_ids, dtype=np.float32)
        if user_id is None or user_id not in self.user_to_idx:
            return out
        user_idx = self.user_to_idx[user_id]
        cand_idx = []
        order = []
        for b in business_ids:
            if b in self.item_to_idx:
                cand_idx.append(self.item_to_idx[b])
                order.append(b)
        if not cand_idx:
            return out
        raw = self._predict_for_user(user_idx, np.array(cand_idx))
        out.loc[order] = self.normalize_rating_scores(raw)
        return out


# ---------------------------------------------------------------------------
# User-based CF
# ---------------------------------------------------------------------------
class UserCFRecommender(BaseRecommender):
    """User-based CF with cosine similarity on centred ratings."""

    name = "user_cf"
    needs_user_history = True

    def __init__(self, k_neighbors: int = 30) -> None:
        self.k = k_neighbors
        self.user_to_idx: dict[str, int] = {}
        self.item_to_idx: dict[str, int] = {}
        self.matrix_: sp.csr_matrix | None = None
        self.centred_: sp.csr_matrix | None = None
        self.user_means_: np.ndarray | None = None
        self.nn_: NearestNeighbors | None = None

    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "UserCFRecommender":
        matrix, user_to_idx, item_to_idx = _build_sparse_matrix(interactions)
        centred, user_means = _mean_center_rows(matrix)
        self.matrix_ = matrix
        self.centred_ = centred
        self.user_means_ = user_means
        self.user_to_idx = user_to_idx
        self.item_to_idx = item_to_idx
        k = min(self.k + 1, self.centred_.shape[0])
        self.nn_ = NearestNeighbors(
            metric="cosine", algorithm="brute", n_neighbors=k
        )
        self.nn_.fit(self.centred_)
        return self

    def _predict_for_user(
        self, user_idx: int, candidate_idx: np.ndarray
    ) -> np.ndarray:
        assert self.nn_ is not None and self.centred_ is not None
        assert self.matrix_ is not None and self.user_means_ is not None
        distances, neighbors = self.nn_.kneighbors(
            self.centred_[user_idx], return_distance=True
        )
        sims = (1.0 - distances).ravel()
        nbr = neighbors.ravel()
        # exclude self
        keep = nbr != user_idx
        sims = sims[keep]
        nbr = nbr[keep]

        preds = np.zeros(len(candidate_idx), dtype=np.float32)
        if len(nbr) == 0:
            return preds + self.user_means_[user_idx]

        sub = self.matrix_[nbr][:, candidate_idx].toarray()
        means = self.user_means_[nbr].reshape(-1, 1)
        centred_sub = np.where(sub > 0, sub - means, 0)
        # weights per item = sum |sim| where neighbour has rated that item
        weight = (sub > 0).astype(np.float32) * np.abs(sims).reshape(-1, 1)
        num = (centred_sub * sims.reshape(-1, 1)).sum(axis=0)
        den = weight.sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            preds = np.where(den > 0, num / den, 0.0)
        return preds + self.user_means_[user_idx]

    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
    ) -> pd.DataFrame:
        if user_id is None or user_id not in self.user_to_idx:
            cand = candidates[["business_id"]].copy()
            cand["score"] = 0.0
            return cand.head(top_n)
        user_idx = self.user_to_idx[user_id]
        cand = candidates[candidates["business_id"].isin(self.item_to_idx)].copy()
        if cand.empty:
            cand["score"] = []
            return cand
        cand_idx = np.array(
            [self.item_to_idx[b] for b in cand["business_id"]]
        )
        raw = self._predict_for_user(user_idx, cand_idx)
        cand["score"] = self.normalize_rating_scores(raw)
        return cand.sort_values("score", ascending=False).head(top_n).reset_index(
            drop=True
        )
