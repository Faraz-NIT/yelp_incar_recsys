"""Cold-start onboarding wizard for new users."""
from __future__ import annotations

import streamlit as st

from src.cold_start import ColdStartProfile
from src.config import ATTRIBUTE_LABELS, CUISINE_OPTIONS

_CUISINE_SVG = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 11h18a9 9 0 0 1-9 9 9 9 0 0 1-9-9z"/>
  <line x1="6" y1="15" x2="18" y2="15"/>
  <path d="M9 7c0-2 3-2 3-4 M14 7c0-2 3-2 3-4"/>
</svg>"""

_PRICE_SVG = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="6" width="18" height="12" rx="2"/>
  <line x1="3" y1="10" x2="21" y2="10"/>
  <line x1="7" y1="15" x2="11" y2="15"/>
</svg>"""

_CHECK_SVG = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="9 11 12 14 22 4"/>
  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
</svg>"""

_RADIUS_SVG = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="9" stroke-dasharray="3 3"/>
  <circle cx="12" cy="12" r="2.5" fill="currentColor"/>
</svg>"""


def _sec_head(icon_svg: str, label: str, heading: str, req: str = "", first: bool = False) -> str:
    req_html = f'<span class="cs-req">&#x2014; {req}</span>' if req else ""
    extra = " cs-sec-head-first" if first else ""
    return f"""
<div class="cs-sec-head{extra}">
  <div class="cs-sec-left">
    <div class="cs-sec-icon">{icon_svg}</div>
    <div>
      <div class="cs-sec-label-txt">{label}{req_html}</div>
      <h3 class="cs-sec-h3">{heading}</h3>
    </div>
  </div>
</div>"""


def render_onboarding(default_radius: float = 5.0) -> ColdStartProfile | None:
    """Render the Cold Start onboarding card.

    Returns the captured ColdStartProfile when submitted, else None.
    """
    if "cold_start_profile" in st.session_state:
        return st.session_state["cold_start_profile"]

    # ── Card head: title + step indicator ────────────────────────────────────
    st.markdown("""
<div class="cs-head">
  <div class="cs-head-left">
    <h1 class="cs-title">Tell us your <span class="cs-accent">taste.</span></h1>
    <p class="cs-subtitle">We don&#8217;t have any history for you yet &#x2014; a few quick questions and we&#8217;ll start hand-picking.</p>
  </div>
  <nav class="cs-stepper" aria-label="Step 1 of 3">
    <div class="cs-step-dot cs-step-active">
      <span class="cs-step-n">1</span>
      <span class="cs-step-label">Taste</span>
    </div>
    <span class="cs-step-line"></span>
    <div class="cs-step-dot">
      <span class="cs-step-n">2</span>
      <span class="cs-step-label">Where</span>
    </div>
    <span class="cs-step-line"></span>
    <div class="cs-step-dot">
      <span class="cs-step-n">3</span>
      <span class="cs-step-label">Picks</span>
    </div>
  </nav>
</div>
""", unsafe_allow_html=True)

    with st.form("cold_start_form"):

        # ── Cuisines ──────────────────────────────────────────────────────────
        st.markdown(_sec_head(
            _CUISINE_SVG,
            label="Cuisines you enjoy",
            heading="What&#8217;s on the menu",
            req="pick 2 to 6",
            first=True,
        ), unsafe_allow_html=True)
        cuisines = st.multiselect(
            "Cuisines",
            options=CUISINE_OPTIONS,
            default=["Italian", "Japanese", "Mexican"],
            max_selections=6,
            label_visibility="collapsed",
        )

        # ── Budget ────────────────────────────────────────────────────────────
        st.markdown(_sec_head(
            _PRICE_SVG,
            label="Price levels you&#8217;re comfortable with",
            heading="Budget",
        ), unsafe_allow_html=True)
        price_levels = st.multiselect(
            "Price",
            options=[1, 2, 3, 4],
            default=[1, 2, 3],
            format_func=lambda x: {
                1: "$ — Inexpensive",
                2: "$$ — Moderate",
                3: "$$$ — Pricey",
                4: "$$$$ — Splurge",
            }[x],
            label_visibility="collapsed",
        )

        # ── Preferences ───────────────────────────────────────────────────────
        st.markdown(_sec_head(
            _CHECK_SVG,
            label="Preferences",
            heading="How you like to dine",
        ), unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            takeout = st.toggle("Takeout available", value=True)
            outdoor = st.toggle("Outdoor seating",   value=False)
        with col2:
            delivery = st.toggle("Delivery available", value=False)
            kids     = st.toggle("Kid-friendly",       value=False)

        # ── Radius ────────────────────────────────────────────────────────────
        st.markdown(_sec_head(
            _RADIUS_SVG,
            label="How far you&#8217;ll drive",
            heading="Search radius",
        ), unsafe_allow_html=True)
        radius = st.slider(
            "Search radius (km)",
            min_value=1.0, max_value=25.0,
            value=float(default_radius), step=0.5,
            label_visibility="collapsed",
        )

        # ── Footer ────────────────────────────────────────────────────────────
        st.markdown('<div class="cs-foot-sep"></div>', unsafe_allow_html=True)
        col_note, col_btn = st.columns([3, 2])
        with col_note:
            st.markdown(
                '<p class="cs-foot-note">Bon app&#233;tit &#x2014; we&#8217;ll save these for next time.</p>',
                unsafe_allow_html=True,
            )
        with col_btn:
            submitted = st.form_submit_button(
                "Save my preferences →",
                type="primary",
                use_container_width=True,
            )

    if not submitted:
        return None
    if not cuisines:
        st.error("Please pick at least one cuisine.")
        return None

    attributes: list[str] = []
    if takeout:  attributes.append("takeout")
    if delivery: attributes.append("delivery")
    if outdoor:  attributes.append("outdoor")
    if kids:     attributes.append("kids")

    profile = ColdStartProfile(
        cuisines=cuisines,
        attributes=attributes,
        price_levels=price_levels,
        radius_km=radius,
    )
    st.session_state["cold_start_profile"] = profile
    return profile
