"""Analytics page: model comparison, sentiment distribution, EDA charts."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.components.styles import inject_css, page_header, sidebar_extras, sidebar_logo, status_banner  # noqa: E402
from src.config import MODELS_DIR  # noqa: E402
from src.preprocessing import load_processed  # noqa: E402


st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
inject_css()
sidebar_logo(ROOT / "app" / "static" / "mcgill_logo.png")
sidebar_extras()
page_header("📊 Analytics", "How the data and models actually behave.")


@st.cache_data(show_spinner=False)
def _load_data() -> dict[str, pd.DataFrame]:
    return load_processed()


data = _load_data()
if not data:
    status_banner("warn", "No processed data yet. Run the pipeline from Admin.")
    st.stop()

businesses = data.get("businesses")
reviews = data.get("reviews")
interactions = data.get("interactions")

# ---------------------------------------------------------------------------
# Top metric strip
# ---------------------------------------------------------------------------
mc = st.columns(4)
mc[0].metric("Restaurants", f"{len(businesses):,}" if businesses is not None else "—")
mc[1].metric("Reviews", f"{len(reviews):,}" if reviews is not None else "—")
mc[2].metric(
    "Users", f"{interactions['user_id'].nunique():,}" if interactions is not None else "—"
)
mc[3].metric(
    "Cities",
    businesses["city"].nunique() if businesses is not None and "city" in businesses else "—",
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Model comparison
# ---------------------------------------------------------------------------
eval_path = MODELS_DIR / "evaluation_results.csv"
st.markdown("### 🥊 Model comparison")
if eval_path.exists():
    eval_df = pd.read_csv(eval_path).round(4)
    st.dataframe(eval_df, use_container_width=True, hide_index=True)

    # Bar chart of the headline ranking metric
    ndcg_col = next((c for c in eval_df.columns if c.startswith("ndcg")), None)
    if ndcg_col is not None and "model" in eval_df.columns:
        st.markdown(f"**{ndcg_col} by model**")
        st.bar_chart(eval_df.set_index("model")[ndcg_col])
else:
    status_banner(
        "warn",
        "Evaluation results not found. Run the evaluate stage on the Admin page.",
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Sentiment distribution
# ---------------------------------------------------------------------------
st.markdown("### 💬 Sentiment analysis")
if reviews is not None and "sentiment_compound" in reviews.columns:
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.markdown("**Compound sentiment distribution**")
        hist = pd.cut(
            reviews["sentiment_compound"],
            bins=[-1.0, -0.5, -0.05, 0.05, 0.5, 1.0],
            labels=["very neg", "neg", "neutral", "pos", "very pos"],
        ).value_counts().sort_index()
        st.bar_chart(hist)
    with s_col2:
        st.markdown("**Sentiment vs star rating**")
        sample = reviews[["stars", "sentiment_compound"]].dropna().sample(
            min(5000, len(reviews)), random_state=0
        )
        agg = (
            sample.groupby("stars")["sentiment_compound"]
            .agg(["mean", "std", "count"])
            .round(3)
        )
        st.dataframe(agg, use_container_width=True)
        st.caption(
            "If the relationship is roughly monotonic (higher stars → "
            "higher mean sentiment) the VADER signal is meaningful."
        )

    if "effective_rating" in reviews.columns:
        st.markdown("**Star vs effective (sentiment-blended) rating**")
        ec1, ec2 = st.columns(2)
        ec1.bar_chart(reviews["stars"].value_counts().sort_index())
        ec1.caption("Raw star ratings")
        ec2.bar_chart(
            pd.cut(
                reviews["effective_rating"],
                bins=[1, 2, 3, 4, 5],
                include_lowest=True,
            ).value_counts().sort_index()
        )
        ec2.caption("Effective rating (after sentiment blend)")
else:
    status_banner(
        "warn",
        "Sentiment columns not found on reviews. Run the sentiment stage.",
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Cuisine landscape
# ---------------------------------------------------------------------------
st.markdown("### 🍜 Cuisine landscape")
if businesses is not None and "categories" in businesses.columns:
    cat_counts: dict[str, int] = {}
    for cats in businesses["categories"].dropna():
        for c in str(cats).split(","):
            c = c.strip()
            if c and c.lower() != "restaurants":
                cat_counts[c] = cat_counts.get(c, 0) + 1
    top = (
        pd.Series(cat_counts)
        .sort_values(ascending=False)
        .head(20)
    )
    st.bar_chart(top)
    st.caption("Top 20 cuisine / category tags across the loaded dataset.")

st.markdown("---")

# ---------------------------------------------------------------------------
# User activity distribution
# ---------------------------------------------------------------------------
st.markdown("### 👥 User activity")
if interactions is not None and not interactions.empty:
    per_user = interactions.groupby("user_id").size()
    a_col1, a_col2 = st.columns(2)
    with a_col1:
        st.markdown("**Distribution of ratings per user**")
        bucket = pd.cut(
            per_user,
            bins=[0, 2, 5, 10, 25, 100, 100_000],
            labels=["1-2", "3-5", "6-10", "11-25", "26-100", "100+"],
        ).value_counts().sort_index()
        st.bar_chart(bucket)
    with a_col2:
        st.markdown("**Stats**")
        st.write(
            {
                "mean ratings / user": round(float(per_user.mean()), 2),
                "median ratings / user": int(per_user.median()),
                "max ratings / user": int(per_user.max()),
                "users with ≥ 5 ratings": int((per_user >= 5).sum()),
            }
        )
        sparsity = 1 - (
            len(interactions) / (per_user.size * interactions["business_id"].nunique())
        )
        st.metric("Matrix sparsity", f"{sparsity:.4%}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Geographic spread
# ---------------------------------------------------------------------------
st.markdown("### 🗺️ Geographic spread")
if (
    businesses is not None
    and "latitude" in businesses.columns
    and "longitude" in businesses.columns
):
    geo_df = businesses[["latitude", "longitude"]].dropna()
    st.map(geo_df, size=2)
    st.caption(
        f"{len(geo_df):,} restaurants plotted. Hotspots indicate dense neighbourhoods."
    )
