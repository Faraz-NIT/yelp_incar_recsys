"""Analytics page: model comparison, sentiment distribution, EDA charts."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from app.components.styles import inject_css, page_header, render_dock, render_topnav, status_banner  # noqa: E402
from src.config import MODELS_DIR, PROCESSED_DIR, REVIEW_PARQUET  # noqa: E402
from src.preprocessing import load_processed  # noqa: E402


st.set_page_config(page_title="Analytics", page_icon="·", layout="wide", initial_sidebar_state="collapsed")
inject_css()
render_topnav("analytics")
page_header("Analytics", "How the data and models actually behave.")


def _processed_mtime() -> float:
    """Max mtime across processed parquet files — used as a cache-bust key."""
    from src.config import BUSINESS_PARQUET, INTERACTION_PARQUET
    files = [
        PROCESSED_DIR / REVIEW_PARQUET,
        PROCESSED_DIR / BUSINESS_PARQUET,
        PROCESSED_DIR / INTERACTION_PARQUET,
    ]
    mtimes = [f.stat().st_mtime for f in files if f.exists()]
    return max(mtimes) if mtimes else 0.0


@st.cache_data(show_spinner=False)
def _load_data(mtime: float) -> dict[str, pd.DataFrame]:  # noqa: ARG001
    return load_processed()


data = _load_data(_processed_mtime())
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
_MODEL_LABELS = {
    "popularity":    "Popularity",
    "content_based": "Content-Based",
    "item_cf":       "Item-CF",
    "user_cf":       "User-CF",
    "matrix_fact":   "ALS",
    "hybrid":        "Hybrid",
}
# Plotly theme colours matching app palette
_ACCENT   = "#c8553d"
_PALETTE  = ["#c8553d", "#0f1f3d", "#8e8aa6", "#a8422a", "#b7b1c6", "#2a3856"]

eval_path = MODELS_DIR / "evaluation_results.csv"
st.markdown("### Model comparison")
if eval_path.exists():
    eval_df = pd.read_csv(eval_path).round(4)
    eval_df["Model"] = eval_df["model"].map(_MODEL_LABELS).fillna(eval_df["model"])

    # ── Full metrics table ──────────────────────────────────────────────────
    display_df = eval_df.drop(columns=["model"], errors="ignore")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.markdown("---")

    ranking_cols = [c for c in eval_df.columns if c.startswith(("precision", "recall", "ndcg"))]
    error_cols   = [c for c in eval_df.columns if c in ("rmse", "mae")]

    # ── Grouped ranking-metrics bar chart ───────────────────────────────────
    if ranking_cols:
        st.markdown("**Ranking quality — Precision, Recall, nDCG**")
        rank_long = eval_df[["Model"] + ranking_cols].melt(
            id_vars="Model", var_name="Metric", value_name="Score"
        )
        fig_rank = px.bar(
            rank_long, x="Model", y="Score", color="Metric",
            barmode="group",
            color_discrete_sequence=_PALETTE,
            template="plotly_white",
        )
        fig_rank.update_layout(
            font_family="Cormorant Garamond, serif",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
            yaxis_title="Score",
            xaxis_title="",
            margin=dict(t=10, b=10),
            height=340,
        )
        fig_rank.update_traces(marker_line_width=0)
        st.plotly_chart(fig_rank, use_container_width=True)

    # ── RMSE / MAE error bar chart ──────────────────────────────────────────
    if error_cols:
        st.markdown("**Prediction error — RMSE & MAE** *(lower is better)*")
        err_long = eval_df[["Model"] + error_cols].melt(
            id_vars="Model", var_name="Metric", value_name="Error"
        )
        fig_err = px.bar(
            err_long, x="Model", y="Error", color="Metric",
            barmode="group",
            color_discrete_sequence=[_ACCENT, "#6B7280"],
            template="plotly_white",
        )
        fig_err.update_layout(
            font_family="Cormorant Garamond, serif",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
            yaxis_title="Error",
            xaxis_title="",
            margin=dict(t=10, b=10),
            height=320,
        )
        fig_err.update_traces(marker_line_width=0)
        st.plotly_chart(fig_err, use_container_width=True)

    # ── Precision–Recall scatter ────────────────────────────────────────────
    prec_col = next((c for c in eval_df.columns if c.startswith("precision")), None)
    rec_col  = next((c for c in eval_df.columns if c.startswith("recall")), None)
    ndcg_col = next((c for c in eval_df.columns if c.startswith("ndcg")), None)
    if prec_col and rec_col:
        st.markdown("**Precision–Recall trade-off**")
        scatter_df = eval_df[["Model", prec_col, rec_col]].copy()
        if ndcg_col:
            scatter_df["nDCG"] = eval_df[ndcg_col]
        fig_pr = px.scatter(
            scatter_df, x=rec_col, y=prec_col,
            text="Model",
            size="nDCG" if ndcg_col else None,
            size_max=28,
            color="Model",
            color_discrete_sequence=_PALETTE,
            template="plotly_white",
            labels={rec_col: "Recall@10", prec_col: "Precision@10"},
        )
        fig_pr.update_traces(textposition="top center", marker_line_width=0)
        fig_pr.update_layout(
            font_family="Cormorant Garamond, serif",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(t=10, b=10),
            height=360,
        )
        st.plotly_chart(fig_pr, use_container_width=True)

    # ── Normalized performance heatmap ──────────────────────────────────────
    metric_cols = ranking_cols + error_cols
    if metric_cols:
        st.markdown("**Normalised performance heatmap** *(each metric scaled 0 → 1; for error metrics, lower raw value = higher normalised score)*")
        heat = eval_df[["Model"] + metric_cols].set_index("Model").copy()
        for col in heat.columns:
            rng = heat[col].max() - heat[col].min()
            if rng > 0:
                if col in error_cols:  # lower is better → invert
                    heat[col] = 1 - (heat[col] - heat[col].min()) / rng
                else:
                    heat[col] = (heat[col] - heat[col].min()) / rng
        fig_heat = go.Figure(data=go.Heatmap(
            z=heat.values,
            x=list(heat.columns),
            y=list(heat.index),
            colorscale=[[0, "#F5F0EB"], [0.5, "#E8B4A0"], [1, _ACCENT]],
            text=np.round(heat.values, 3),
            texttemplate="%{text}",
            showscale=True,
            zmin=0, zmax=1,
        ))
        fig_heat.update_layout(
            font_family="Cormorant Garamond, serif",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10),
            height=max(200, 60 * len(heat)),
            xaxis=dict(side="top"),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ── Metric rank leaderboard ─────────────────────────────────────────────
    if ranking_cols:
        st.markdown("**Model ranking per metric** *(1 = best)*")
        rank_tbl = eval_df[["Model"] + ranking_cols + error_cols].set_index("Model").copy()
        for col in ranking_cols:
            rank_tbl[col] = rank_tbl[col].rank(ascending=False).astype(int)
        for col in error_cols:
            rank_tbl[col] = rank_tbl[col].rank(ascending=True).astype(int)
        st.dataframe(rank_tbl, use_container_width=True)

else:
    status_banner(
        "warn",
        "Evaluation results not found. Run the evaluate stage on the Admin page.",
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Sentiment distribution
# ---------------------------------------------------------------------------
st.markdown("### Sentiment analysis")
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
            ).value_counts().sort_index().rename(index=str)
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
st.markdown("### Cuisine landscape")
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
st.markdown("### User activity")
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
st.markdown("### Geographic spread")
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

render_dock("analytics", user_id=st.session_state.get("selected_user_id"))
