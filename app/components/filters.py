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
    """Render the filter sidebar and return the chosen filters."""
    st.sidebar.markdown("### Refine results")

    if businesses is not None and "categories" in businesses.columns:
        # Build cuisine list from data if available, fallback to defaults
        all_cats: set[str] = set()
        for cats in businesses["categories"].dropna().head(2000):
            for c in str(cats).split(","):
                c = c.strip()
                if c and c.lower() != "restaurants":
                    all_cats.add(c)
        cuisine_options = sorted(all_cats) if all_cats else CUISINE_OPTIONS
    else:
        cuisine_options = CUISINE_OPTIONS

    cuisines = st.sidebar.multiselect(
        "Cuisines (boosted, not hard-filter)",
        options=cuisine_options,
        default=[],
    )

    radius_km = st.sidebar.slider(
        "Radius (km)",
        min_value=0.5,
        max_value=25.0,
        value=float(default_radius),
        step=0.5,
    )

    min_stars = st.sidebar.slider(
        "Minimum stars",
        min_value=1.0,
        max_value=5.0,
        value=3.5,
        step=0.5,
    )

    price_levels = st.sidebar.multiselect(
        "Price levels",
        options=[1, 2, 3, 4],
        default=[1, 2, 3, 4],
        format_func=lambda x: "$" * x,
    )

    st.sidebar.markdown("**Must-have**")
    col1, col2 = st.sidebar.columns(2)
    takeout = col1.checkbox("Takeout", value=False)
    delivery = col2.checkbox("Delivery", value=False)
    outdoor = col1.checkbox("Outdoor", value=False)
    kids = col2.checkbox("Kid-friendly", value=False)

    attributes: list[str] = []
    if takeout:
        attributes.append("takeout")
    if delivery:
        attributes.append("delivery")
    if outdoor:
        attributes.append("outdoor")
    if kids:
        attributes.append("kids")

    open_now = st.sidebar.checkbox("Open right now", value=False)

    st.sidebar.markdown("---")
    top_n = st.sidebar.slider("Top-N", min_value=3, max_value=20, value=8)
    show_components = st.sidebar.checkbox(
        "Show score breakdown",
        value=False,
        help="Reveal the four hybrid components per card.",
    )

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


def apply_hard_filters(
    businesses: pd.DataFrame, filters: UserFilters
) -> pd.DataFrame:
    """Apply hard filters (radius, stars, price, attributes) before scoring."""
    df = businesses.copy()
    if "distance_km" in df.columns:
        df = df[df["distance_km"] <= filters.radius_km]
    if filters.min_stars > 1.0:
        df = df[df["stars"] >= filters.min_stars]
    if filters.price_levels:
        df = df[
            df["price_level"].isin(filters.price_levels) | df["price_level"].isna()
        ]
    for attr in filters.attributes:
        if attr in df.columns:
            df = df[df[attr] == True]  # noqa: E712
    return df.reset_index(drop=True)
