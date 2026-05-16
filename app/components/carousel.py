"""Auto-sliding photo carousel for the home page."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


def _star_str(rating: float | None) -> str:
    if rating is None:
        return ""
    full = int(rating)
    half = (rating - full) >= 0.5
    return "★" * full + ("½" if half else "") + f" {rating:.1f}"


def _load_city_photos(
    photo_map: dict[str, list[str]],
    photos_dir: Path,
    businesses: list[dict],   # each dict: business_id, name, stars, categories
    max_photos: int = 10,
) -> list[dict]:
    """Return up to max_photos slides, each with photo_b64 + restaurant metadata."""
    result: list[dict] = []
    if not photos_dir.is_dir() or not photo_map:
        return result
    for biz in businesses:
        if len(result) >= max_photos:
            break
        bid = biz.get("business_id", "")
        for pid in photo_map.get(bid, [])[:3]:
            path = photos_dir / f"{pid}.jpg"
            if path.exists():
                result.append({
                    "photo_b64": base64.b64encode(path.read_bytes()).decode(),
                    "name": biz.get("name", ""),
                    "stars": _star_str(biz.get("stars")),
                    "cats": (biz.get("categories") or "")[:60],
                })
                break
    return result


def render_carousel(
    slides: list[dict],
    city_name: str,
    height: int = 400,
) -> None:
    """Render an auto-advancing photo carousel with per-slide restaurant labels.

    Each entry in `slides` must have keys: photo_b64, name, stars, cats.
    Falls back to a branded gradient when slides is empty.
    """
    if not slides:
        st.markdown(
            f"""
            <div style="
                width:100%;height:{height}px;border-radius:18px;
                background:linear-gradient(135deg,#1C2438 0%,#3a2010 60%,#C4563A 100%);
                display:flex;align-items:center;justify-content:center;
                color:#EDE4D9;font-family:'Cormorant Garamond',Georgia,serif;
                text-align:center;letter-spacing:0.04em;
                box-shadow:0 8px 40px rgba(28,36,56,0.22);
            ">
              <div>
                <div style="font-size:2.8rem;font-weight:600;">{city_name}</div>
                <div style="font-size:1rem;opacity:0.65;margin-top:0.6rem;font-style:italic;">
                  Add the Yelp photos dataset to see restaurant photos here.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    slides_html = "\n".join(
        f'<div class="slide">'
        f'<img src="data:image/jpeg;base64,{s["photo_b64"]}" alt="{s["name"]}" />'
        f'</div>'
        for s in slides
    )
    dots_html = "\n".join(
        f'<div class="dot{" active" if i == 0 else ""}" data-idx="{i}"></div>'
        for i in range(len(slides))
    )

    # JS-safe metadata array (name/stars/cats per slide)
    slide_data_js = json.dumps([
        {"name": s["name"], "stars": s["stars"], "cats": s["cats"]}
        for s in slides
    ])
    n = len(slides)
    first = slides[0]

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:transparent;overflow:hidden;}}

.carousel{{
  width:100%;height:{height}px;border-radius:18px;
  overflow:hidden;position:relative;background:#1C2438;
  box-shadow:0 8px 40px rgba(28,36,56,0.28);
  user-select:none;
}}

.track{{
  display:flex;height:100%;
  transition:transform 0.78s cubic-bezier(0.4,0,0.2,1);
  will-change:transform;
}}

.slide{{min-width:100%;height:100%;flex-shrink:0;position:relative;}}
.slide img{{width:100%;height:100%;object-fit:cover;object-position:center;display:block;}}

.overlay{{
  position:absolute;inset:0;
  background:linear-gradient(
    to top,
    rgba(28,36,56,0.92) 0%,
    rgba(28,36,56,0.22) 48%,
    transparent 100%
  );
  pointer-events:none;
}}

/* City badge — top left */
.city-badge{{
  position:absolute;top:1.2rem;left:1.4rem;
  background:rgba(28,36,56,0.55);
  backdrop-filter:blur(6px);
  -webkit-backdrop-filter:blur(6px);
  border:1px solid rgba(237,228,217,0.18);
  border-radius:999px;
  padding:0.28rem 0.85rem;
  color:#EDE4D9;
  font-family:'Cormorant Garamond',Georgia,serif;
  font-size:0.82rem;
  font-weight:600;
  letter-spacing:0.1em;
  text-transform:uppercase;
  pointer-events:none;
}}

/* Restaurant info — bottom left */
.label{{
  position:absolute;bottom:2.4rem;left:2rem;right:7rem;
  color:#EDE4D9;
  font-family:'Cormorant Garamond',Georgia,serif;
  text-shadow:0 2px 14px rgba(0,0,0,0.6);
  pointer-events:none;
  transition:opacity 0.3s;
}}
.label-stars{{
  font-size:0.88rem;color:#FBBF24;letter-spacing:0.04em;margin-bottom:0.25rem;
}}
.label-name{{
  font-size:1.9rem;font-weight:600;line-height:1.15;letter-spacing:0.01em;
}}
.label-cats{{
  font-size:0.85rem;opacity:0.65;margin-top:0.3rem;font-style:italic;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}}

/* Dots */
.dots{{
  position:absolute;bottom:1.3rem;right:1.4rem;
  display:flex;gap:8px;align-items:center;
}}
.dot{{
  width:8px;height:8px;border-radius:50%;
  background:rgba(237,228,217,0.3);
  cursor:pointer;
  transition:background 0.3s,transform 0.3s,width 0.3s,border-radius 0.3s;
  flex-shrink:0;
}}
.dot.active{{
  background:#C4563A;transform:scale(1.2);width:22px;border-radius:4px;
}}

/* Progress bar */
.progress-bar{{position:absolute;bottom:0;left:0;right:0;height:3px;background:rgba(237,228,217,0.1);}}
.progress-fill{{height:100%;background:#C4563A;width:0%;transition:width linear;}}
</style>
</head>
<body>
<div class="carousel">
  <div class="track" id="track">
    {slides_html}
  </div>
  <div class="overlay"></div>

  <div class="city-badge">{city_name}</div>

  <div class="label" id="label">
    <div class="label-stars" id="lbl-stars">{first["stars"]}</div>
    <div class="label-name"  id="lbl-name">{first["name"]}</div>
    <div class="label-cats"  id="lbl-cats">{first["cats"]}</div>
  </div>

  <div class="dots" id="dots">
    {dots_html}
  </div>
  <div class="progress-bar"><div class="progress-fill" id="pbar"></div></div>
</div>

<script>
(function(){{
  const INTERVAL = 4500;
  const track = document.getElementById('track');
  const dots  = document.querySelectorAll('.dot');
  const pbar  = document.getElementById('pbar');
  const lblName  = document.getElementById('lbl-name');
  const lblStars = document.getElementById('lbl-stars');
  const lblCats  = document.getElementById('lbl-cats');
  const label    = document.getElementById('label');
  const data  = {slide_data_js};
  const total = {n};
  let cur = 0, timer = null;

  function updateLabel(idx) {{
    label.style.opacity = '0';
    setTimeout(() => {{
      lblName.textContent  = data[idx].name;
      lblStars.textContent = data[idx].stars;
      lblCats.textContent  = data[idx].cats;
      label.style.opacity  = '1';
    }}, 220);
  }}

  function resetProgress() {{
    pbar.style.transition = 'none';
    pbar.style.width = '0%';
    requestAnimationFrame(() => requestAnimationFrame(() => {{
      pbar.style.transition = 'width ' + INTERVAL + 'ms linear';
      pbar.style.width = '100%';
    }}));
  }}

  function goTo(n) {{
    cur = (n + total) % total;
    track.style.transform = 'translateX(-' + (cur * 100) + '%)';
    dots.forEach((d, i) => d.classList.toggle('active', i === cur));
    updateLabel(cur);
    resetProgress();
  }}

  dots.forEach(d => d.addEventListener('click', () => {{
    clearInterval(timer);
    goTo(parseInt(d.dataset.idx));
    timer = setInterval(() => goTo(cur + 1), INTERVAL);
  }}));

  // start
  label.style.transition = 'opacity 0.3s';
  goTo(0);
  timer = setInterval(() => goTo(cur + 1), INTERVAL);
}})();
</script>
</body>
</html>"""

    components.html(html, height=height + 4, scrolling=False)
