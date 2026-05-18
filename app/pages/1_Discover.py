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
# Wizard card — identity + location in one unified flow
# ---------------------------------------------------------------------------
top_users = (
    interactions["user_id"].value_counts().head(50).index.tolist()
    if not interactions.empty else []
)

_wiz_phase = st.session_state.get("wizard_phase", "choose")
_wiz_mode  = st.session_state.get("wizard_mode", "returning")

_CARD_TITLES = {
    "choose":     "Who&#8217;s driving?",
    "onboarding": "Tell us your taste",
    "location":   "Where are you driving from?",
}
_STEP_LABELS = {
    "choose":     "Step 01 &middot; Identity",
    "onboarding": "Step 01 &middot; New User",
    "location":   "Step 02 &middot; Location",
}

# Unique keyframe name per phase forces browser to replay animation on every transition
_anim_id = f"wiz_{_wiz_phase}"
st.markdown(
    f"<style>"
    f"@keyframes {_anim_id}{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}"
    f"[data-testid='stVerticalBlockBorderWrapper']{{animation:{_anim_id} 0.28s cubic-bezier(0.22,0.61,0.36,1) both}}"
    f"</style>",
    unsafe_allow_html=True,
)

# Back button lives above the card for the onboarding phase (matches Cold Start design)
if _wiz_phase == "onboarding":
    _back_col, _ = st.columns([1, 5])
    with _back_col:
        if st.button("← Back", key="wiz_back_ob"):
            st.session_state["wizard_phase"] = "choose"
            st.session_state.pop("cold_start_profile", None)
            st.rerun()

with st.container(border=True):
    # Generic header for choose + location phases; onboarding supplies its own cs-head
    if _wiz_phase != "onboarding":
        st.markdown(
            f'<div class="wizard-card-header-inner">'
            f'<span class="wizard-card-title">{_CARD_TITLES[_wiz_phase]}</span>'
            f'<span class="wizard-card-step">{_STEP_LABELS[_wiz_phase]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if _wiz_phase == "choose":
        c_ret, c_new = st.columns(2)
        with c_ret:
            st.markdown(
                '<div class="wizard-choice-card">'
                '<span class="wizard-choice-icon">&#8617;</span>'
                '<span class="wizard-choice-label">Returning User</span>'
                '<span class="wizard-choice-desc">Personalised picks based on your rating history.</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("Select →", key="wiz_ret", use_container_width=True):
                st.session_state["wizard_phase"] = "location"
                st.session_state["wizard_mode"] = "returning"
                st.rerun()
        with c_new:
            st.markdown(
                '<div class="wizard-choice-card">'
                '<span class="wizard-choice-icon">&#10024;</span>'
                '<span class="wizard-choice-label">New User</span>'
                "<span class=\"wizard-choice-desc\">Tell us your taste and we'll find great nearby spots.</span>"
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("Select →", key="wiz_new", use_container_width=True):
                st.session_state["wizard_phase"] = "onboarding"
                st.session_state["wizard_mode"] = "new"
                st.rerun()

    elif _wiz_phase == "onboarding":
        _ob_profile = render_onboarding()
        if _ob_profile is not None:
            st.session_state["wizard_phase"] = "location"
            st.rerun()

    elif _wiz_phase == "location":
        _back_col, _ = st.columns([1, 5])
        with _back_col:
            if st.button("← Back", key="wiz_back_loc"):
                st.session_state["wizard_phase"] = "choose"
                st.session_state.pop("user_location", None)
                st.session_state.pop("selected_user_id", None)
                st.rerun()
        if _wiz_mode == "returning":
            if top_users:
                field_label("PICK A USER")
                st.selectbox(
                    "Pick a user",
                    options=top_users,
                    format_func=lambda u: f"{u[:8]}… ({int((interactions['user_id'] == u).sum())} ratings)",
                    label_visibility="collapsed",
                    key="selected_user_id",
                )
            else:
                st.info("No users in interactions yet.")
        render_location_picker(show_header=False)

# ── Must complete wizard before showing recommendations ──
if _wiz_phase != "location":
    st.stop()
if "user_location" not in st.session_state:
    empty_state_card(
        "Pick a location to see recommendations",
        "Once we know where you are, we'll surface your personalised Top-N restaurants nearby.",
        icon_src=_ICON_MAP,
    )
    st.stop()

lat, lon, src_label = st.session_state["user_location"]
mode = "New user (cold start)" if _wiz_mode == "new" else "Returning user"
selected_user_id: str | None = st.session_state.get("selected_user_id")
profile = st.session_state.get("cold_start_profile")

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
    'color:#b7b1c6;text-transform:uppercase;margin:1.2rem 0 0.3rem 0;">MODEL</p>',
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
