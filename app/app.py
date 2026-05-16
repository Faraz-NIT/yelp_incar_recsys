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

from app.components.styles import (  # noqa: E402
    inject_css,
    page_header,
    sidebar_extras,
    sidebar_logo,
    status_banner,
)
from src.pipeline import has_processed_data, has_trained_models, load_metadata  # noqa: E402


st.set_page_config(
    page_title="In-Car Restaurant Recommender",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
sidebar_logo(ROOT / "app" / "static" / "mcgill_logo.png")
sidebar_extras()

# ---------------------------------------------------------------------------
# Hero — two-column card with inline SVG illustration
# ---------------------------------------------------------------------------
def _read_svg(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

_STATIC = ROOT / "app" / "static"

def _svg_img_tag(path: Path, alt: str = "") -> str:
    """Return an <img> tag with the SVG embedded as a base64 data URI."""
    content = _read_svg(path)
    if not content:
        return ""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" alt="{alt}" class="hero-img"/>'

_hero_right = _svg_img_tag(_STATIC / "hero.svg", "In-car restaurant illustration")

st.markdown(
    f"""
    <div class="hero-card">
      <div class="hero-left">
        <span class="hero-eyebrow">In-Car &middot; Recommendations</span>
        <h1 class="hero-title">Where to <em class="hero-accent">next</em>.</h1>
        <p class="hero-subtitle">
          A personalised restaurant concierge for the road &mdash;
          surfacing the right table at the right moment, wherever
          the drive takes you.
        </p>
        <div class="hero-pills">
          <span class="hero-pill"><span class="hero-pill-dot">&#9679;</span>Live recommendations</span>
          <span class="hero-pill">Top-N &middot; personalised</span>
        </div>
      </div>
      <div class="hero-right">
        {_hero_right}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------
processed_ok = has_processed_data()
models_ok = has_trained_models()
meta = load_metadata() if models_ok else {}

c1, c2 = st.columns(2)
with c1:
    if processed_ok:
        status_banner("ok", "Processed dataset available")
    else:
        status_banner(
            "warn",
            "No processed data yet — head to the Admin page to run the pipeline.",
        )
with c2:
    if models_ok:
        status_banner(
            "ok",
            f"Trained models available "
            f"({meta.get('n_users', '?')} users · "
            f"{meta.get('n_businesses', '?')} restaurants)",
        )
    else:
        status_banner(
            "warn",
            "No trained models on disk — train them from the Admin page.",
        )

st.markdown("")

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
    (_ICON_DISCOVER, "Discover",  "Pick a user, set your location, get a personalised Top-N restaurant list."),
    (_ICON_MAP,      "Map View",  "See recommendations as colour-coded pins on an interactive map."),
    (_ICON_ADMIN,    "Admin",     "Configure cities, thresholds, and run the full data + training pipeline."),
    (_ICON_ANALYTICS,"Analytics", "Model comparison table, sentiment distributions, and EDA charts."),
]
for col, (icon, title, blurb) in zip(nav_cols, nav_cards):
    col.markdown(
        f"""
        <div class="nav-card">
          <span class="nav-card-icon">{icon}</span>
          <div class="nav-card-title">{title}</div>
          <div class="nav-card-desc">{blurb}</div>
          <span class="nav-card-arrow">&#8594;</span>
        </div>
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
