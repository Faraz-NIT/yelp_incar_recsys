"""Discover page: pick user, set GPS, get hybrid recommendations.

Flow:
  1. Confirm processed data + trained models are present.
  2. User picks an existing user_id (or chooses cold-start mode).
  3. User confirms GPS / picks city / enters coordinates.
  4. Sidebar filters (cuisines, price, radius, attributes, top-N).
  5. We compute distances, apply hard filters, run the hybrid scorer.
  6. Optional Claude annotation for the "why" per card.
  7. Render the cards.
"""
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
    breadcrumb,
    empty_state_card,
    field_label,
    inject_css,
    sidebar_extras,
    sidebar_logo,
    status_banner,
    step_header,
    styled_page_header,
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


st.set_page_config(page_title="Discover", page_icon="🍽️", layout="wide")
inject_css()
sidebar_logo(ROOT / "app" / "static" / "mcgill_logo.png")
sidebar_extras(user_id=st.session_state.get("selected_user_id"))
breadcrumb(("Recommendations", False), ("Discover", True))
styled_page_header(
    "Discover",
    "Find a great place to eat — wherever you are right now.",
    icon_src=_ICON_DISCOVER,
)


# ---------------------------------------------------------------------------
# Data + model loading (cached)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_models() -> dict:
    """Load all five trained recommenders + assemble the hybrid."""
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


data = _load_data()
models = _load_models()
photo_map = _load_photo_map()
photos_dir = RAW_DIR / "photos"

if not data or "businesses" not in data:
    status_banner(
        "err",
        "No processed data found. Run the pipeline from the Admin page first.",
    )
    st.stop()

if not models:
    status_banner(
        "err",
        "Trained models missing. Train them from the Admin page first.",
    )
    st.stop()

businesses = data["businesses"]
interactions = data.get("interactions", pd.DataFrame(columns=["user_id", "business_id"]))
reviews = data.get("reviews")

# ---------------------------------------------------------------------------
# Identity selector
# ---------------------------------------------------------------------------
step_header(
    "01",
    "Who's driving?",
    "Choose a returning user to get personalised picks, or start fresh.",
)

# Pre-compute the top-N users by interaction count so the demo always has
# someone with real history available — picking a random user from a 600-user
# pool is more demonstrative than asking the user to type an opaque ID.
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
    field_label("Mode")
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
            field_label("Pick a user")
            selected_user_id = st.selectbox(
                "Pick a user",
                options=top_users,
                format_func=lambda u: f"{u[:8]}… ({int((interactions['user_id'] == u).sum())} ratings)",
                label_visibility="collapsed",
            )
        else:
            st.info("No users in interactions yet.")

st.session_state["selected_user_id"] = selected_user_id

# Show cold-start regime + explanation
threshold = 3
regime = classify_user(selected_user_id, interactions, threshold=threshold)
n_history = int((interactions["user_id"] == selected_user_id).sum()) if selected_user_id else 0
status_banner(
    "ok" if regime == "established" else "warn",
    get_cold_start_explanation(regime, n_history),
)

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
# Location
# ---------------------------------------------------------------------------
step_header(
    "02",
    "Where are you driving from?",
    "Three ways to set a starting point. We never store it.",
)
loc = render_location_picker()
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
    help="If ANTHROPIC_API_KEY is set, asks Claude for a one-line rationale "
    "per recommendation. Falls back to a template otherwise.",
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

# Pre-compute a content preference profile if we have explicit cold-start
# cuisine choices — overrides the user-history-based content signal.
pref_profile = None
if profile is not None and profile.cuisines:
    pref_profile = models["content_based"].build_preference_profile(profile.cuisines)

with st.spinner("Scoring restaurants ..."):
    recs = hybrid.recommend(
        user_id=selected_user_id,
        candidates=cand,
        top_n=filters.top_n,
        weights=weights,
        preference_profile=pref_profile,
    )

# Optional LLM annotation
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
    # Template fallback for "why"
    recs = annotate_recommendations(
        recs,
        user_cuisines=user_cuisines,
        reviews_df=None,
        use_llm=False,
    )

# ---------------------------------------------------------------------------
# Header strip with the active mix
# ---------------------------------------------------------------------------
step_header("03", "Recommendations")
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("Candidates", len(cand))
mc2.metric("Returned", len(recs))
mc3.metric(
    "Personalised w.", f"{weights.personalized:.2f}", delta=f"{weights.personalized - base_weights.personalized:+.2f}"
)
mc4.metric("Content w.", f"{weights.content:.2f}")
mc5.metric(
    "From", src_label,
    help=f"Lat {lat:.4f}, Lon {lon:.4f}",
)

# Persist the latest recs so the Map page can pick them up
st.session_state["last_recs"] = recs
st.session_state["last_center"] = (lat, lon)
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
    st.write("**Active hybrid weights** (after cold-start adjustment):")
    st.json(
        {
            "personalised": round(weights.personalized, 3),
            "content": round(weights.content, 3),
            "popularity": round(weights.popularity, 3),
            "distance": round(weights.distance, 3),
        }
    )
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
