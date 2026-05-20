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
from src.config import MODEL_FILES, MODELS_DIR, PROCESSED_DIR, REVIEW_PARQUET  # noqa: E402
from src.preprocessing import load_processed  # noqa: E402


st.set_page_config(page_title="Analytics", page_icon="·", layout="wide", initial_sidebar_state="collapsed")
inject_css()
render_topnav("analytics")
page_header("Analytics", "How the data and models actually behave.")


def _processed_mtime() -> float:
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

businesses   = data.get("businesses")
reviews      = data.get("reviews")
interactions = data.get("interactions")

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_ACCENT  = "#ff7a1a"
_NAVY    = "#0f1f3d"
_GRAY    = "#8e8aa6"
_PALETTE = [_ACCENT, _NAVY, _GRAY, "#a8422a", "#b7b1c6", "#2a3856"]

_BASE_LAYOUT: dict = dict(
    font_family="DM Sans, sans-serif",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="#ffffff",
    margin=dict(t=4, b=4, l=4, r=4),
)

_XAXIS_CLEAN = dict(showgrid=False, zeroline=False,
                    tickfont=dict(size=10, color="#8e8aa6", family="DM Sans"))
_YAXIS_GRID  = dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", zeroline=False,
                    tickfont=dict(size=10, color="#8e8aa6", family="DM Sans"))


def _card_title(title: str, subtitle: str = "") -> None:
    sub = (
        f'<span style="font-style:italic;color:#8e8aa6;font-size:.8rem;'
        f'font-family:\'DM Sans\',sans-serif;font-weight:400;margin-left:6px;">'
        f'{subtitle}</span>'
    ) if subtitle else ""
    st.markdown(
        f'<div style="padding:.85rem 1.1rem .3rem 1.1rem;">'
        f'<span style="font-family:\'Instrument Serif\',\'Cormorant Garamond\',serif;'
        f'font-size:1.1rem;font-weight:400;color:#0d0d0d;">{title}</span>{sub}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Top metric strip
# ---------------------------------------------------------------------------
mc = st.columns(4)
mc[0].metric("Restaurants",  f"{len(businesses):,}"                          if businesses    is not None else "—")
mc[1].metric("Reviews",      f"{len(reviews):,}"                             if reviews       is not None else "—")
mc[2].metric("Users",        f"{interactions['user_id'].nunique():,}"         if interactions  is not None else "—")
mc[3].metric("Cities",
             businesses["city"].nunique()
             if businesses is not None and "city" in businesses else "—")

st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Row 1 — Area chart (2/3) + Rating distribution funnel (1/3)
# ---------------------------------------------------------------------------
r1c1, r1c2 = st.columns([2, 1])

with r1c1:
    with st.container(border=True):
        # Try to build a time-series chart from dates in reviews or interactions
        _ts_built = False

        if reviews is not None and "date" in reviews.columns:
            try:
                rv = reviews.copy()
                rv["date"] = pd.to_datetime(rv["date"], errors="coerce")
                rv = rv.dropna(subset=["date"])
                rv["month"] = rv["date"].dt.to_period("M").dt.to_timestamp()
                monthly = rv.groupby("month").size().rename("Reviews").reset_index()
                monthly.columns = ["Month", "Reviews"]
                monthly = monthly.sort_values("Month").tail(24)
                monthly["Trend"] = monthly["Reviews"].rolling(3, min_periods=1).mean().round(0)

                _card_title("Reviews over time", "monthly volume · trailing 24 months")
                fig_ts = go.Figure()
                fig_ts.add_trace(go.Scatter(
                    x=monthly["Month"], y=monthly["Reviews"],
                    fill="tozeroy", fillcolor="rgba(255,122,26,0.13)",
                    line=dict(color=_ACCENT, width=2), name="Reviews",
                    hovertemplate="%{y:,}<extra>Reviews</extra>",
                ))
                fig_ts.add_trace(go.Scatter(
                    x=monthly["Month"], y=monthly["Trend"],
                    line=dict(color=_GRAY, width=1.5, dash="dash"),
                    name="3-mo avg",
                    hovertemplate="%{y:,.0f}<extra>3-mo avg</extra>",
                ))
                fig_ts.update_layout(**_BASE_LAYOUT, height=230,
                    xaxis=_XAXIS_CLEAN, yaxis=_YAXIS_GRID,
                    showlegend=True,
                    legend=dict(x=1, y=1.05, xanchor="right", orientation="h",
                                font=dict(size=10, family="JetBrains Mono")),
                )
                st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar": False})
                _ts_built = True
            except Exception:
                pass

        if not _ts_built and interactions is not None and "date" in interactions.columns:
            try:
                ia = interactions.copy()
                ia["date"] = pd.to_datetime(ia["date"], errors="coerce")
                ia = ia.dropna(subset=["date"])
                ia["month"] = ia["date"].dt.to_period("M").dt.to_timestamp()
                monthly = ia.groupby("month").size().reset_index()
                monthly.columns = ["Month", "Count"]
                monthly = monthly.sort_values("Month").tail(24)
                monthly["Trend"] = monthly["Count"].rolling(3, min_periods=1).mean().round(0)

                _card_title("Interactions over time", "monthly volume · trailing 24 months")
                fig_ts = go.Figure()
                fig_ts.add_trace(go.Scatter(
                    x=monthly["Month"], y=monthly["Count"],
                    fill="tozeroy", fillcolor="rgba(255,122,26,0.13)",
                    line=dict(color=_ACCENT, width=2), name="Interactions",
                ))
                fig_ts.add_trace(go.Scatter(
                    x=monthly["Month"], y=monthly["Trend"],
                    line=dict(color=_GRAY, width=1.5, dash="dash"), name="3-mo avg",
                ))
                fig_ts.update_layout(**_BASE_LAYOUT, height=230,
                    xaxis=_XAXIS_CLEAN, yaxis=_YAXIS_GRID,
                    showlegend=True,
                    legend=dict(x=1, y=1.05, xanchor="right", orientation="h",
                                font=dict(size=10, family="JetBrains Mono")),
                )
                st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar": False})
                _ts_built = True
            except Exception:
                pass

        if not _ts_built:
            # Fall back: review count by star as area chart
            _card_title("Review volume by star rating", "distribution across all reviews")
            if reviews is not None and "stars" in reviews.columns:
                sc = reviews["stars"].value_counts().sort_index()
                fig_ts = go.Figure(go.Scatter(
                    x=sc.index.astype(str), y=sc.values,
                    fill="tozeroy", fillcolor="rgba(255,122,26,0.13)",
                    line=dict(color=_ACCENT, width=2),
                    hovertemplate="%{y:,}<extra></extra>",
                ))
                fig_ts.update_layout(**_BASE_LAYOUT, height=230,
                    showlegend=False,
                    xaxis={**_XAXIS_CLEAN, "title": "Stars"},
                    yaxis=_YAXIS_GRID,
                )
                st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown(
                    '<div style="height:220px;display:flex;align-items:center;'
                    'justify-content:center;color:#8e8aa6;font-size:.9rem;">'
                    'No date or star data available</div>',
                    unsafe_allow_html=True,
                )

with r1c2:
    with st.container(border=True):
        _card_title("Rating distribution", "share by star")

        if reviews is not None and "stars" in reviews.columns:
            sc = reviews["stars"].value_counts().sort_index()
            total = sc.sum()
            bar_colors = {1: "#c9402e", 2: "#c98c2a", 3: _GRAY, 4: "#1e8a55", 5: _ACCENT}

            rows = ""
            for star in sorted(sc.index, reverse=True):
                count = sc[star]
                pct   = count / total
                color = bar_colors.get(int(star), _GRAY)
                rows += (
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
                    f'  <span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                    f'color:#8e8aa6;min-width:20px;">{int(star)}★</span>'
                    f'  <div style="flex:1;background:rgba(0,0,0,0.06);border-radius:4px;'
                    f'height:7px;overflow:hidden;">'
                    f'    <div style="width:{pct*100:.1f}%;height:100%;background:{color};'
                    f'border-radius:4px;"></div></div>'
                    f'  <span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                    f'color:#3a3a37;min-width:44px;text-align:right;">{count:,}</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="padding:.4rem 1.1rem 1rem 1.1rem;">{rows}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="height:180px;display:flex;align-items:center;'
                'justify-content:center;color:#8e8aa6;font-size:.9rem;">No review data</div>',
                unsafe_allow_html=True,
            )

st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Row 2 — Top cuisines | Sentiment vs stars | Top cities
# ---------------------------------------------------------------------------
r2c1, r2c2, r2c3 = st.columns(3)

with r2c1:
    with st.container(border=True):
        _card_title("Top cuisines", "by restaurant count")

        if businesses is not None and "categories" in businesses.columns:
            cat_counts: dict[str, int] = {}
            for cats in businesses["categories"].dropna():
                for c in str(cats).split(","):
                    c = c.strip()
                    if c and c.lower() not in ("restaurants", "food"):
                        cat_counts[c] = cat_counts.get(c, 0) + 1
            top = pd.Series(cat_counts).sort_values(ascending=False).head(8)

            bar_colors = [_ACCENT] + [_GRAY] * (len(top) - 1)
            fig_cuis = go.Figure(go.Bar(
                y=top.index.tolist(),
                x=top.values,
                orientation="h",
                marker_color=bar_colors,
                marker_line_width=0,
                text=[f"{v:,}" for v in top.values],
                textposition="outside",
                textfont=dict(size=10, color="#8e8aa6", family="JetBrains Mono"),
                hovertemplate="%{y}: %{x:,}<extra></extra>",
            ))
            fig_cuis.update_layout(
                **_BASE_LAYOUT, height=270,
                showlegend=False,
                xaxis=dict(showgrid=False, zeroline=False, visible=False),
                yaxis=dict(showgrid=False, zeroline=False,
                           tickfont=dict(size=11, color="#3a3a37", family="DM Sans"),
                           autorange="reversed"),
                bargap=0.28,
            )
            st.plotly_chart(fig_cuis, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown("No category data.")

with r2c2:
    with st.container(border=True):
        if (reviews is not None
                and "stars" in reviews.columns
                and "sentiment_compound" in reviews.columns):
            _card_title("Sentiment by star", "mean VADER score per rating")
            agg = (reviews.groupby("stars")["sentiment_compound"]
                   .mean().round(3).reset_index())
            agg.columns = ["Stars", "Sentiment"]
            peak_idx = int(agg["Sentiment"].idxmax())

            fig_sent = go.Figure(go.Bar(
                x=agg["Stars"].astype(str),
                y=agg["Sentiment"],
                marker_color=[_ACCENT if i == peak_idx else _GRAY
                              for i in range(len(agg))],
                marker_line_width=0,
                text=agg["Sentiment"].round(2),
                textposition="outside",
                textfont=dict(size=10, color="#8e8aa6", family="JetBrains Mono"),
                hovertemplate="★%{x}: %{y:.3f}<extra></extra>",
            ))
            fig_sent.update_layout(
                **_BASE_LAYOUT, height=270,
                showlegend=False,
                xaxis={**_XAXIS_CLEAN, "title": "Stars"},
                yaxis={**_YAXIS_GRID,
                       "zeroline": True, "zerolinecolor": "rgba(0,0,0,0.10)"},
                bargap=0.28,
            )
            st.plotly_chart(fig_sent, use_container_width=True, config={"displayModeBar": False})

        elif reviews is not None and "stars" in reviews.columns:
            _card_title("Star rating breakdown", "count per rating value")
            sc = reviews["stars"].value_counts().sort_index()
            peak_idx = int(sc.values.argmax())
            fig_stars = go.Figure(go.Bar(
                x=sc.index.astype(str),
                y=sc.values,
                marker_color=[_ACCENT if i == peak_idx else _GRAY
                              for i in range(len(sc))],
                marker_line_width=0,
                hovertemplate="★%{x}: %{y:,}<extra></extra>",
            ))
            fig_stars.update_layout(
                **_BASE_LAYOUT, height=270,
                showlegend=False,
                xaxis={**_XAXIS_CLEAN, "title": "Stars"},
                yaxis=_YAXIS_GRID,
                bargap=0.28,
            )
            st.plotly_chart(fig_stars, use_container_width=True, config={"displayModeBar": False})
        else:
            _card_title("Sentiment", "no data")
            st.markdown("Run the sentiment pipeline first.")

with r2c3:
    with st.container(border=True):
        _card_title("Top cities", "by restaurant count")

        if businesses is not None and "city" in businesses.columns:
            city_counts = businesses["city"].value_counts().head(8)
            rows = ""
            for i, (city, count) in enumerate(city_counts.items(), 1):
                num_color = _ACCENT if i == 1 else "#8e8aa6"
                border = "border-bottom:1px solid rgba(0,0,0,0.05);" if i < len(city_counts) else ""
                rows += (
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:7px 0;{border}">'
                    f'  <span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                    f'color:{num_color};min-width:18px;font-weight:500;">#{i}</span>'
                    f'  <span style="flex:1;font-family:\'DM Sans\',sans-serif;'
                    f'font-size:13px;color:#0d0d0d;">{city}</span>'
                    f'  <span style="font-family:\'JetBrains Mono\',monospace;'
                    f'font-size:11px;color:#8e8aa6;">{count:,}</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="padding:.4rem 1.1rem 1rem 1.1rem;">{rows}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("No city data.")

st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
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

eval_path = MODELS_DIR / "evaluation_results.csv"
st.markdown("### Model comparison")

if not eval_path.exists():
    status_banner("warn", "Evaluation results not found. Run the evaluate stage on the Admin page.")
    _ec1, _ec2 = st.columns([1, 5])
    with _ec1:
        if st.button("▶ Run Evaluation Now", type="primary"):
            from src.config import DEFAULT_CONFIG
            from src.pipeline import evaluate_models, has_trained_models, train_test_split_interactions
            from src.utils import load_pickle
            if not has_trained_models():
                st.error("No trained models found. Run the Train stage from Admin first.")
            else:
                try:
                    with st.spinner("Evaluating models — this may take a minute …"):
                        _cfg = DEFAULT_CONFIG
                        _d = load_processed()
                        if "interactions" not in _d or "businesses" not in _d:
                            st.error("Processed data missing. Run the preprocessing stage first.")
                            st.stop()
                        _models = {k: load_pickle(MODELS_DIR / MODEL_FILES[k])
                                   for k in ("popularity", "content_based", "item_cf", "user_cf", "matrix_fact")}
                        _train, _test = train_test_split_interactions(
                            _d["interactions"], test_size=_cfg.test_size, random_state=_cfg.random_state
                        )
                        evaluate_models(_models, _train, _test, _d["businesses"])
                    st.rerun()
                except Exception as _e:
                    st.exception(_e)

if eval_path.exists():
    eval_df = pd.read_csv(eval_path).round(4)
    eval_df["Model"] = eval_df["model"].map(_MODEL_LABELS).fillna(eval_df["model"])

    display_df = eval_df.drop(columns=["model"], errors="ignore")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    ranking_cols = [c for c in eval_df.columns if c.startswith(("precision", "recall", "ndcg"))]
    error_cols   = [c for c in eval_df.columns if c in ("rmse", "mae")]

    # ── Ranking + error charts side by side ─────────────────────────────────
    if ranking_cols or error_cols:
        mc1, mc2 = st.columns(2)

        with mc1:
            with st.container(border=True):
                _card_title("Ranking quality", "precision · recall · nDCG")
                if ranking_cols:
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
                        **_BASE_LAYOUT, height=290,
                        showlegend=True,
                        legend=dict(x=1, y=1.08, xanchor="right", orientation="h",
                                    font=dict(size=10, family="JetBrains Mono")),
                        xaxis=_XAXIS_CLEAN, yaxis=_YAXIS_GRID,
                    )
                    fig_rank.update_traces(marker_line_width=0)
                    st.plotly_chart(fig_rank, use_container_width=True, config={"displayModeBar": False})

        with mc2:
            with st.container(border=True):
                if error_cols:
                    _card_title("Prediction error", "RMSE & MAE · lower is better")
                    err_long = eval_df[["Model"] + error_cols].melt(
                        id_vars="Model", var_name="Metric", value_name="Error"
                    )
                    fig_err = px.bar(
                        err_long, x="Model", y="Error", color="Metric",
                        barmode="group",
                        color_discrete_sequence=[_ACCENT, _GRAY],
                        template="plotly_white",
                    )
                    fig_err.update_layout(
                        **_BASE_LAYOUT, height=290,
                        showlegend=True,
                        legend=dict(x=1, y=1.08, xanchor="right", orientation="h",
                                    font=dict(size=10, family="JetBrains Mono")),
                        xaxis=_XAXIS_CLEAN, yaxis=_YAXIS_GRID,
                    )
                    fig_err.update_traces(marker_line_width=0)
                    st.plotly_chart(fig_err, use_container_width=True, config={"displayModeBar": False})
                else:
                    prec_col = next((c for c in eval_df.columns if c.startswith("precision")), None)
                    rec_col  = next((c for c in eval_df.columns if c.startswith("recall")), None)
                    ndcg_col = next((c for c in eval_df.columns if c.startswith("ndcg")), None)
                    if prec_col and rec_col:
                        _card_title("Precision–Recall", "trade-off · bubble size = nDCG")
                        sdf = eval_df[["Model", prec_col, rec_col]].copy()
                        if ndcg_col:
                            sdf["nDCG"] = eval_df[ndcg_col]
                        fig_pr = px.scatter(
                            sdf, x=rec_col, y=prec_col,
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
                            **_BASE_LAYOUT, height=290,
                            showlegend=False,
                            xaxis=_XAXIS_CLEAN, yaxis=_YAXIS_GRID,
                        )
                        st.plotly_chart(fig_pr, use_container_width=True, config={"displayModeBar": False})

    # ── Performance heatmap ──────────────────────────────────────────────────
    metric_cols = ranking_cols + error_cols
    if metric_cols:
        with st.container(border=True):
            _card_title("Performance heatmap",
                        "normalised 0 → 1 · for error metrics lower raw = higher score")
            heat = eval_df[["Model"] + metric_cols].set_index("Model").copy()
            for col in heat.columns:
                rng = heat[col].max() - heat[col].min()
                if rng > 0:
                    if col in error_cols:
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
                **_BASE_LAYOUT,
                showlegend=False,
                height=max(200, 60 * len(heat)),
                xaxis=dict(side="top",
                           tickfont=dict(size=10, color="#3a3a37", family="JetBrains Mono")),
                yaxis=dict(tickfont=dict(size=10, color="#3a3a37", family="DM Sans")),
            )
            st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

    # ── Metric rank leaderboard ──────────────────────────────────────────────
    if ranking_cols:
        with st.container(border=True):
            _card_title("Model leaderboard", "rank per metric · 1 = best")
            rank_tbl = eval_df[["Model"] + ranking_cols + error_cols].set_index("Model").copy()
            for col in ranking_cols:
                rank_tbl[col] = rank_tbl[col].rank(ascending=False).astype(int)
            for col in error_cols:
                rank_tbl[col] = rank_tbl[col].rank(ascending=True).astype(int)
            st.dataframe(rank_tbl, use_container_width=True)

else:
    status_banner("warn", "Evaluation results not found. Run the evaluate stage on the Admin page.")

st.markdown("---")

# ---------------------------------------------------------------------------
# User activity
# ---------------------------------------------------------------------------
st.markdown("### User activity")
if interactions is not None and not interactions.empty:
    per_user = interactions.groupby("user_id").size()
    ac1, ac2 = st.columns(2)

    with ac1:
        with st.container(border=True):
            _card_title("Ratings per user", "bucket distribution")
            bucket = pd.cut(
                per_user,
                bins=[0, 2, 5, 10, 25, 100, 100_000],
                labels=["1–2", "3–5", "6–10", "11–25", "26–100", "100+"],
            ).value_counts().sort_index()
            fig_act = go.Figure(go.Bar(
                x=bucket.index.astype(str),
                y=bucket.values,
                marker_color=[_ACCENT if i == 0 else _GRAY for i in range(len(bucket))],
                marker_line_width=0,
                text=bucket.values,
                textposition="outside",
                textfont=dict(size=10, color="#8e8aa6", family="JetBrains Mono"),
                hovertemplate="%{x}: %{y:,} users<extra></extra>",
            ))
            fig_act.update_layout(
                **_BASE_LAYOUT, height=240,
                showlegend=False,
                xaxis={**_XAXIS_CLEAN, "title": "Ratings"},
                yaxis=_YAXIS_GRID,
                bargap=0.25,
            )
            st.plotly_chart(fig_act, use_container_width=True, config={"displayModeBar": False})

    with ac2:
        with st.container(border=True):
            _card_title("Activity stats", "engagement summary")
            sparsity = 1 - (
                len(interactions) / (per_user.size * interactions["business_id"].nunique())
            )
            stats_html = ""
            items = [
                ("Mean ratings / user",    f"{float(per_user.mean()):.2f}"),
                ("Median ratings / user",  str(int(per_user.median()))),
                ("Max ratings / user",     f"{int(per_user.max()):,}"),
                ("Users with ≥ 5 ratings", f"{int((per_user >= 5).sum()):,}"),
                ("Matrix sparsity",        f"{sparsity:.4%}"),
            ]
            for label, value in items:
                stats_html += (
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:baseline;padding:7px 0;'
                    f'border-bottom:1px solid rgba(0,0,0,0.05);">'
                    f'  <span style="font-size:.88rem;color:#3a3a37;">{label}</span>'
                    f'  <span style="font-family:\'JetBrains Mono\',monospace;'
                    f'font-size:13px;color:{_ACCENT};font-weight:500;">{value}</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="padding:.4rem 1.1rem 1rem 1.1rem;">{stats_html}</div>',
                unsafe_allow_html=True,
            )

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
