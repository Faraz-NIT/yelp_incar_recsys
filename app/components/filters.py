"""Sidebar filter controls."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.config import CUISINE_OPTIONS


@dataclass
class UserFilters:
    cuisines: list[str]
    price_levels: list[int]
    radius_km: float
    min_stars: float
    attributes: list[str]
    open_now_only: bool
    top_n: int
    show_components: bool


def render_filter_sidebar(
    businesses: pd.DataFrame | None,
    default_radius: float = 5.0,
) -> UserFilters:
    """Render inline filter controls (sidebar replaced by expander)."""
    if businesses is not None and "categories" in businesses.columns:
        all_cats: set[str] = set()
        for cats in businesses["categories"].dropna().head(2000):
            for c in str(cats).split(","):
                c = c.strip()
                if c and c.lower() != "restaurants":
                    all_cats.add(c)
        cuisine_options = sorted(all_cats) if all_cats else CUISINE_OPTIONS
    else:
        cuisine_options = CUISINE_OPTIONS

    with st.expander("Refine results", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            cuisines = st.multiselect(
                "Cuisines (boosted)",
                options=cuisine_options,
                default=[],
            )
            radius_km = st.slider(
                "Radius (km)",
                min_value=0.5,
                max_value=25.0,
                value=float(default_radius),
                step=0.5,
            )
        with fc2:
            min_stars = st.slider(
                "Min stars",
                min_value=1.0,
                max_value=5.0,
                value=3.5,
                step=0.5,
            )
            price_levels = st.multiselect(
                "Price levels",
                options=[1, 2, 3, 4],
                default=[1, 2, 3, 4],
                format_func=lambda x: "$" * x,
            )
        with fc3:
            top_n = st.slider("Top-N", min_value=3, max_value=20, value=8)
            open_now = st.checkbox("Open right now", value=False)
            show_components = st.checkbox(
                "Show score breakdown",
                value=False,
                help="Reveal the four hybrid components per card.",
            )
            bc1, bc2 = st.columns(2)
            takeout = bc1.checkbox("Takeout", value=False)
            delivery = bc2.checkbox("Delivery", value=False)
            outdoor = bc1.checkbox("Outdoor", value=False)
            kids = bc2.checkbox("Kid-friendly", value=False)

    attributes: list[str] = []
    if takeout:
        attributes.append("takeout")
    if delivery:
        attributes.append("delivery")
    if outdoor:
        attributes.append("outdoor")
    if kids:
        attributes.append("kids")

    return UserFilters(
        cuisines=cuisines,
        price_levels=price_levels,
        radius_km=radius_km,
        min_stars=min_stars,
        attributes=attributes,
        open_now_only=open_now,
        top_n=top_n,
        show_components=show_components,
    )


def render_filter_rail(
    businesses: pd.DataFrame | None,
    default_radius: float = 5.0,
) -> UserFilters:
    """Render filter widgets directly in the calling column (no expander wrapper)."""
    if businesses is not None and "categories" in businesses.columns:
        all_cats: set[str] = set()
        for cats in businesses["categories"].dropna().head(2000):
            for c in str(cats).split(","):
                c = c.strip()
                if c and c.lower() != "restaurants":
                    all_cats.add(c)
        cuisine_options = sorted(all_cats) if all_cats else CUISINE_OPTIONS
    else:
        cuisine_options = CUISINE_OPTIONS

    st.markdown('<p class="disc-frail-head">Filters</p>', unsafe_allow_html=True)

    st.markdown('<span class="disc-flabel">Cuisines</span>', unsafe_allow_html=True)
    cuisines = st.multiselect(
        "Cuisines",
        options=cuisine_options,
        default=[],
        label_visibility="collapsed",
        key="fr_cuisines",
    )

    st.markdown('<span class="disc-flabel">Radius (km)</span>', unsafe_allow_html=True)
    radius_km = st.slider(
        "Radius",
        min_value=0.5,
        max_value=25.0,
        value=float(default_radius),
        step=0.5,
        label_visibility="collapsed",
        key="fr_radius",
    )

    st.markdown('<div class="disc-fdivider"></div>', unsafe_allow_html=True)

    st.markdown('<span class="disc-flabel">Min Stars</span>', unsafe_allow_html=True)
    min_stars = st.slider(
        "Min stars",
        min_value=1.0,
        max_value=5.0,
        value=3.5,
        step=0.5,
        label_visibility="collapsed",
        key="fr_min_stars",
    )

    st.markdown('<span class="disc-flabel">Price</span>', unsafe_allow_html=True)
    price_levels = st.multiselect(
        "Price",
        options=[1, 2, 3, 4],
        default=[1, 2, 3, 4],
        format_func=lambda x: "$" * x,
        label_visibility="collapsed",
        key="fr_price",
    )

    st.markdown('<div class="disc-fdivider"></div>', unsafe_allow_html=True)

    st.markdown('<span class="disc-flabel">Results</span>', unsafe_allow_html=True)
    top_n = st.slider(
        "Top-N",
        min_value=3,
        max_value=20,
        value=8,
        label_visibility="collapsed",
        key="fr_top_n",
    )
    open_now = st.checkbox("Open now", value=False, key="fr_open_now")
    show_components = st.checkbox(
        "Score breakdown", value=False, key="fr_show_components"
    )

    st.markdown('<span class="disc-flabel">Amenities</span>', unsafe_allow_html=True)
    bc1, bc2 = st.columns(2)
    takeout = bc1.checkbox("Takeout", value=False, key="fr_takeout")
    delivery = bc2.checkbox("Delivery", value=False, key="fr_delivery")
    outdoor = bc1.checkbox("Outdoor", value=False, key="fr_outdoor")
    kids = bc2.checkbox("Kids", value=False, key="fr_kids")

    attributes: list[str] = []
    if takeout:
        attributes.append("takeout")
    if delivery:
        attributes.append("delivery")
    if outdoor:
        attributes.append("outdoor")
    if kids:
        attributes.append("kids")

    return UserFilters(
        cuisines=cuisines,
        price_levels=price_levels,
        radius_km=radius_km,
        min_stars=min_stars,
        attributes=attributes,
        open_now_only=open_now,
        top_n=top_n,
        show_components=show_components,
    )


def apply_hard_filters(businesses: pd.DataFrame, filters: UserFilters) -> pd.DataFrame:
    """Apply hard filters (radius, stars, price, attributes) before scoring."""
    df = businesses.copy()
    if "distance_km" in df.columns:
        df = df[df["distance_km"] <= filters.radius_km]
    if filters.min_stars > 1.0:
        df = df[df["stars"] >= filters.min_stars]
    if filters.price_levels:
        df = df[df["price_level"].isin(filters.price_levels) | df["price_level"].isna()]
    for attr in filters.attributes:
        if attr in df.columns:
            df = df[df[attr] == True]  # noqa: E712
    return df.reset_index(drop=True)
