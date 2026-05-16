"""End-to-end pipeline orchestration.

A single ``run_full_pipeline`` callable owns the lifecycle:

    raw JSON → parquet → sentiment-enriched reviews
            → train models → evaluate → persist to disk

Both the CLI script (``scripts/run_pipeline.py``) and the Streamlit admin
page consume this. Progress callbacks let the Streamlit page render a
progress bar.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    DEFAULT_CONFIG,
    INTERACTION_PARQUET,
    MODEL_FILES,
    MODELS_DIR,
    PROCESSED_DIR,
    REVIEW_PARQUET,
    PipelineConfig,
)
from src.evaluation import evaluate_all, train_test_split_interactions
from src.preprocessing import load_processed, run_preprocessing
from src.recommenders import (
    ContentBasedRecommender,
    HybridRecommender,
    ItemCFRecommender,
    MatrixFactorizationRecommender,
    PopularityRecommender,
    UserCFRecommender,
)
from src.sentiment import add_sentiment
from src.utils import load_json, logger, save_json, save_pickle, timed


ProgressCB = Callable[[float, str], Any]


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------
def has_processed_data() -> bool:
    return (PROCESSED_DIR / INTERACTION_PARQUET).exists()


def has_trained_models() -> bool:
    return (MODELS_DIR / MODEL_FILES["popularity"]).exists()


def load_metadata() -> dict:
    path = MODELS_DIR / MODEL_FILES["metadata"]
    return load_json(path) if path.exists() else {}


# ---------------------------------------------------------------------------
# Sentiment stage
# ---------------------------------------------------------------------------
def run_sentiment(
    config: PipelineConfig, progress_cb: ProgressCB | None = None
) -> pd.DataFrame:
    review_path = PROCESSED_DIR / REVIEW_PARQUET
    if not review_path.exists():
        raise FileNotFoundError(
            "Reviews parquet not found. Run preprocessing first."
        )
    reviews = pd.read_parquet(review_path)
    if reviews.empty:
        raise RuntimeError(
            "No reviews to process — the k-core pruning step produced an "
            "empty interaction table. Lower `min_user_reviews` and "
            "`min_business_reviews` (e.g. to 2 and 3) and re-run preprocessing, "
            "or regenerate the sample data with more interactions."
        )
    reviews = add_sentiment(
        reviews,
        alpha=config.sentiment_blend_alpha,
        progress_cb=progress_cb,
    )
    reviews.to_parquet(review_path, index=False)
    # Rebuild interactions with effective rating
    interactions = (
        reviews.groupby(["user_id", "business_id"], as_index=False)
        .agg(
            rating=("effective_rating", "mean"),
            raw_stars=("stars", "mean"),
            sentiment=("sentiment_compound", "mean"),
            n=("stars", "count"),
        )
    )
    interactions.to_parquet(PROCESSED_DIR / INTERACTION_PARQUET, index=False)
    return reviews


# ---------------------------------------------------------------------------
# Training stage
# ---------------------------------------------------------------------------
def train_models(
    config: PipelineConfig,
    progress_cb: ProgressCB | None = None,
) -> dict[str, Any]:
    def report(p: float, msg: str) -> None:
        logger.info("[train %.0f%%] %s", p * 100, msg)
        if progress_cb:
            progress_cb(p, msg)

    data = load_processed()
    if "interactions" not in data or "businesses" not in data:
        raise RuntimeError("Processed data missing. Run preprocessing first.")
    interactions = data["interactions"]
    businesses = data["businesses"]
    reviews = data.get("reviews")

    report(0.05, "Splitting train/test ...")
    train, test = train_test_split_interactions(
        interactions, test_size=config.test_size, random_state=config.random_state
    )

    models: dict[str, Any] = {}

    report(0.15, "Fitting popularity baseline ...")
    with timed("popularity.fit"):
        pop = PopularityRecommender().fit(train, businesses=businesses, reviews=reviews)
    models["popularity"] = pop
    save_pickle(pop, MODELS_DIR / MODEL_FILES["popularity"])

    report(0.30, "Fitting content-based model ...")
    with timed("content.fit"):
        content = ContentBasedRecommender(config).fit(
            train, businesses=businesses, reviews=reviews
        )
    models["content_based"] = content
    save_pickle(content, MODELS_DIR / MODEL_FILES["content_based"])

    report(0.50, "Fitting item-based CF ...")
    with timed("item_cf.fit"):
        item_cf = ItemCFRecommender(k_neighbors=30).fit(train, businesses=businesses)
    models["item_cf"] = item_cf
    save_pickle(item_cf, MODELS_DIR / MODEL_FILES["item_cf"])

    report(0.65, "Fitting user-based CF ...")
    with timed("user_cf.fit"):
        user_cf = UserCFRecommender(k_neighbors=30).fit(train, businesses=businesses)
    models["user_cf"] = user_cf
    save_pickle(user_cf, MODELS_DIR / MODEL_FILES["user_cf"])

    report(0.80, "Fitting matrix factorisation ...")
    with timed("matrix_fact.fit"):
        mf = MatrixFactorizationRecommender(config).fit(
            train, businesses=businesses, reviews=reviews
        )
    models["matrix_fact"] = mf
    save_pickle(mf, MODELS_DIR / MODEL_FILES["matrix_fact"])

    report(0.95, "Saving metadata ...")
    meta = {
        "cities": config.cities,
        "n_users": int(interactions["user_id"].nunique()),
        "n_businesses": int(interactions["business_id"].nunique()),
        "n_interactions": int(len(interactions)),
        "config": {
            "mf_n_factors": config.mf_n_factors,
            "mf_n_epochs": config.mf_n_epochs,
            "sentiment_blend_alpha": config.sentiment_blend_alpha,
            "min_user_reviews": config.min_user_reviews,
            "min_business_reviews": config.min_business_reviews,
        },
    }
    save_json(meta, MODELS_DIR / MODEL_FILES["metadata"])
    report(1.0, "Training complete.")

    return {"models": models, "train": train, "test": test, "metadata": meta}


# ---------------------------------------------------------------------------
# Evaluation stage
# ---------------------------------------------------------------------------
def evaluate_models(
    models: dict[str, Any],
    train: pd.DataFrame,
    test: pd.DataFrame,
    businesses: pd.DataFrame,
    k: int = 10,
    max_users: int | None = 300,
    progress_cb: ProgressCB | None = None,
) -> pd.DataFrame:
    if progress_cb:
        progress_cb(0.1, "Computing per-model metrics ...")
    # Also evaluate the hybrid built from these components
    hybrid = HybridRecommender(
        personalised=models["matrix_fact"],
        content=models["content_based"],
        popularity=models["popularity"],
    )
    full = {**models, "hybrid": hybrid}
    df = evaluate_all(full, train, test, businesses, k=k, max_users=max_users)
    df = df.sort_values(f"ndcg@{k}", ascending=False).reset_index(drop=True)
    metrics_path = MODELS_DIR / "evaluation_results.csv"
    df.to_csv(metrics_path, index=False)
    if progress_cb:
        progress_cb(1.0, f"Saved metrics to {metrics_path}")
    return df


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------
def run_full_pipeline(
    config: PipelineConfig | None = None,
    stages: tuple[str, ...] = ("preprocess", "sentiment", "train", "evaluate"),
    progress_cb: ProgressCB | None = None,
) -> dict[str, Any]:
    """Orchestrate the requested pipeline stages.

    Each stage occupies a slice of the [0, 1] progress range so the UI gets
    smooth movement across the whole run.
    """
    cfg = config or DEFAULT_CONFIG
    bands = {
        "preprocess": (0.00, 0.35),
        "sentiment": (0.35, 0.55),
        "train": (0.55, 0.90),
        "evaluate": (0.90, 1.00),
    }
    bands = {k: v for k, v in bands.items() if k in stages}

    def make_local_cb(stage: str) -> ProgressCB | None:
        if progress_cb is None:
            return None
        lo, hi = bands[stage]

        def inner(p: float, msg: str) -> None:
            progress_cb(lo + (hi - lo) * p, f"[{stage}] {msg}")

        return inner

    result: dict[str, Any] = {}

    if "preprocess" in stages:
        result["preprocess"] = run_preprocessing(cfg, make_local_cb("preprocess"))

    if "sentiment" in stages:
        result["sentiment"] = run_sentiment(cfg, make_local_cb("sentiment"))

    if "train" in stages:
        result["train"] = train_models(cfg, make_local_cb("train"))

    if "evaluate" in stages and "train" in result:
        data = load_processed()
        train_df = result["train"]["train"]
        test_df = result["train"]["test"]
        models = result["train"]["models"]
        result["evaluate"] = evaluate_models(
            models,
            train_df,
            test_df,
            data["businesses"],
            progress_cb=make_local_cb("evaluate"),
        )

    if progress_cb:
        progress_cb(1.0, "All stages complete.")
    return result
