"""Streamlit landing page — PITSTOP hero."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.components.styles import inject_css, render_dock, render_topnav  # noqa: E402
from src.pipeline import has_processed_data, has_trained_models  # noqa: E402

st.set_page_config(
    page_title="Pitstop · Drive. Discover.",
    page_icon="·",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

# ---------------------------------------------------------------------------
# Load food hero image (drop food-hero.png into app/static/ to enable)
# ---------------------------------------------------------------------------
_STATIC = ROOT / "app" / "static"


def _img_b64(path: Path) -> str:
    if not path.exists():
        return ""
    ext = path.suffix.lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/{mime};base64,{data}"


_food_src = _img_b64(_STATIC / "food-hero.png")
_food_html = (
    f'<div class="ps-hero-art"><img src="{_food_src}" alt="" /></div>'
    if _food_src
    else ""
)

processed_ok = has_processed_data()
models_ok = has_trained_models()
spots_count = "14" if models_ok else "—"

render_topnav("app")

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <section class="ps-hero">

      <div class="ps-status-chip">
        <span class="pulse-dot"></span>
        Live &middot; {spots_count} spots near you
      </div>

      <div class="ps-corner-meta">
        <div><b>v0.4</b> &middot; public beta</div>
        <div>CarPlay &amp; Android&nbsp;Auto</div>
      </div>

      <div class="ps-hero-stack">
        {_food_html}
        <div class="ps-subline-wrap">
          <div class="ps-dashed"></div>
          <p class="ps-subline">Fast &middot; local &middot; routed live from your dashboard.</p>
        </div>
      </div>

    </section>
    """,
    unsafe_allow_html=True,
)

render_dock("app", user_id=st.session_state.get("selected_user_id"))
