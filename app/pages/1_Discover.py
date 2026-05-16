"""Discover page: pick user, set GPS, get hybrid recommendations."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _svg_b64(name: str) -> str:
    p = ROOT / "app" / "static" / name
    try:
        return f"data:image/svg+xml;base64,{base64.b64encode(p.read_text(encoding='utf-8').encode()).decode()}"
    except Exception:
        return ""


_ICON_DISCOVER = _svg_b64("icon-discover.svg")
_ICON_MAP      = _svg_b64("icon-mapview.svg")

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.components.cards import render_recommendations  # noqa: E402
from app.components.cold_start import render_onboarding  # noqa: E402
from app.components.filters import apply_hard_filters, render_filter_sidebar  # noqa: E402
from app.components.location import render_location_picker  # noqa: E402
from app.components.styles import (  # noqa: E402
    empty_state_card,
    field_label,
    inject_css,
    sidebar_extras,
    sidebar_logo,
    status_banner,
)
from src.cold_start import (  # noqa: E402
    adjust_weights,
    classify_user,
    filter_by_profile,
    get_cold_start_explanation,
)
from src.config import MODEL_FILES, MODELS_DIR, PROCESSED_DIR, RAW_DIR  # noqa: E402
from src.geo import add_distance_column  # noqa: E402
from src.llm_explain import annotate_recommendations  # noqa: E402
from src.preprocessing import load_processed  # noqa: E402
from src.recommenders.hybrid import HybridRecommender, HybridWeights  # noqa: E402
from src.utils import load_business_photos, load_pickle  # noqa: E402


st.set_page_config(page_title="Discover", page_icon="·", layout="wide")
inject_css()
sidebar_logo(ROOT / "app" / "static" / "mcgill_logo.png")
sidebar_extras(user_id=st.session_state.get("selected_user_id"))


# ---------------------------------------------------------------------------
# Inline helpers
# ---------------------------------------------------------------------------
_PERSON_ICON = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
    'style="color:var(--text-primary);flex-shrink:0">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)
_PIN_ICON = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
    'style="color:var(--text-primary);flex-shrink:0">'
    '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
    '<circle cx="12" cy="10" r="3"/></svg>'
)


def _disc_step(num: str, icon: str, heading: str, subtitle: str = "") -> None:
    sub = f'<p class="disc-step-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="disc-step">'
        f'<span class="disc-step-num">{num}</span>'
        f'<div>'
        f'<div class="disc-step-head">{icon}'
        f'<span class="disc-step-title">{heading}</span></div>'
        f'{sub}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data + model loading (cached)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_models() -> dict:
    models: dict = {}
    for key in ("popularity", "content_based", "item_cf", "user_cf", "matrix_fact"):
        path = MODELS_DIR / MODEL_FILES[key]
        if not path.exists():
            return {}
        models[key] = load_pickle(path)
    hybrid = HybridRecommender(
        personalised=models["matrix_fact"],
        content=models["content_based"],
        popularity=models["popularity"],
    )
    models["hybrid"] = hybrid
    return models


@st.cache_data(show_spinner=False)
def _load_data() -> dict[str, pd.DataFrame]:
    return load_processed()


@st.cache_data(show_spinner=False)
def _load_photo_map() -> dict:
    return load_business_photos(RAW_DIR)


data    = _load_data()
models  = _load_models()
photo_map  = _load_photo_map()
photos_dir = RAW_DIR / "photos"

if not data or "businesses" not in data:
    status_banner("err", "No processed data found. Run the pipeline from the Admin page first.")
    st.stop()

if not models:
    status_banner("err", "Trained models missing. Train them from the Admin page first.")
    st.stop()

businesses   = data["businesses"]
interactions = data.get("interactions", pd.DataFrame(columns=["user_id", "business_id"]))
reviews      = data.get("reviews")

# ---------------------------------------------------------------------------
# Hero card
# ---------------------------------------------------------------------------
n_biz_fmt = f"{len(businesses):,}"
hero_b64  = _svg_b64("hero.svg")

st.markdown(
    f"""
    <div class="hero-card">
      <div class="hero-left">
        <div class="page-header-wrap" style="margin-bottom:1rem;">
          <div class="page-header-badge">
            <img src="{_ICON_DISCOVER}" alt="Discover"/>
          </div>
          <div>
            <h1 class="page-header-title">Discover</h1>
            <p class="page-header-subtitle">Find a great place to eat — wherever you are right now.</p>
          </div>
        </div>
        <div class="disc-metrics">
          <div>
            <div class="disc-metric-val">{n_biz_fmt}</div>
            <div class="disc-metric-label">PLACES INDEXED</div>
          </div>
          <div>
            <div class="disc-metric-val">36 <span class="disc-metric-unit">mi</span></div>
            <div class="disc-metric-label">DEFAULT RADIUS</div>
          </div>
          <div>
            <div class="disc-metric-val">4.6<span class="disc-metric-unit">s</span></div>
            <div class="disc-metric-label">MEDIAN LATENCY</div>
          </div>
        </div>
      </div>
      <div class="hero-right">
        <img src="{hero_b64}" class="hero-img" alt="Discover illustration"/>
        <span class="disc-pick-badge">#1 pick</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Step 01 — Identity selector
# ---------------------------------------------------------------------------
_disc_step(
    "01",
    _PERSON_ICON,
    "Who&#8217;s driving?",
    "Choose a returning user to get personalised picks, or start fresh.",
)

top_users = (
    interactions["user_id"]
    .value_counts()
    .head(50)
    .index.tolist()
    if not interactions.empty
    else []
)

id_col1, id_col2 = st.columns([2, 1])
with id_col1:
    field_label("MODE")
    mode = st.radio(
        "Mode",
        options=["Returning user", "New user (cold start)"],
        horizontal=True,
        label_visibility="collapsed",
    )
with id_col2:
    selected_user_id: str | None = None
    if mode == "Returning user":
        if top_users:
            field_label("PICK A USER")
            selected_user_id = st.selectbox(
                "Pick a user",
                options=top_users,
                format_func=lambda u: f"{u[:8]}… ({int((interactions['user_id'] == u).sum())} ratings)",
                label_visibility="collapsed",
                key="selected_user_id",
            )
        else:
            st.info("No users in interactions yet.")
    else:
        st.session_state["selected_user_id"] = None

if mode == "Returning user":
    selected_user_id = st.session_state.get("selected_user_id")

if mode == "Returning user":
    st.session_state.pop("cold_start_profile", None)

threshold = 3
regime    = classify_user(selected_user_id, interactions, threshold=threshold)
n_history = int((interactions["user_id"] == selected_user_id).sum()) if selected_user_id else 0

if regime == "established":
    banner_msg = (
        f"{n_history} ratings on record — "
        f'<em style="color:var(--accent)">full hybrid model</em>'
        f" with collaborative filtering at the centre."
    )
    banner_kind = "ok"
elif regime == "light":
    banner_msg = (
        f"Only {n_history} ratings in history — blending your stated "
        "preferences with collaborative filtering."
    )
    banner_kind = "warn"
else:
    banner_msg = (
        "No rating history found — using your stated cuisine preferences "
        "plus the most popular nearby restaurants."
    )
    banner_kind = "warn"

status_banner(banner_kind, banner_msg)

# ---------------------------------------------------------------------------
# Onboarding (only when cold)
# ---------------------------------------------------------------------------
profile = None
if mode == "New user (cold start)" or regime == "new":
    with st.expander("🎯 Tell us your taste (cold-start onboarding)", expanded=True):
        profile = render_onboarding()
        if profile is None:
            st.info("Submit the form above to continue.")
            st.stop()

# ---------------------------------------------------------------------------
# Step 02 — Location
# ---------------------------------------------------------------------------
_disc_step(
    "02",
    _PIN_ICON,
    "Where are you driving from?",
    "Three ways to set a starting point. We never store it.",
)
loc = render_location_picker(show_header=False)
if loc is None:
    empty_state_card(
        "Pick a location to see recommendations",
        "Once we know where you are, we'll surface your personalised Top-N restaurants nearby.",
        icon_src=_ICON_MAP,
    )
    st.stop()
lat, lon, src_label = loc

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
filters = render_filter_sidebar(
    businesses,
    default_radius=profile.radius_km if profile else 5.0,
)
use_llm = st.sidebar.checkbox(
    "Use Claude for the 'why' text",
    value=False,
    help="If GROQ_API_KEY is set, asks the LLM for a one-line rationale "
    "per recommendation. Falls back to a template otherwise.",
)

_MODEL_LABELS: dict[str, str] = {
    "hybrid":        "🔀 Hybrid (recommended)",
    "popularity":    "🏆 Popularity",
    "content_based": "🎯 Content-based",
    "item_cf":       "👥 Item-CF",
    "user_cf":       "🤝 User-CF",
    "matrix_fact":   "🧮 Matrix Factorization",
}
st.sidebar.markdown(
    '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;'
    'color:#9CA3AF;text-transform:uppercase;margin:1.2rem 0 0.3rem 0;">MODEL</p>',
    unsafe_allow_html=True,
)
selected_model_key: str = st.sidebar.selectbox(  # type: ignore[assignment]
    "Recommender model",
    options=list(_MODEL_LABELS.keys()),
    format_func=lambda k: _MODEL_LABELS[k],
    index=0,
    key="selected_model_key",
    label_visibility="collapsed",
    help="Swap the active scoring engine. Models that need user history fall back to Popularity for cold-start users.",
)

# ---------------------------------------------------------------------------
# Build candidate set
# ---------------------------------------------------------------------------
cand = add_distance_column(businesses, lat, lon)
if profile is not None:
    cand = filter_by_profile(cand, profile)
cand = apply_hard_filters(cand, filters)

if cand.empty:
    st.warning(
        "No restaurants matched the filters. Try widening the radius or "
        "relaxing star / price filters."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------
hybrid: HybridRecommender = models["hybrid"]
base_weights = HybridWeights(
    personalized=hybrid.weights.personalized,
    content=hybrid.weights.content,
    popularity=hybrid.weights.popularity,
    distance=hybrid.weights.distance,
)
weights = adjust_weights(base_weights, regime)

pref_profile = None
if profile is not None and profile.cuisines:
    pref_profile = models["content_based"].build_preference_profile(profile.cuisines)

active_model = models[selected_model_key]
_model_needs_history = getattr(active_model, "needs_user_history", True)
if _model_needs_history and not selected_user_id:
    st.warning(
        f"**{_MODEL_LABELS[selected_model_key]}** requires a returning user's rating "
        "history and cannot score a cold-start user. Falling back to Popularity."
    )
    active_model = models["popularity"]
    selected_model_key = "popularity"

with st.spinner("Scoring restaurants ..."):
    if selected_model_key == "hybrid":
        recs = hybrid.recommend(
            user_id=selected_user_id,
            candidates=cand,
            top_n=filters.top_n,
            weights=weights,
            preference_profile=pref_profile,
        )
    elif selected_model_key == "content_based":
        recs = active_model.recommend(
            user_id=selected_user_id,
            candidates=cand,
            top_n=filters.top_n,
            preference_profile=pref_profile,
        )
    else:
        recs = active_model.recommend(
            user_id=selected_user_id,
            candidates=cand,
            top_n=filters.top_n,
        )

user_cuisines = (profile.cuisines if profile else filters.cuisines) or None
if use_llm or filters.show_components:
    with st.spinner("Generating explanations ..."):
        recs = annotate_recommendations(
            recs,
            user_cuisines=user_cuisines,
            reviews_df=reviews,
            use_llm=use_llm,
            max_llm_calls=5,
        )
else:
    recs = annotate_recommendations(
        recs,
        user_cuisines=user_cuisines,
        reviews_df=None,
        use_llm=False,
    )

# ---------------------------------------------------------------------------
# Step 03 — Results strip
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="disc-step" style="margin-top:3rem;margin-bottom:0.5rem;">'
    '<span class="disc-step-num">03</span>'
    '<div><div class="disc-step-head">'
    '<span class="disc-step-title">Recommendations</span>'
    '</div></div></div>',
    unsafe_allow_html=True,
)

mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("Candidates", len(cand))
mc2.metric("Returned", len(recs))
if selected_model_key == "hybrid":
    mc3.metric(
        "Personalised w.", f"{weights.personalized:.2f}",
        delta=f"{weights.personalized - base_weights.personalized:+.2f}",
    )
    mc4.metric("Content w.", f"{weights.content:.2f}")
else:
    mc3.metric("Model", _MODEL_LABELS[selected_model_key])
    mc4.metric(
        "Personalised",
        "Yes" if not getattr(active_model, "needs_user_history", True) is False
        else str(bool(selected_user_id)),
    )
mc5.metric("From", src_label, help=f"Lat {lat:.4f}, Lon {lon:.4f}")

st.session_state["last_recs"]      = recs
st.session_state["last_center"]    = (lat, lon)
st.session_state["last_radius_km"] = filters.radius_km

render_recommendations(
    recs,
    show_components=filters.show_components,
    photo_map=photo_map,
    photos_dir=photos_dir,
)

# ---------------------------------------------------------------------------
# Diagnostic expander
# ---------------------------------------------------------------------------
with st.expander("🔬 Under the hood"):
    if selected_model_key == "hybrid":
        st.write("**Active hybrid weights** (after cold-start adjustment):")
        st.json(
            {
                "personalised": round(weights.personalized, 3),
                "content":      round(weights.content, 3),
                "popularity":   round(weights.popularity, 3),
                "distance":     round(weights.distance, 3),
            }
        )
    else:
        st.write(f"**Active model:** {_MODEL_LABELS[selected_model_key]}")
        st.write(f"Needs user history: `{getattr(active_model, 'needs_user_history', True)}`")
    st.write(
        f"User regime: `{regime}` · history ratings: `{n_history}` · "
        f"candidate set: `{len(cand)}` restaurants within {filters.radius_km} km"
    )
    if not recs.empty and {"personalised_score", "content_score", "popularity_score", "distance_score"}.issubset(
        recs.columns
    ):
        st.write("**Component scores** for the Top-N:")
        st.dataframe(
            recs[
                ["name", "personalised_score", "content_score",
                 "popularity_score", "distance_score", "score"]
            ].round(3),
            use_container_width=True,
        )
