"""Admin page: configure and run the data + training pipeline.

This page is what an operator uses to bootstrap or refresh the system.
Each pipeline stage (preprocess, sentiment, train, evaluate) is a separate
toggle, plus a "Run full pipeline" button. A live progress bar is wired
through ``run_full_pipeline``'s ``progress_cb`` argument.
"""
from __future__ import annotations

import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.components.styles import inject_css, page_header, sidebar_extras, sidebar_logo, status_banner  # noqa: E402
from src.config import (  # noqa: E402
    DEFAULT_CONFIG,
    MODELS_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    PipelineConfig,
)
from src.geo import CITY_CENTROIDS  # noqa: E402
from src.pipeline import (  # noqa: E402
    has_processed_data,
    has_trained_models,
    load_metadata,
    run_full_pipeline,
)


st.set_page_config(page_title="Admin", page_icon="·", layout="wide")
inject_css()
sidebar_logo(ROOT / "app" / "static" / "mcgill_logo.png")
sidebar_extras(user_id=st.session_state.get("selected_user_id"))
page_header(
    "Admin",
    "Run the data pipeline and train the recommenders. Power-user only.",
)

# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------
status_cols = st.columns(3)
with status_cols[0]:
    if has_processed_data():
        status_banner("ok", "Processed data: present")
    else:
        status_banner("warn", "Processed data: missing")
with status_cols[1]:
    if has_trained_models():
        status_banner("ok", "Trained models: present")
    else:
        status_banner("warn", "Trained models: missing")
with status_cols[2]:
    raw_files = list(RAW_DIR.glob("yelp_academic_dataset_*.json"))
    if raw_files:
        status_banner("ok", f"Raw Yelp files: {len(raw_files)} detected")
    else:
        status_banner(
            "warn",
            "Raw Yelp files: none — drop the JSON files into data/raw/ "
            "or generate sample data via the CLI script.",
        )

# ---------------------------------------------------------------------------
# Pipeline configuration form
# ---------------------------------------------------------------------------
st.markdown("### 1. Configure the pipeline")

with st.form("pipeline_config"):
    cfg_left, cfg_right = st.columns(2)

    with cfg_left:
        st.markdown("**Data selection**")
        cities = st.multiselect(
            "Cities",
            options=sorted(CITY_CENTROIDS.keys()),
            default=DEFAULT_CONFIG.cities,
            help="Only restaurants in these cities are loaded. "
            "Fewer cities = faster training.",
        )
        min_user_reviews = st.slider(
            "Min reviews per user",
            min_value=1,
            max_value=50,
            value=DEFAULT_CONFIG.min_user_reviews,
            help="Users with fewer ratings are pruned before training. "
            "Higher values give cleaner CF signal but a smaller user base.",
        )
        min_business_reviews = st.slider(
            "Min reviews per restaurant",
            min_value=1,
            max_value=200,
            value=DEFAULT_CONFIG.min_business_reviews,
        )
        review_sample = st.number_input(
            "Cap on number of reviews (0 = no cap)",
            min_value=0,
            max_value=10_000_000,
            value=0,
            step=10_000,
            help="If your machine struggles, cap the review stream. 0 keeps everything.",
        )

    with cfg_right:
        st.markdown("**Modelling**")
        sentiment_alpha = st.slider(
            "Sentiment blend α (weight on star vs VADER sentiment)",
            min_value=0.0,
            max_value=1.0,
            value=DEFAULT_CONFIG.sentiment_blend_alpha,
            step=0.05,
            help="effective = α · star + (1 - α) · sentiment_star. "
            "α=1 ignores sentiment; α=0 ignores the explicit rating.",
        )
        mf_factors = st.slider(
            "MF latent factors",
            min_value=8,
            max_value=128,
            value=DEFAULT_CONFIG.mf_n_factors,
            step=8,
        )
        mf_epochs = st.slider(
            "MF training epochs",
            min_value=5,
            max_value=60,
            value=DEFAULT_CONFIG.mf_n_epochs,
            step=5,
        )
        st.markdown("**Hybrid weights (auto-normalised)**")
        w_p = st.slider("Personalised", 0.0, 1.0, DEFAULT_CONFIG.weight_personalized, 0.05)
        w_c = st.slider("Content", 0.0, 1.0, DEFAULT_CONFIG.weight_content, 0.05)
        w_o = st.slider("Popularity", 0.0, 1.0, DEFAULT_CONFIG.weight_popularity, 0.05)
        w_d = st.slider("Distance", 0.0, 1.0, DEFAULT_CONFIG.weight_distance, 0.05)

    st.markdown("**Stages to run**")
    stage_cols = st.columns(4)
    run_preprocess = stage_cols[0].checkbox("Preprocess", value=not has_processed_data())
    run_sentiment = stage_cols[1].checkbox("Sentiment", value=not has_processed_data())
    run_train = stage_cols[2].checkbox("Train", value=not has_trained_models())
    run_evaluate = stage_cols[3].checkbox("Evaluate", value=True)

    submitted = st.form_submit_button(
        "▶ Run selected stages",
        use_container_width=True,
        type="primary",
    )

# ---------------------------------------------------------------------------
# Build a PipelineConfig from the form
# ---------------------------------------------------------------------------
def _build_config() -> PipelineConfig:
    return PipelineConfig(
        cities=list(cities) if cities else DEFAULT_CONFIG.cities,
        min_user_reviews=int(min_user_reviews),
        min_business_reviews=int(min_business_reviews),
        review_sample_size=int(review_sample) if review_sample > 0 else None,
        sentiment_blend_alpha=float(sentiment_alpha),
        mf_n_factors=int(mf_factors),
        mf_n_epochs=int(mf_epochs),
        weight_personalized=float(w_p),
        weight_content=float(w_c),
        weight_popularity=float(w_o),
        weight_distance=float(w_d),
    )


# ---------------------------------------------------------------------------
# Run pipeline with progress bar
# ---------------------------------------------------------------------------
if submitted:
    stages: tuple[str, ...] = tuple(
        s
        for s, on in [
            ("preprocess", run_preprocess),
            ("sentiment", run_sentiment),
            ("train", run_train),
            ("evaluate", run_evaluate),
        ]
        if on
    )
    if not stages:
        st.warning("Pick at least one stage to run.")
        st.stop()
    if "evaluate" in stages and "train" not in stages and not has_trained_models():
        st.warning("Cannot evaluate without trained models. Tick 'Train' or run it earlier.")
        st.stop()

    config = _build_config()

    st.markdown("### 2. Pipeline run")
    progress_bar = st.progress(0.0, text="Starting ...")
    log_area = st.empty()
    log_lines: list[str] = []

    def progress_cb(p: float, msg: str) -> None:  # noqa: D401
        progress_bar.progress(min(max(p, 0.0), 1.0), text=msg)
        log_lines.append(f"[{p * 100:5.1f}%] {msg}")
        log_area.code("\n".join(log_lines[-40:]), language="text")

    try:
        result = run_full_pipeline(config=config, stages=stages, progress_cb=progress_cb)
        progress_bar.progress(1.0, text="Done.")
        status_banner("ok", "Pipeline completed successfully.")
        # Bust caches on the other pages
        st.cache_data.clear()
        st.cache_resource.clear()
        if "evaluate" in result:
            st.markdown("#### Evaluation results")
            st.dataframe(result["evaluate"].round(4), use_container_width=True)
    except Exception as exc:  # pragma: no cover - surface to UI
        status_banner("err", f"Pipeline failed: {exc}")
        with st.expander("Traceback"):
            st.code(traceback.format_exc(), language="python")


# ---------------------------------------------------------------------------
# Existing artifacts
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 3. Existing artifacts")

art_left, art_right = st.columns(2)
with art_left:
    st.markdown("**Processed parquet files**")
    parquet_rows = []
    for path in sorted(PROCESSED_DIR.glob("*.parquet")):
        size_mb = path.stat().st_size / (1024 * 1024)
        parquet_rows.append({"file": path.name, "size (MB)": round(size_mb, 2)})
    if parquet_rows:
        st.dataframe(pd.DataFrame(parquet_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("None yet.")

with art_right:
    st.markdown("**Trained models**")
    model_rows = []
    for path in sorted(MODELS_DIR.glob("*.pkl")):
        size_mb = path.stat().st_size / (1024 * 1024)
        model_rows.append({"file": path.name, "size (MB)": round(size_mb, 2)})
    if model_rows:
        st.dataframe(pd.DataFrame(model_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("None yet.")

meta = load_metadata()
if meta:
    st.markdown("**Last training metadata**")
    st.json(meta)

eval_path = MODELS_DIR / "evaluation_results.csv"
if eval_path.exists():
    st.markdown("**Most recent evaluation**")
    df = pd.read_csv(eval_path)
    st.dataframe(df.round(4), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Danger zone
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("⚠️ Danger zone — reset artifacts"):
    st.warning(
        "These actions delete files on disk. They cannot be undone from the UI."
    )
    dz_col1, dz_col2 = st.columns(2)
    with dz_col1:
        if st.button("🗑 Delete trained models"):
            for f in MODELS_DIR.glob("*.pkl"):
                f.unlink()
            for f in MODELS_DIR.glob("*.json"):
                f.unlink()
            for f in MODELS_DIR.glob("*.csv"):
                f.unlink()
            st.cache_resource.clear()
            st.success("Models deleted.")
            st.rerun()
    with dz_col2:
        if st.button("🗑 Delete processed data"):
            for f in PROCESSED_DIR.glob("*.parquet"):
                f.unlink()
            st.cache_data.clear()
            st.success("Processed data deleted.")
            st.rerun()
