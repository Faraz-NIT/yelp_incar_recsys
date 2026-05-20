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


def _img_b64(name: str) -> str:
    p = ROOT / "app" / "static" / name
    if not p.exists():
        return ""
    ext = p.suffix.lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.components.cards import render_recommendations  # noqa: E402
from app.components.cold_start import render_onboarding  # noqa: E402
from app.components.filters import apply_hard_filters, render_filter_rail  # noqa: E402
from app.components.location import render_location_picker  # noqa: E402
from app.components.styles import (
    empty_state_card,
    field_label,  # noqa: E402
    inject_css,
    render_dock,
    render_topnav,
    status_banner,
)
from src.cold_start import (
    adjust_weights,
    classify_user,  # noqa: E402
    filter_by_profile,
)
from src.config import MODEL_FILES, MODELS_DIR, RAW_DIR  # noqa: E402
from src.geo import add_distance_column  # noqa: E402
from src.llm_explain import annotate_recommendations  # noqa: E402
from src.preprocessing import load_processed  # noqa: E402
from src.recommenders.hybrid import HybridRecommender, HybridWeights  # noqa: E402
from src.utils import load_business_photos, load_pickle  # noqa: E402

st.set_page_config(
    page_title="Discover",
    page_icon="·",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
render_topnav("discover")


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


def _processed_mtime() -> float:
    from src.config import (
        BUSINESS_PARQUET,
        INTERACTION_PARQUET,
        PROCESSED_DIR,
        REVIEW_PARQUET,
    )

    files = [
        PROCESSED_DIR / f
        for f in (REVIEW_PARQUET, BUSINESS_PARQUET, INTERACTION_PARQUET)
    ]
    mtimes = [f.stat().st_mtime for f in files if f.exists()]
    return max(mtimes) if mtimes else 0.0


@st.cache_data(show_spinner=False)
def _load_data(mtime: float) -> dict[str, pd.DataFrame]:  # noqa: ARG001
    return load_processed()


@st.cache_data(show_spinner=False)
def _load_photo_map() -> dict:
    return load_business_photos(RAW_DIR)


data = _load_data(_processed_mtime())
models = _load_models()
photo_map = _load_photo_map()
photos_dir = RAW_DIR / "photos"

if not data or "businesses" not in data:
    status_banner(
        "err", "No processed data found. Run the pipeline from the Admin page first."
    )
    st.stop()

if not models:
    status_banner(
        "err", "Trained models missing. Train them from the Admin page first."
    )
    st.stop()

businesses = data["businesses"]
interactions = data.get(
    "interactions", pd.DataFrame(columns=["user_id", "business_id"])
)
reviews = data.get("reviews")

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
n_biz_fmt = f"{len(businesses):,}"
_food_src = _img_b64("food-hero.png")
_food_img = (
    f'<img src="{_food_src}" alt="" class="disc-ph-food" />' if _food_src else ""
)
st.markdown(
    f"""
    <div class="disc-ph">
      <div>
        <h1 class="disc-ph-title">Discover <i>along the way.</i></h1>
        <p class="disc-ph-sub">
          {n_biz_fmt} restaurants indexed &middot;
          personalised, distance-aware, hybrid scoring.
        </p>
      </div>
      {_food_img}
      <div class="disc-ph-actions">
        <a class="disc-btn-ghost" href="./Map_View" target="_self">&#128506; Map View</a>
        <a class="disc-btn-accent" href="./Analytics" target="_self">Analytics &#8594;</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Wizard — identity + location
# ---------------------------------------------------------------------------
top_users = (
    interactions["user_id"].value_counts().head(50).index.tolist()
    if not interactions.empty
    else []
)

_wiz_phase = st.session_state.get("wizard_phase", "choose")
_wiz_mode = st.session_state.get("wizard_mode", "returning")

_CARD_TITLES = {
    "choose": "Who&#8217;s driving?",
    "onboarding": "Tell us your taste",
    "location": "Where are you driving from?",
}
_STEP_LABELS = {
    "choose": "Step 01 &middot; Identity",
    "onboarding": "Step 01 &middot; New User",
    "location": "Step 02 &middot; Location",
}

_anim_id = f"wiz_{_wiz_phase}"
st.markdown(
    f"<style>"
    f"@keyframes {_anim_id}{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}"
    f"[data-testid='stVerticalBlockBorderWrapper']{{animation:{_anim_id} 0.28s cubic-bezier(0.22,0.61,0.36,1) both}}"
    f"</style>",
    unsafe_allow_html=True,
)

with st.container(border=True):

    if _wiz_phase == "choose":
        # ── Header ──────────────────────────────────────────────────────────
        st.markdown(
            '<div class="wiz-title-bar">'
            '<h2 class="wiz-hdr-title">Who&rsquo;s driving?</h2>'
            "</div>",
            unsafe_allow_html=True,
        )
        # ── Two choice columns ───────────────────────────────────────────────
        c_ret, c_new = st.columns(2)
        with c_ret:
            st.markdown(
                '<div class="wiz-card">'
                '<span class="wiz-card-icon">&#8617;</span>'
                '<div class="wiz-card-title">Returning user</div>'
                '<div class="wiz-card-desc">Personalised picks based on your rating history.</div>'
                '<div class="wiz-tags">'
                '<span class="wiz-tag wiz-tag-hot">Hybrid Model</span>'
                '<span class="wiz-tag">Collaborative Filtering</span>'
                '<span class="wiz-tag">~120ms</span>'
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("Select →", key="wiz_ret", use_container_width=True):
                st.session_state["wizard_phase"] = "location"
                st.session_state["wizard_mode"] = "returning"
                st.rerun()
        with c_new:
            st.markdown(
                '<div class="wiz-card">'
                '<span class="wiz-card-icon">&#10022;</span>'
                '<div class="wiz-card-title">New user</div>'
                '<div class="wiz-card-desc">Tell us your taste and we\'ll find great nearby spots.</div>'
                '<div class="wiz-tags">'
                '<span class="wiz-tag">Cold Start</span>'
                '<span class="wiz-tag">Content + Popularity</span>'
                '<span class="wiz-tag">3 Quick Questions</span>'
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button("Select →", key="wiz_new", use_container_width=True):
                st.session_state["wizard_phase"] = "onboarding"
                st.session_state["wizard_mode"] = "new"
                st.rerun()
        # ── Progress footer ──────────────────────────────────────────────────
        st.markdown(
            '<div class="wiz-footer">'
            '<span class="wiz-prog-label">Progress</span>'
            '<div class="wiz-prog-track"><div class="wiz-prog-fill"></div></div>'
            '<div class="wiz-steps">'
            '<span class="wiz-step on">01 Identity</span>'
            '<span class="wiz-step">02 Location</span>'
            '<span class="wiz-step">03 Taste</span>'
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    elif _wiz_phase == "onboarding":
        _back_col, _ = st.columns([1, 5])
        with _back_col:
            if st.button("← Back", key="wiz_back_ob"):
                st.session_state["wizard_phase"] = "choose"
                st.session_state.pop("cold_start_profile", None)
                st.rerun()
        _ob_profile = render_onboarding()
        if _ob_profile is not None:
            st.session_state["wizard_phase"] = "location"
            st.rerun()

    elif _wiz_phase == "location":
        st.markdown(
            f'<div class="wizard-card-header-inner">'
            f'<span class="wizard-card-title">{_CARD_TITLES["location"]}</span>'
            f'<span class="wizard-card-step">{_STEP_LABELS["location"]}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        _back_col2, _ = st.columns([1, 5])
        with _back_col2:
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

if _wiz_phase == "choose":
    st.markdown(
        '<div class="wiz-hints">'
        "<span>&#8593; to switch &middot; &#8629; to select"
        " &middot; We never store your location.</span>"
        '<a href="./" target="_self">Back to home</a>'
        "</div>",
        unsafe_allow_html=True,
    )

if _wiz_phase != "location":
    st.stop()
if "user_location" not in st.session_state:
    empty_state_card(
        "Pick a location to see recommendations",
        "Once we know where you are, we'll surface your personalised Top-N restaurants nearby.",
        icon_src=_svg_b64("icon-mapview.svg"),
    )
    st.stop()

lat, lon, src_label = st.session_state["user_location"]
_wiz_mode = st.session_state.get("wizard_mode", "returning")
selected_user_id: str | None = st.session_state.get("selected_user_id")
profile = st.session_state.get("cold_start_profile")

if _wiz_mode == "returning":
    st.session_state.pop("cold_start_profile", None)
    profile = None

threshold = 3
regime = classify_user(selected_user_id, interactions, threshold=threshold)
n_history = (
    int((interactions["user_id"] == selected_user_id).sum()) if selected_user_id else 0
)

if regime == "established":
    _banner_msg = (
        f"{n_history} ratings on record — "
        f'<em style="color:var(--accent)">full hybrid model</em>'
        f" with collaborative filtering at the centre."
    )
    _banner_kind = "ok"
elif regime == "light":
    _banner_msg = (
        f"Only {n_history} ratings in history — blending your stated "
        "preferences with collaborative filtering."
    )
    _banner_kind = "warn"
else:
    _banner_msg = (
        "No rating history found — using stated cuisine preferences "
        "plus the most popular nearby restaurants."
    )
    _banner_kind = "warn"

_MODEL_LABELS: dict[str, str] = {
    "hybrid": "Hybrid (recommended)",
    "popularity": "Popularity",
    "content_based": "Content-based",
    "item_cf": "Item-CF",
    "user_cf": "User-CF",
    "matrix_fact": "Matrix Factorization",
}

# Read model + llm toggle from session state (set by widgets rendered below)
_sel_model_key: str = st.session_state.get("selected_model_key", "hybrid")
_use_llm: bool = st.session_state.get("_disc_use_llm", False)

# ---------------------------------------------------------------------------
# 3-column layout
# ---------------------------------------------------------------------------
col_f, col_c, col_r = st.columns([1.1, 3.2, 1.5], gap="large")

# ── Left: filter rail ──────────────────────────────────────────────────────
with col_f:
    filters = render_filter_rail(
        businesses,
        default_radius=profile.radius_km if profile else 5.0,
    )

# ── Build candidate set + score (uses filter values just set) ─────────────
cand = add_distance_column(businesses, lat, lon)
if profile is not None:
    cand = filter_by_profile(cand, profile)
cand = apply_hard_filters(cand, filters)

recs: pd.DataFrame = pd.DataFrame()
_model_swapped = False
weights = None
active_model = None

if not cand.empty:
    hybrid_model: HybridRecommender = models["hybrid"]
    base_weights = HybridWeights(
        personalized=hybrid_model.weights.personalized,
        content=hybrid_model.weights.content,
        popularity=hybrid_model.weights.popularity,
        distance=hybrid_model.weights.distance,
    )
    weights = adjust_weights(base_weights, regime)

    pref_profile = None
    if profile is not None and profile.cuisines:
        pref_profile = models["content_based"].build_preference_profile(
            profile.cuisines,
            attributes=profile.attributes,
            price_levels=profile.price_levels,
        )

    active_model = models[_sel_model_key]
    if getattr(active_model, "needs_user_history", True) and not selected_user_id:
        active_model = models["popularity"]
        _sel_model_key = "popularity"
        _model_swapped = True

    with st.spinner("Scoring …"):
        if _sel_model_key == "hybrid":
            recs = hybrid_model.recommend(
                user_id=selected_user_id,
                candidates=cand,
                top_n=filters.top_n,
                weights=weights,
                preference_profile=pref_profile,
            )
        elif _sel_model_key == "content_based":
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
    if _use_llm or filters.show_components:
        with st.spinner("Generating explanations …"):
            recs = annotate_recommendations(
                recs,
                user_cuisines=user_cuisines,
                reviews_df=reviews,
                use_llm=_use_llm,
                max_llm_calls=5,
            )
    else:
        recs = annotate_recommendations(
            recs,
            user_cuisines=user_cuisines,
            reviews_df=None,
            use_llm=False,
        )

# Persist to disk — HTML link navigation starts a new Streamlit session so
# session_state doesn't survive cross-page navigation via <a> tags.
_RECS_CACHE = ROOT / "app" / "static" / "_last_recs.pkl"
if not recs.empty:
    import pickle as _pickle

    _RECS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(_RECS_CACHE, "wb") as _f:
        _pickle.dump(
            {"recs": recs, "center": (lat, lon), "radius_km": filters.radius_km}, _f
        )
    st.session_state["last_recs"] = recs
    st.session_state["last_center"] = (lat, lon)
    st.session_state["last_radius_km"] = filters.radius_km

n_results = len(recs)
sort_label = _MODEL_LABELS.get(_sel_model_key, _sel_model_key)

# ── Center: results list ───────────────────────────────────────────────────
with col_c:
    status_banner(_banner_kind, _banner_msg)

    if _model_swapped:
        st.info(
            f"**{_MODEL_LABELS.get(st.session_state.get('selected_model_key', 'hybrid'))}** "
            "needs user history — fell back to Popularity."
        )

    st.markdown(
        f"""
        <div class="disc-list-head">
          <h2 class="disc-list-title">{n_results} places <i>on your route</i></h2>
          <div class="disc-list-sort">
            sorted by
            <span class="disc-sort-pill">{sort_label}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _sm1, _sm2, _ = st.columns([3, 2, 1])
    with _sm1:
        st.selectbox(
            "Model",
            options=list(_MODEL_LABELS.keys()),
            format_func=lambda k: _MODEL_LABELS[k],
            key="selected_model_key",
            label_visibility="collapsed",
        )
    with _sm2:
        st.checkbox(
            "Claude 'why' text",
            value=False,
            key="_disc_use_llm",
            help="If GROQ_API_KEY is set, asks Claude for a one-line rationale.",
        )

    if cand.empty:
        st.warning(
            "No restaurants matched the filters. Try widening the radius or "
            "relaxing star / price filters."
        )
    elif recs.empty:
        st.warning("Scoring returned no results.")
    else:
        render_recommendations(
            recs,
            show_components=filters.show_components,
            photo_map=photo_map,
            photos_dir=photos_dir,
        )

    with st.expander("🔬 Under the hood"):
        if _sel_model_key == "hybrid" and weights is not None:
            st.write("**Active hybrid weights** (after cold-start adjustment):")
            st.json(
                {
                    "personalised": round(weights.personalized, 3),
                    "content": round(weights.content, 3),
                    "popularity": round(weights.popularity, 3),
                    "distance": round(weights.distance, 3),
                }
            )
        else:
            st.write(f"**Active model:** {_MODEL_LABELS[_sel_model_key]}")
        st.write(
            f"User regime: `{regime}` · history: `{n_history}` · "
            f"candidates: `{len(cand)}` within {filters.radius_km} km"
        )
        if not recs.empty and {
            "personalised_score",
            "content_score",
            "popularity_score",
            "distance_score",
        }.issubset(recs.columns):
            st.dataframe(
                recs[
                    [
                        "name",
                        "personalised_score",
                        "content_score",
                        "popularity_score",
                        "distance_score",
                        "score",
                    ]
                ].round(3),
                use_container_width=True,
            )

# ── Right: now-driving card ────────────────────────────────────────────────
with col_r:
    city_label = src_label or f"{lat:.3f}, {lon:.3f}"
    radius_disp = f"{filters.radius_km:.0f}"
    st.markdown(
        f"""
        <div class="disc-nd-card">
          <div class="disc-nd-label">Now Driving</div>
          <div class="disc-nd-route">
            {city_label}
            <span class="disc-nd-arrow">&#8594;</span>
            Nearby
          </div>
          <div class="disc-nd-stats">
            <div class="disc-nd-s">
              <b>{len(cand)}</b>
              <small>Candidates</small>
            </div>
            <div class="disc-nd-s">
              <b>{radius_disp}<span style="font-size:.75em;margin-left:1px">km</span></b>
              <small>Radius</small>
            </div>
            <div class="disc-nd-s">
              <b>{n_results}</b>
              <small>Results</small>
            </div>
          </div>
        </div>
        <a class="disc-nd-map-link" href="./Map_View" target="_self">&#128506; View on map &#8594;</a>
        """,
        unsafe_allow_html=True,
    )

render_dock("discover", user_id=st.session_state.get("selected_user_id"))
