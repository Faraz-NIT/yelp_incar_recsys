"""Streamlit landing page for the in-car restaurant recommender.

This is the front door. From here the user navigates to Discover, Map,
Admin, or Analytics in the sidebar.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

# Make ``src`` importable when streamlit launches us from app/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.components.carousel import _load_city_photos, render_hero_carousel  # noqa: E402
from app.components.styles import (  # noqa: E402
    inject_css,
    page_header,
    sidebar_extras,
    sidebar_logo,
)
from src.config import DEFAULT_CONFIG, RAW_DIR  # noqa: E402
from src.geo import CITY_CENTROIDS  # noqa: E402
from src.pipeline import has_processed_data, has_trained_models, load_metadata  # noqa: E402
from src.preprocessing import load_processed  # noqa: E402
from src.utils import load_business_photos  # noqa: E402


st.set_page_config(
    page_title="In-Car Restaurant Recommender",
    page_icon="·",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
sidebar_logo(ROOT / "app" / "static" / "mcgill_logo.png")

# ---------------------------------------------------------------------------
# Sidebar city selector
# ---------------------------------------------------------------------------
_all_cities = sorted(CITY_CENTROIDS.keys())
_default_city = DEFAULT_CONFIG.cities[0] if DEFAULT_CONFIG.cities else _all_cities[0]
_default_idx = _all_cities.index(_default_city) if _default_city in _all_cities else 0

st.sidebar.markdown(
    '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;'
    'color:#9CA3AF;text-transform:uppercase;margin:1.2rem 0 0.4rem 0.5rem;">EXPLORE CITY</p>',
    unsafe_allow_html=True,
)
selected_city: str | None = st.sidebar.selectbox(
    "City",
    options=_all_cities,
    index=None,
    placeholder="Select a city…",
    label_visibility="collapsed",
    key="home_city",
)

processed_ok = has_processed_data()
models_ok = has_trained_models()
meta = load_metadata() if models_ok else {}

sidebar_extras(
    user_id=st.session_state.get("selected_user_id"),
    processed_ok=processed_ok,
    models_ok=models_ok,
    meta=meta,
)

# ---------------------------------------------------------------------------
# Photo loader (cached per city)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _city_photos(city: str, max_n: int = 10) -> list[dict]:
    photo_map = load_business_photos(RAW_DIR)
    photos_dir = RAW_DIR / "photos"
    data = load_processed()
    if not data or "businesses" not in data:
        return []
    businesses = data["businesses"]
    if "city" not in businesses.columns:
        return []
    cols = [c for c in ["business_id", "name", "stars", "categories"] if c in businesses.columns]
    city_biz = (
        businesses[businesses["city"] == city][cols]
        .sort_values("stars", ascending=False)
        .to_dict("records")
    )
    return _load_city_photos(photo_map, photos_dir, city_biz, max_n)


# ---------------------------------------------------------------------------
# Hero + carousel (combined, photo panel on the right of the hero card)
# ---------------------------------------------------------------------------
_slides = _city_photos(selected_city) if selected_city else []
render_hero_carousel(_slides, city_name=selected_city or "")

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="section-header">
      <span class="section-title">Where to next</span>
      <span class="section-label">Section Icons &middot; In Context</span>
    </div>
    """,
    unsafe_allow_html=True,
)

_STATIC = ROOT / "app" / "static"

def _read_svg(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def _icon_img(path: Path, alt: str = "") -> str:
    content = _read_svg(path)
    if not content:
        return ""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" alt="{alt}" width="36" height="36"/>'

_ICON_DISCOVER  = _icon_img(_STATIC / "icon-discover.svg",  "Discover")
_ICON_MAP       = _icon_img(_STATIC / "icon-mapview.svg",   "Map View")
_ICON_ADMIN     = _icon_img(_STATIC / "icon-admin.svg",     "Admin")
_ICON_ANALYTICS = _icon_img(_STATIC / "icon-analytics.svg", "Analytics")

nav_cols = st.columns(4)
nav_cards = [
    (_ICON_DISCOVER,  "Discover",   "Pick a user, set your location, get a personalised Top-N restaurant list.", "./Discover"),
    (_ICON_MAP,       "Map View",   "See recommendations as colour-coded pins on an interactive map.",          "./Map_View"),
    (_ICON_ADMIN,     "Admin",      "Configure cities, thresholds, and run the full data + training pipeline.", "./Admin"),
    (_ICON_ANALYTICS, "Analytics",  "Model comparison table, sentiment distributions, and EDA charts.",         "./Analytics"),
]
for col, (icon, title, blurb, href) in zip(nav_cols, nav_cards):
    col.markdown(
        f"""
        <a class="nav-card" href="{href}" target="_self">
          <span class="nav-card-icon">{icon}</span>
          <div class="nav-card-title">{title}</div>
          <div class="nav-card-desc">{blurb}</div>
          <span class="nav-card-arrow">&#8594;</span>
        </a>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
fcol1, fcol2, fcol3 = st.columns(3)
fcol1.markdown(
    "**Cold-start aware** — new users describe their taste; weights rebalance."
)
fcol2.markdown(
    "**LLM-augmented (optional)** — Claude generates a one-sentence "
    "rationale per recommendation when an API key is present."
)
fcol3.markdown(
    "**Reproducible** — every stage runnable from CLI or the Admin page."
)
