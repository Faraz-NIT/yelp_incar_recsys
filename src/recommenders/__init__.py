"""Recommender implementations: popularity, content, CF, MF, hybrid."""

from src.recommenders.base import BaseRecommender
from src.recommenders.collaborative import ItemCFRecommender, UserCFRecommender
from src.recommenders.content_based import ContentBasedRecommender
from src.recommenders.hybrid import HybridRecommender
from src.recommenders.matrix_factorization import \
    MatrixFactorizationRecommender
from src.recommenders.popularity import PopularityRecommender

__all__ = [
    "BaseRecommender",
    "PopularityRecommender",
    "ContentBasedRecommender",
    "UserCFRecommender",
    "ItemCFRecommender",
    "MatrixFactorizationRecommender",
    "HybridRecommender",
]
