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


st.set_page_config(page_title="Map View", page_icon="·", layout="wide", initial_sidebar_state="collapsed")
inject_css()
render_topnav("map")
page_header("Map View", "Where the recommendations actually are.")


recs: pd.DataFrame | None = st.session_state.get("last_recs")
center = st.session_state.get("last_center")
radius_km = st.session_state.get("last_radius_km", 5.0)

if recs is None or recs.empty or center is None:
    status_banner(
        "warn",
        "No recommendations yet. Generate some on the Discover page first.",
    )
    st.stop()

lat, lon = center

# ---------------------------------------------------------------------------
# Build the folium map
# ---------------------------------------------------------------------------
try:
    import folium
    from folium import plugins
    from streamlit_folium import st_folium
except ImportError:
    status_banner(
        "err",
        "folium / streamlit-folium not installed. "
        "Install them with `pip install folium streamlit-folium` "
        "or use the environment.yml conda env.",
    )
    st.dataframe(
        recs[[c for c in ["name", "stars", "distance_km", "score", "address"] if c in recs.columns]],
        use_container_width=True,
    )
    st.stop()

# Score-to-color mapping
def _color_for(score: float) -> str:
    if score >= 0.75:
        return "#c8553d"  # brand accent terracotta
    if score >= 0.55:
        return "#FBBF24"  # warm amber
    if score >= 0.40:
        return "#4ADE80"  # green
    return "#b7b1c6"      # muted


m = folium.Map(
    location=[lat, lon],
    zoom_start=13,
    tiles="cartodbpositron",
    control_scale=True,
)

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

# User marker
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
        <div style='font-family:"Cormorant Garamond",Georgia,serif;min-width:200px;color:#0f1f3d;'>
          <div style='font-weight:600;font-size:1.1rem;'>#{rank} · {row['name']}</div>
          <div style='color:#8e8aa6;font-size:0.88rem;margin-top:3px;'>{cats}</div>
          <div style='margin-top:7px;font-size:0.92rem;color:#c8553d;font-weight:500;'>★ {stars}</div>
          <div style='color:#b7b1c6;font-size:0.82rem;margin-top:2px;'>{dist_str} · score {score:.2f}</div>
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

# Fit bounds to include all pins
if "latitude" in recs.columns and "longitude" in recs.columns:
    pts = recs[["latitude", "longitude"]].dropna().values.tolist()
    pts.append([lat, lon])
    if len(pts) > 1:
        try:
            m.fit_bounds(pts, padding=(20, 20))
        except Exception:
            pass

st_folium(m, width=None, height=620, returned_objects=[])

# Legend
st.markdown(
    """
    <div style='display:flex;gap:1.2rem;margin-top:0.9rem;flex-wrap:wrap;
                font-family:"Cormorant Garamond",Georgia,serif;font-size:0.88rem;
                color:#8e8aa6;letter-spacing:0.01em;'>
      <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#c8553d;margin-right:5px;vertical-align:middle;'></span>Top pick (≥ 0.75)</span>
      <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#FBBF24;margin-right:5px;vertical-align:middle;'></span>Strong (0.55–0.75)</span>
      <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#4ADE80;margin-right:5px;vertical-align:middle;'></span>Solid (0.40–0.55)</span>
      <span><span style='display:inline-block;width:13px;height:13px;border-radius:50%;background:#b7b1c6;margin-right:5px;vertical-align:middle;'></span>Other</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Table fallback below the map
# ---------------------------------------------------------------------------
st.markdown("### Ranked list")
display_cols = [
    c
    for c in ["name", "stars", "distance_km", "score", "categories", "address"]
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
