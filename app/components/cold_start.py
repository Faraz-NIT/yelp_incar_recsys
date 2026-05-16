"""Cold-start onboarding wizard for new users."""
from __future__ import annotations

import streamlit as st

from src.cold_start import ColdStartProfile
from src.config import ATTRIBUTE_LABELS, CUISINE_OPTIONS


def render_onboarding(default_radius: float = 5.0) -> ColdStartProfile | None:
    """Render the onboarding wizard.

    Returns
    -------
    ColdStartProfile | None
        The captured profile when the user submits, else ``None``.
    """
    # Return already-submitted profile so it survives Streamlit reruns.
    if "cold_start_profile" in st.session_state:
        return st.session_state["cold_start_profile"]

    st.markdown(
        "### Welcome — let's tune your in-car recommendations"
    )
    st.caption(
        "We don't have any history for you yet. Tell us a bit about your taste "
        "so we can hand-pick restaurants while you're on the road."
    )

    with st.form("cold_start_form"):
        cuisines = st.multiselect(
            "🍜 Cuisines you enjoy (pick 2–6)",
            options=CUISINE_OPTIONS,
            default=["Italian", "Japanese", "Mexican"],
            max_selections=6,
        )
        price_levels = st.multiselect(
            "💵 Price levels you're comfortable with",
            options=[1, 2, 3, 4],
            default=[1, 2, 3],
            format_func=lambda x: "$" * x + (
                {1: " — Inexpensive", 2: " — Moderate",
                 3: " — Pricey", 4: " — Ultra High-End"}[x]
            ),
        )
        col1, col2 = st.columns(2)
        with col1:
            takeout = st.checkbox("Takeout available", value=True)
            outdoor = st.checkbox("Outdoor seating", value=False)
        with col2:
            delivery = st.checkbox("Delivery available", value=False)
            kids = st.checkbox("Kid-friendly", value=False)

        radius = st.slider(
            "🚗 Search radius (km)",
            min_value=1.0,
            max_value=25.0,
            value=float(default_radius),
            step=0.5,
            help="How far you're willing to drive right now.",
        )

        submitted = st.form_submit_button("✨ Save my preferences", type="primary")

    if not submitted:
        return None

    if not cuisines:
        st.error("Please pick at least one cuisine.")
        return None

    attributes = []
    if takeout:
        attributes.append("takeout")
    if delivery:
        attributes.append("delivery")
    if outdoor:
        attributes.append("outdoor")
    if kids:
        attributes.append("kids")

    profile = ColdStartProfile(
        cuisines=cuisines,
        attributes=attributes,
        price_levels=price_levels,
        radius_km=radius,
    )
    st.session_state["cold_start_profile"] = profile
    return profile
