"""Matrix factorisation recommender.

Wraps Surprise's SVD with a clean fit/predict interface. Surprise's SVD is the
classic Funk-style biased MF with L2 regularisation, the same model used in
the Netflix Prize. When Surprise is unavailable, falls back to TruncatedSVD on
the centred sparse matrix.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PipelineConfig
from src.recommenders.base import BaseRecommender
from src.utils import logger, timed

try:
    from surprise import SVD, Dataset, Reader
    _HAS_SURPRISE = True
except ImportError:  # pragma: no cover
    _HAS_SURPRISE = False
    logger.warning("Surprise not installed; falling back to TruncatedSVD.")


class MatrixFactorizationRecommender(BaseRecommender):
    """Biased SVD matrix factorisation."""

    name = "matrix_fact"
    needs_user_history = True

    def __init__(self, config: PipelineConfig | None = None) -> None:
        cfg = config or PipelineConfig()
        self.cfg = cfg
        self._model = None
        self._fallback_factors: dict | None = None  # used when no Surprise
        self._global_mean: float = 3.5

    def fit(
        self,
        interactions: pd.DataFrame,
        businesses: pd.DataFrame | None = None,
        reviews: pd.DataFrame | None = None,
    ) -> "MatrixFactorizationRecommender":
        rating_col = "rating"
        self._global_mean = float(interactions[rating_col].mean())

        if _HAS_SURPRISE:
            reader = Reader(rating_scale=(1, 5))
            ds = Dataset.load_from_df(
                interactions[["user_id", "business_id", rating_col]], reader
            )
            train = ds.build_full_trainset()
            self._model = SVD(
                n_factors=self.cfg.mf_n_factors,
                n_epochs=self.cfg.mf_n_epochs,
                lr_all=self.cfg.mf_lr_all,
                reg_all=self.cfg.mf_reg_all,
                random_state=self.cfg.random_state,
            )
            with timed(f"SVD fit (k={self.cfg.mf_n_factors})"):
                self._model.fit(train)
            self._train = train
        else:
            self._fit_fallback(interactions, rating_col)
        return self

    def _fit_fallback(self, interactions: pd.DataFrame, rating_col: str) -> None:
        """TruncatedSVD on centred user-item matrix."""
        import scipy.sparse as sp
        from sklearn.decomposition import TruncatedSVD

        users = interactions["user_id"].astype("category")
        items = interactions["business_id"].astype("category")
        ratings = interactions[rating_col].astype(np.float32).to_numpy()
        matrix = sp.csr_matrix(
            (ratings, (users.cat.codes.to_numpy(), items.cat.codes.to_numpy()))
        )
        svd = TruncatedSVD(
            n_components=min(self.cfg.mf_n_factors, min(matrix.shape) - 1),
            random_state=self.cfg.random_state,
        )
        u_factors = svd.fit_transform(matrix)
        v_factors = svd.components_.T
        self._fallback_factors = {
            "user_to_idx": {u: i for i, u in enumerate(users.cat.categories)},
            "item_to_idx": {b: i for i, b in enumerate(items.cat.categories)},
            "u": u_factors,
            "v": v_factors,
        }

    def _predict(self, user_id: str, business_id: str) -> float:
        if self._model is not None:
            return float(self._model.predict(user_id, business_id).est)
        f = self._fallback_factors
        if f is None:
            return self._global_mean
        ui = f["user_to_idx"].get(user_id)
        vi = f["item_to_idx"].get(business_id)
        if ui is None or vi is None:
            return self._global_mean
        return float(np.dot(f["u"][ui], f["v"][vi]))

    def recommend(
        self,
        user_id: str | None,
        candidates: pd.DataFrame,
        top_n: int = 10,
    ) -> pd.DataFrame:
        cand = candidates[["business_id"]].copy()
        if user_id is None:
            cand["score"] = 0.0
            return cand.head(top_n)
        preds = np.array(
            [self._predict(user_id, b) for b in cand["business_id"]],
            dtype=np.float32,
        )
        cand["score"] = (preds - 1.0) / 4.0
        return cand.sort_values("score", ascending=False).head(top_n).reset_index(
            drop=True
        )

    def score_pairs(
        self, user_id: str | None, business_ids: list[str]
    ) -> pd.Series:
        if user_id is None:
            return pd.Series(0.0, index=business_ids, dtype=np.float32)
        preds = [self._predict(user_id, b) for b in business_ids]
        return pd.Series(
            (np.array(preds) - 1.0) / 4.0,
            index=business_ids,
            dtype=np.float32,
        )
