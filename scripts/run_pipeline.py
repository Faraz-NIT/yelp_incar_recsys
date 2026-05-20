"""CLI entry point for running the full pipeline.

Examples
--------
Run everything (preprocess, sentiment, train, evaluate) on Philadelphia:

    python scripts/run_pipeline.py --cities Philadelphia

Run only training and evaluation (assuming preprocessing has already happened):

    python scripts/run_pipeline.py --skip preprocess sentiment

Use a smaller MF model for a fast smoke test:

    python scripts/run_pipeline.py --mf-factors 16 --mf-epochs 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make ``src`` importable when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DEFAULT_CONFIG, PipelineConfig  # noqa: E402
from src.pipeline import run_full_pipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the in-car restaurant recsys pipeline")
    p.add_argument("--cities", nargs="+", default=DEFAULT_CONFIG.cities)
    p.add_argument(
        "--min-user-reviews", type=int, default=DEFAULT_CONFIG.min_user_reviews
    )
    p.add_argument(
        "--min-business-reviews", type=int, default=DEFAULT_CONFIG.min_business_reviews
    )
    p.add_argument(
        "--sample-reviews",
        type=int,
        default=None,
        help="Cap on number of reviews loaded (None = all)",
    )
    p.add_argument(
        "--sentiment-alpha", type=float, default=DEFAULT_CONFIG.sentiment_blend_alpha
    )
    p.add_argument("--mf-factors", type=int, default=DEFAULT_CONFIG.mf_n_factors)
    p.add_argument("--mf-epochs", type=int, default=DEFAULT_CONFIG.mf_n_epochs)
    p.add_argument(
        "--skip",
        nargs="+",
        default=[],
        choices=["preprocess", "sentiment", "train", "evaluate"],
        help="Stages to skip",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    config = PipelineConfig(
        cities=args.cities,
        min_user_reviews=args.min_user_reviews,
        min_business_reviews=args.min_business_reviews,
        review_sample_size=args.sample_reviews,
        sentiment_blend_alpha=args.sentiment_alpha,
        mf_n_factors=args.mf_factors,
        mf_n_epochs=args.mf_epochs,
    )
    stages = tuple(
        s
        for s in ("preprocess", "sentiment", "train", "evaluate")
        if s not in args.skip
    )

    def cb(p: float, msg: str) -> None:
        bar = "█" * int(p * 30) + "░" * (30 - int(p * 30))
        print(f"\r[{bar}] {p * 100:5.1f}% {msg[:80]:<80}", end="", flush=True)

    result = run_full_pipeline(config=config, stages=stages, progress_cb=cb)
    print()
    if "evaluate" in result:
        print("\n=== Evaluation results ===")
        print(result["evaluate"].to_string(index=False))


if __name__ == "__main__":
    main()
