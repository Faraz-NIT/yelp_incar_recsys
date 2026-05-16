"""Restaurant recommendation cards."""
from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st


def _photo_b64(business_id: str, photo_map: dict[str, list[str]], photos_dir: Path | None) -> str | None:
    """Return base64-encoded JPEG for the first available photo of a business."""
    if not photo_map or not photos_dir or not photos_dir.is_dir():
        return None
    photo_ids = photo_map.get(business_id, [])
    for pid in photo_ids:
        path = photos_dir / f"{pid}.jpg"
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode()
    return None


def _star_string(stars: float | None) -> str:
    if stars is None or pd.isna(stars):
        return "—"
    full = int(stars)
    half = (stars - full) >= 0.5
    return "★" * full + ("½" if half else "") + " " + f"{stars:.1f}"


def _price_string(level: float | None) -> str:
    if level is None or pd.isna(level):
        return ""
    return "$" * int(level)


def _format_categories(cats: str | None, limit: int = 3) -> list[str]:
    if not cats:
        return []
    parts = [c.strip() for c in cats.split(",") if c.strip().lower() != "restaurants"]
    return parts[:limit]


def render_card(
    rank: int,
    row: pd.Series,
    show_components: bool = False,
    photo_b64: str | None = None,
) -> None:
    """Render a single recommendation card."""
    name = row.get("name", "—")
    stars = _star_string(row.get("stars"))
    price = _price_string(row.get("price_level"))
    cats = _format_categories(row.get("categories"))
    address = row.get("address", "")
    city = row.get("city", "")
    distance = row.get("distance_km")
    why = row.get("why", "")

    meta_pieces = [stars]
    if price:
        meta_pieces.append(price)
    if pd.notna(distance):
        meta_pieces.append(f"{distance:.1f} km")
    if row.get("review_count"):
        meta_pieces.append(f"{int(row['review_count'])} reviews")
    meta_str = " &nbsp;·&nbsp; ".join(meta_pieces)

    tags_html = "".join(f'<span class="tag">{c}</span>' for c in cats)
    if row.get("takeout") is True:
        tags_html += '<span class="tag tag-success">Takeout</span>'
    if row.get("delivery") is True:
        tags_html += '<span class="tag tag-success">Delivery</span>'
    if row.get("outdoor") is True:
        tags_html += '<span class="tag">Outdoor</span>'

    address_html = (
        f'<div class="rec-card-meta">📍 {address}, {city}</div>'
        if address
        else ""
    )
    why_html = f'<div class="rec-card-why">{why}</div>' if why else ""

    score_pct = int(round(float(row.get("score", 0)) * 100))

    if photo_b64:
        photo_html = (
            f'<div class="rec-card-photo">'
            f'<img src="data:image/jpeg;base64,{photo_b64}" alt="{name}" />'
            f'</div>'
        )
    else:
        photo_html = '<div class="rec-card-photo-placeholder">🍽️</div>'

    st.markdown(
        f"""
        <div class="rec-card">
            {photo_html}
            <div class="rec-card-rank">#{rank}</div>
            <div class="rec-card-name">{name}</div>
            <div class="rec-card-meta">{meta_str}
                &nbsp;·&nbsp;
                <span class="tag tag-accent">Match {score_pct}%</span>
            </div>
            {address_html}
            <div>{tags_html}</div>
            {why_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if show_components:
        with st.expander("🔬 Score breakdown", expanded=False):
            cols = st.columns(4)
            for col, (label, key) in zip(
                cols,
                [
                    ("Personalised", "personalised_score"),
                    ("Content", "content_score"),
                    ("Popularity", "popularity_score"),
                    ("Distance", "distance_score"),
                ],
            ):
                val = row.get(key)
                if pd.notna(val):
                    col.metric(label, f"{float(val):.2f}")


def render_recommendations(
    recs: pd.DataFrame,
    show_components: bool = False,
    photo_map: dict[str, list[str]] | None = None,
    photos_dir: Path | None = None,
) -> None:
    """Render a vertical list of recommendation cards."""
    if recs.empty:
        st.warning("No recommendations to show. Try widening the radius or relaxing filters.")
        return
    for i, (_, row) in enumerate(recs.iterrows(), 1):
        bid = str(row.get("business_id", ""))
        photo_b64 = _photo_b64(bid, photo_map or {}, photos_dir) if bid else None
        render_card(i, row, show_components=show_components, photo_b64=photo_b64)
