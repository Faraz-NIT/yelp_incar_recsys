"""Map view: visualise the user location, radius, and ranked pins."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.components.styles import inject_css, page_header, render_dock, render_topnav, status_banner  # noqa: E402
from src.preprocessing import load_processed  # noqa: E402


st.set_page_config(page_title="Map View", page_icon="·", layout="wide", initial_sidebar_state="collapsed")
inject_css()
render_topnav("map")
page_header("Map View", "Where the recommendations actually are.")


import pickle as _pickle

_RECS_CACHE = ROOT / "app" / "static" / "_last_recs.pkl"

recs: pd.DataFrame | None = st.session_state.get("last_recs")
center = st.session_state.get("last_center")
radius_km = st.session_state.get("last_radius_km", 5.0)

# Session state is empty when navigating via HTML links (new WebSocket session).
# Fall back to the file written by the Discover page.
if (recs is None or recs.empty) and _RECS_CACHE.exists():
    try:
        with open(_RECS_CACHE, "rb") as _f:
            _cached = _pickle.load(_f)
        recs      = _cached.get("recs")
        center    = _cached.get("center")
        radius_km = _cached.get("radius_km", 5.0)
    except Exception:
        pass

have_recs = recs is not None and not recs.empty and center is not None

# ---------------------------------------------------------------------------
# Fallback: load all businesses if no recommendations yet
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _load_businesses() -> pd.DataFrame | None:
    data = load_processed()
    biz = data.get("businesses")
    if biz is None or biz.empty:
        return None
    needed = ["latitude", "longitude", "name", "stars", "categories"]
    if not all(c in biz.columns for c in ["latitude", "longitude"]):
        return None
    return biz[[c for c in needed if c in biz.columns]].dropna(subset=["latitude", "longitude"])


if not have_recs:
    status_banner(
        "info",
        'Showing all indexed restaurants. '
        '<a href="./Discover" target="_self" style="color:var(--accent)">Generate recommendations</a>'
        ' on the Discover page to highlight your personalised picks.',
    )
    businesses_df = _load_businesses()
    if businesses_df is None or businesses_df.empty:
        status_banner("warn", "No processed data found. Run the pipeline from the Admin page first.")
        st.stop()

    # Default center: centroid of all businesses
    lat = float(businesses_df["latitude"].median())
    lon = float(businesses_df["longitude"].median())
    display_df = businesses_df.sample(min(500, len(businesses_df)), random_state=0)
else:
    lat, lon = center
    display_df = None  # unused in rec mode

# ---------------------------------------------------------------------------
# Build the folium map
# ---------------------------------------------------------------------------
try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    status_banner(
        "err",
        "folium / streamlit-folium not installed. "
        "Run: `pip install folium streamlit-folium`",
    )
    if have_recs:
        st.dataframe(
            recs[[c for c in ["name", "stars", "distance_km", "score", "address"] if c in recs.columns]],
            use_container_width=True,
        )
    st.stop()


def _color_for(score: float) -> str:
    if score >= 0.75:
        return "#c8553d"
    if score >= 0.55:
        return "#FBBF24"
    if score >= 0.40:
        return "#4ADE80"
    return "#b7b1c6"


m = folium.Map(
    location=[lat, lon],
    zoom_start=12 if have_recs else 11,
    tiles="cartodbpositron",
    control_scale=True,
)

if have_recs:
    # Radius circle
    folium.Circle(
        location=[lat, lon],
        radius=radius_km * 1000.0,
        color="#c8553d",
        weight=2,
        fill=True,
        fill_opacity=0.05,
        tooltip=f"{radius_km:.1f} km radius",
    ).add_to(m)

    # User / driver marker
    folium.Marker(
        location=[lat, lon],
        icon=folium.Icon(color="red", icon="car", prefix="fa"),
        tooltip="You are here",
    ).add_to(m)

    # Recommendation pins
    for rank, (_, row) in enumerate(recs.iterrows(), 1):
        blat = row.get("latitude")
        blon = row.get("longitude")
        if pd.isna(blat) or pd.isna(blon):
            continue
        score = float(row.get("score", 0.0))
        color = _color_for(score)
        stars = row.get("stars", "—")
        cats = str(row.get("categories", "") or "")[:80]
        dist = row.get("distance_km")
        dist_str = f"{dist:.1f} km" if pd.notna(dist) else "—"
        popup_html = f"""
            <div style='font-family:"DM Sans",sans-serif;min-width:200px;color:#0d0d0d;'>
              <div style='font-weight:600;font-size:1.05rem;'>#{rank} · {row['name']}</div>
              <div style='color:#7a7a73;font-size:0.85rem;margin-top:3px;'>{cats}</div>
              <div style='margin-top:7px;font-size:0.9rem;color:#c8553d;font-weight:500;'>★ {stars}</div>
              <div style='color:#b7b1c6;font-size:0.8rem;margin-top:2px;'>{dist_str} · score {score:.2f}</div>
            </div>
        """
        folium.CircleMarker(
            location=[blat, blon],
            radius=10 + 8 * score,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"#{rank} {row['name']}",
        ).add_to(m)

    # Fit bounds
    if "latitude" in recs.columns and "longitude" in recs.columns:
        pts = recs[["latitude", "longitude"]].dropna().values.tolist()
        pts.append([lat, lon])
        if len(pts) > 1:
            try:
                m.fit_bounds(pts, padding=(20, 20))
            except Exception:
                pass

else:
    # Browse mode: plot a sample of all businesses
    for _, row in display_df.iterrows():
        blat = row.get("latitude")
        blon = row.get("longitude")
        if pd.isna(blat) or pd.isna(blon):
            continue
        stars = row.get("stars", "—")
        cats = str(row.get("categories", "") or "")[:60]
        popup_html = f"""
            <div style='font-family:"DM Sans",sans-serif;min-width:180px;color:#0d0d0d;'>
              <div style='font-weight:600;'>{row['name']}</div>
              <div style='color:#7a7a73;font-size:0.82rem;'>{cats}</div>
              <div style='color:#c8553d;margin-top:5px;'>★ {stars}</div>
            </div>
        """
        folium.CircleMarker(
            location=[blat, blon],
            radius=6,
            color="#8e8aa6",
            weight=1,
            fill=True,
            fill_color="#8e8aa6",
            fill_opacity=0.55,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=str(row["name"]),
        ).add_to(m)

st_folium(m, width=None, height=620, returned_objects=[])

# Legend (only shown in recommendation mode)
if have_recs:
    st.markdown(
        """
        <div style='display:flex;gap:1.2rem;margin-top:0.9rem;flex-wrap:wrap;
                    font-family:"DM Sans",sans-serif;font-size:0.88rem;
                    color:#7a7a73;letter-spacing:0.01em;'>
          <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#c8553d;margin-right:5px;vertical-align:middle;'></span>Top pick (≥ 0.75)</span>
          <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#FBBF24;margin-right:5px;vertical-align:middle;'></span>Strong (0.55–0.75)</span>
          <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#4ADE80;margin-right:5px;vertical-align:middle;'></span>Solid (0.40–0.55)</span>
          <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#b7b1c6;margin-right:5px;vertical-align:middle;'></span>Other</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------------------------
    # Table below the map
    # ---------------------------------------------------------------------------
    st.markdown("### Ranked list")
    display_cols = [
        c for c in ["name", "stars", "distance_km", "score", "categories", "address"]
        if c in recs.columns
    ]
    st.dataframe(
        recs[display_cols].assign(
            distance_km=lambda d: d["distance_km"].round(2) if "distance_km" in d else None,
            score=lambda d: d["score"].round(3) if "score" in d else None,
        ),
        use_container_width=True,
    )

render_dock("map", user_id=st.session_state.get("selected_user_id"))
