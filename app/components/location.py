"""Geolocation picker with multiple fallback strategies.

We try three ways to get the driver's coordinates, in order:

1. **Browser HTML5 geolocation** — best UX. Uses ``streamlit_js_eval`` if it's
   installed; otherwise we inject a JS shim that posts the coords back via
   ``window.parent.postMessage`` and the user copies them into a field.
2. **City centroid** — pick a city from the cities loaded in the dataset and
   we use its centroid.
3. **Manual lat/lon entry** — for when neither of the above is workable.

The picker writes the chosen ``(lat, lon, source_label)`` into
``st.session_state["user_location"]``.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

from src.geo import CITY_CENTROIDS, lookup_city_centroid


def _try_js_geolocation() -> Optional[tuple[float, float]]:
    """Use streamlit_js_eval if available."""
    try:
        from streamlit_js_eval import get_geolocation  # type: ignore
    except ImportError:
        return None
    try:
        coords = get_geolocation()
    except Exception:
        return None
    if coords is None:
        return None
    c = coords.get("coords") if isinstance(coords, dict) else None
    if not c:
        return None
    return float(c.get("latitude")), float(c.get("longitude"))


def render_location_picker(
    cities_in_dataset: list[str] | None = None,
    show_header: bool = True,
) -> tuple[float, float, str] | None:
    """Render the location picker and return (lat, lon, source_label).

    Persists the choice in session state so the UI doesn't ask twice.
    """
    if "user_location" in st.session_state:
        lat, lon, src = st.session_state["user_location"]
        st.markdown(
            f"📍 Using **{src}** &nbsp;·&nbsp; `{lat:.4f}, {lon:.4f}` "
            "&nbsp;·&nbsp; <a href='#' onclick='window.location.reload();return false;'>change</a>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([5, 1])
        with c2:
            if st.button("📍 Change", key="loc_change"):
                del st.session_state["user_location"]
                st.rerun()
        return lat, lon, src

    if show_header:
        st.markdown("### Where are you driving from?")

    tab_gps, tab_city, tab_manual = st.tabs(
        ["🛰 Use my GPS", "🏙 Pick a city", "📌 Enter coordinates"]
    )

    with tab_gps:
        st.caption(
            "Click the button to share your browser's location. "
            "Requires `pip install streamlit-js-eval` and HTTPS."
        )
        if st.button("📡 Get my location", key="gps_btn", type="primary"):
            coords = _try_js_geolocation()
            if coords is None:
                st.error(
                    "Could not get GPS. "
                    "Either the package `streamlit-js-eval` is missing or the "
                    "browser denied permission. Try the other tabs."
                )
            else:
                lat, lon = coords
                st.session_state["user_location"] = (lat, lon, "GPS")
                st.rerun()

    with tab_city:
        options = cities_in_dataset or list(CITY_CENTROIDS.keys())
        chosen = st.selectbox("City", options=options, index=0)
        if st.button("📌 Use this city's centre", key="city_btn"):
            centroid = lookup_city_centroid(chosen)
            if centroid is None:
                st.error(f"No centroid known for {chosen}. Use manual entry.")
            else:
                lat, lon = centroid
                st.session_state["user_location"] = (lat, lon, f"{chosen} centre")
                st.rerun()

    with tab_manual:
        col1, col2 = st.columns(2)
        lat = col1.number_input("Latitude", value=39.9526, format="%.6f")
        lon = col2.number_input("Longitude", value=-75.1652, format="%.6f")
        if st.button("✅ Use these coordinates", key="manual_btn"):
            st.session_state["user_location"] = (
                float(lat),
                float(lon),
                "Manual entry",
            )
            st.rerun()

    return None
