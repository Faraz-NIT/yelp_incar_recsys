"""Auto-sliding photo carousel for the home page."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

try:
    from PIL import Image, ImageFilter

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# City-specific hero copy
# ---------------------------------------------------------------------------
_CITY_COPY: dict[str, tuple[str, str, list[str]]] = {
    # city: (title_em, subtitle, [pill1, pill2])
    "Philadelphia": (
        "eat in <em>Philly</em>.",
        "Cheesesteaks, rowhome charm, and a dining scene that punches above its weight — your next table is closer than you think.",
        ["Cheesesteaks &amp; more", "Over 2 000 restaurants"],
    ),
    "Tampa": (
        "dine in <em>Tampa</em>.",
        "Waterfront seafood, Cuban sandwiches, and a Bay-side food scene with something for every palate on the road.",
        ["Gulf Coast cuisine", "Cuban &amp; fusion"],
    ),
    "New Orleans": (
        "taste <em>New Orleans</em>.",
        "Cre\u00f4le heat, jazz-fuelled brasseries, and a culinary soul like nowhere else — let the city feed you right.",
        ["Cre\u00f4le &amp; Cajun", "French Quarter eats"],
    ),
    "Tucson": (
        "eat in <em>Tucson</em>.",
        "Sonoran desert spice, farm-fresh flavours, and a UNESCO City of Gastronomy waiting at every turn.",
        ["Sonoran cuisine", "Farm-to-table"],
    ),
    "Indianapolis": (
        "dine in <em>Indy</em>.",
        "Midwestern hospitality meets a fast-evolving food scene — from craft breweries to James Beard-worthy kitchens.",
        ["Craft &amp; local", "Race-day dining"],
    ),
    "Nashville": (
        "eat in <em>Nashville</em>.",
        "Hot chicken, honky-tonk energy, and a restaurant boom that has turned Music City into a true food destination.",
        ["Hot chicken", "Southern &amp; beyond"],
    ),
    "Reno": (
        "discover <em>Reno</em>.",
        "Beyond the casino floor lies a thriving independent dining scene framed by Sierra Nevada peaks and Basque heritage.",
        ["Basque tradition", "Indie dining"],
    ),
    "Saint Louis": (
        "eat in <em>St. Louis</em>.",
        "Toasted ravioli, slow-smoked ribs, and a food culture as iconic as the Arch itself — discover it from the driver seat.",
        ["BBQ &amp; Italian", "Gateway City eats"],
    ),
    "Santa Barbara": (
        "dine in <em>Santa Barbara</em>.",
        "Sun-drenched wine country, fresh Pacific seafood, and farm-to-fork dining set against the California Riviera.",
        ["Wine country cuisine", "Pacific seafood"],
    ),
    "Boise": (
        "eat in <em>Boise</em>.",
        "Treasure Valley produce, a booming craft scene, and restaurants that turn locally-sourced into something extraordinary.",
        ["Locally sourced", "Craft &amp; artisan"],
    ),
    "Edmonton": (
        "dine in <em>Edmonton</em>.",
        "A festival-city appetite — from Ukrainian perogies to world-class sushi — Canada\u2019s most underrated food destination.",
        ["World cuisines", "Festival city flavours"],
    ),
}

_DEFAULT_COPY: tuple[str, str, list[str]] = (
    "eat <em>next</em>.",
    "A personalised restaurant concierge for the road — surfacing the right table at the right moment, wherever the drive takes you.",
    ["Live recommendations", "Top-N &middot; personalised"],
)


def _star_str(rating: float | None) -> str:
    if rating is None:
        return ""
    full = int(rating)
    half = (rating - full) >= 0.5
    return "★" * full + ("½" if half else "") + f" {rating:.1f}"


def _load_city_photos(
    photo_map: dict[str, list[str]],
    photos_dir: Path,
    businesses: list[dict],  # each dict: business_id, name, stars, categories
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
                result.append(
                    {
                        "photo_b64": _encode_photo(path),
                        "name": biz.get("name", ""),
                        "stars": _star_str(biz.get("stars")),
                        "cats": (biz.get("categories") or "")[:60],
                    }
                )
                break
    return result


def _encode_photo(path: Path, target_height: int = 800) -> str:
    """Return a base64-encoded JPEG, upscaled with LANCZOS and sharpened."""
    if not _PIL_AVAILABLE:
        return base64.b64encode(path.read_bytes()).decode()
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if h < target_height:
        scale = target_height / h
        img = img.resize((int(w * scale), target_height), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=3))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def render_hero_carousel(
    slides: list[dict],
    city_name: str,
    height: int = 290,
) -> None:
    """Render the full hero card: text on the left, photo carousel on the right.

    All rendered inside a single components.html() iframe so the JS carousel
    and the hero text coexist without Streamlit layout constraints.
    Each entry in `slides` must have keys: photo_b64, name, stars, cats.
    """
    title_em, subtitle, pills = _CITY_COPY.get(city_name, _DEFAULT_COPY)
    eyebrow_city = city_name if city_name else "Recommendations"
    pill1, pill2 = pills[0], pills[1]

    if slides:
        slides_html = "\n".join(
            f'<div class="slide">'
            f'<img src="data:image/jpeg;base64,{s["photo_b64"]}" alt="{s["name"]}" />'
            f"</div>"
            for s in slides
        )
        dots_html = "\n".join(
            f'<div class="dot{" active" if i == 0 else ""}" data-idx="{i}"></div>'
            for i in range(len(slides))
        )
        slide_data_js = json.dumps(
            [
                {"name": s["name"], "stars": s["stars"], "cats": s["cats"]}
                for s in slides
            ]
        )
        n = len(slides)
        first = slides[0]

        right_html = f"""
        <div class="hero-right" id="hero-right">
          <div class="track" id="track">{slides_html}</div>
          <div class="photo-overlay">
            <div class="ov-city">{city_name}</div>
            <div class="ov-name" id="ov-name">{first["name"]}</div>
            <div class="ov-stars" id="ov-stars">{first["stars"]}</div>
          </div>
          <div class="dots" id="dots">{dots_html}</div>
          <div class="progress-bar"><div class="progress-fill" id="pbar"></div></div>
        </div>
        """

        script_html = f"""
        <script>
        (function(){{
          const INTERVAL = 4500;
          const track  = document.getElementById('track');
          const dots   = document.querySelectorAll('.dot');
          const pbar   = document.getElementById('pbar');
          const ovName = document.getElementById('ov-name');
          const ovStars = document.getElementById('ov-stars');
          const data   = {slide_data_js};
          const total  = {n};
          let cur = 0, timer = null;

          function updateInfo(idx) {{
            ovName.style.opacity = '0';
            setTimeout(() => {{
              ovName.textContent  = data[idx].name;
              ovStars.textContent = data[idx].stars;
              ovName.style.opacity = '1';
            }}, 200);
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
            updateInfo(cur);
            resetProgress();
          }}

          dots.forEach(d => d.addEventListener('click', () => {{
            clearInterval(timer);
            goTo(parseInt(d.dataset.idx));
            timer = setInterval(() => goTo(cur + 1), INTERVAL);
          }}));

          ovName.style.transition = 'opacity 0.3s';
          goTo(0);
          timer = setInterval(() => goTo(cur + 1), INTERVAL);
        }})();
        </script>
        """
    else:
        # Try to use the placeholder food image when no slides are available
        _placeholder = (
            Path(__file__).resolve().parents[1] / "static" / "placeholder.jpg"
        )
        if _placeholder.exists():
            with open(_placeholder, "rb") as _f:
                _ph_b64 = base64.b64encode(_f.read()).decode()
            if city_name:
                _overlay_html = (
                    f'<div class="ph-overlay">'
                    f'<div class="ph-city">{city_name}</div>'
                    f'<div class="ph-hint">Add the Yelp photos dataset to see restaurant photos.</div>'
                    f"</div>"
                )
            else:
                _overlay_html = (
                    '<div class="ph-overlay">'
                    '<div class="ph-city">Your next meal awaits</div>'
                    '<div class="ph-hint">Select a city in the sidebar to get started.</div>'
                    "</div>"
                )
            right_html = f"""
        <div class="hero-right" style="position:relative;padding:0;overflow:hidden;">
          <img src="data:image/jpeg;base64,{_ph_b64}"
               style="width:100%;height:100%;object-fit:cover;display:block;filter:brightness(0.72);" />
          {_overlay_html}
        </div>
        """
        else:
            city_label = city_name if city_name else "Select a city"
            hint = (
                "Add the Yelp photos dataset to see photos."
                if city_name
                else "Select a city in the sidebar."
            )
            right_html = f"""
        <div class="hero-right empty">
          <div class="empty-label">
            <div class="empty-city">{city_label}</div>
            <div class="empty-hint">{hint}</div>
          </div>
        </div>
        """
        script_html = ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:transparent;overflow:hidden;font-family:"Cormorant Garamond","Times New Roman",Georgia,serif;}}

/* ── Hero card (matches original .hero-card) ── */
.hero{{
  width:100%;height:{height}px;
  border-radius:16px;
  overflow:hidden;
  display:flex;flex-direction:row;
  background:#FFFFFF;
  box-shadow:0 4px 28px rgba(0,0,0,0.07),0 1px 4px rgba(0,0,0,0.04);
  user-select:none;
}}

/* ── LEFT panel (matches original .hero-left) ── */
.hero-left{{
  flex:0 0 62%;
  display:flex;flex-direction:column;justify-content:center;
  padding:3rem 2.5rem 2.5rem 3rem;
  background:#FFFFFF;
  position:relative;z-index:2;
}}

.eyebrow{{
  font-size:0.70rem;font-weight:600;
  letter-spacing:0.12em;text-transform:uppercase;
  color:#C4563A;margin-bottom:0.85rem;display:block;
}}

.title{{
  font-size:3.6rem;font-weight:600;
  color:#1C2438;line-height:1.1;
  margin:0 0 0.8rem 0;letter-spacing:0.01em;
}}
.title em{{color:#C4563A;font-style:italic;font-weight:600;}}

.subtitle{{
  font-size:1.1rem;font-weight:500;
  color:#6B7280;line-height:1.65;
  margin:0 0 1.8rem 0;max-width:400px;
}}

.pills{{display:flex;gap:0.5rem;flex-wrap:wrap;}}
.pill{{
  display:inline-flex;align-items:center;gap:0.35rem;
  padding:0.28rem 0.9rem;
  border:1px solid #E8E3DC;border-radius:999px;
  font-size:0.82rem;font-weight:500;
  color:#6B7280;background:#FFFFFF;letter-spacing:0.01em;
}}
.pill-dot{{color:#C4563A;font-size:0.55rem;line-height:1;}}

/* ── RIGHT panel (carousel, 38% width) ── */
.hero-right{{
  flex:0 0 38%;
  position:relative;overflow:hidden;
  border-radius:0 16px 16px 0;
}}

/* warm gradient placeholder when no photos */
.hero-right.empty{{
  background:linear-gradient(135deg,#f5f0eb 0%,#ede4d9 60%,#d4b5a0 100%);
  display:flex;align-items:center;justify-content:center;
}}
.empty-label{{text-align:center;color:#1C2438;}}
.empty-city{{font-size:1.5rem;font-weight:600;}}
.empty-hint{{font-size:0.75rem;opacity:0.5;margin-top:0.35rem;font-style:italic;}}

/* placeholder image overlay */
.ph-overlay{{
  position:absolute;bottom:0;left:0;right:0;
  padding:1.2rem 1.5rem 1.4rem;
  background:linear-gradient(to top,rgba(28,36,56,0.72) 0%,transparent 100%);
  color:#FFFFFF;
}}
.ph-city{{font-size:1.3rem;font-weight:600;letter-spacing:0.01em;line-height:1.2;}}
.ph-hint{{font-size:0.72rem;opacity:0.75;margin-top:0.3rem;font-style:italic;}}

/* sliding track */
.track{{
  display:flex;height:100%;
  transition:transform 0.78s cubic-bezier(0.4,0,0.2,1);
  will-change:transform;
}}
.slide{{min-width:100%;height:100%;flex-shrink:0;}}
.slide img{{width:100%;height:100%;object-fit:cover;object-position:center;display:block;}}

/* left-edge fade blending into white left panel */
.hero-right::before{{
  content:'';
  position:absolute;top:0;left:0;bottom:0;width:36px;
  background:linear-gradient(to right,rgba(255,255,255,0.55),transparent);
  pointer-events:none;z-index:2;
}}

/* bottom overlay: city + name + stars */
.photo-overlay{{
  position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(to top,rgba(28,36,56,0.85) 0%,transparent 100%);
  padding:0.5rem 0.8rem 0.45rem 0.8rem;
  pointer-events:none;z-index:3;
}}
.ov-city{{
  font-size:0.58rem;font-weight:700;letter-spacing:0.13em;
  text-transform:uppercase;color:#C4563A;
}}
.ov-name{{
  font-size:1.25rem;font-weight:600;color:#EDE4D9;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  transition:opacity 0.3s;
}}
.ov-stars{{font-size:0.95rem;color:#FBBF24;margin-top:0.1rem;}}

/* dots — top right of photo panel */
.dots{{
  position:absolute;top:0.55rem;right:0.7rem;
  display:flex;gap:5px;align-items:center;z-index:4;
}}
.dot{{
  width:6px;height:6px;border-radius:50%;
  background:rgba(237,228,217,0.30);cursor:pointer;
  transition:background 0.3s,width 0.3s,border-radius 0.3s;flex-shrink:0;
}}
.dot.active{{background:#C4563A;width:15px;border-radius:4px;}}

/* progress bar */
.progress-bar{{
  position:absolute;bottom:0;left:0;right:0;height:3px;
  background:rgba(237,228,217,0.08);z-index:5;
}}
.progress-fill{{height:100%;background:#C4563A;width:0%;transition:width linear;}}
</style>
</head>
<body>
<div class="hero">
  <div class="hero-left">
    <span class="eyebrow">In-Car &middot; {eyebrow_city}</span>
    <h1 class="title">Where to {title_em}</h1>
    <p class="subtitle">{subtitle}</p>
    <div class="pills">
      <span class="pill"><span class="pill-dot">&#9679;</span>{pill1}</span>
      <span class="pill">{pill2}</span>
    </div>
  </div>
  {right_html}
</div>
{script_html}
</body>
</html>"""

    components.html(html, height=height + 4, scrolling=False)


def render_carousel(
    slides: list[dict],
    city_name: str,
    height: int = 260,
) -> None:
    """Render a split carousel: text info on the left, photo on the right.

    Each entry in `slides` must have keys: photo_b64, name, stars, cats.
    Falls back to a branded gradient when slides is empty.
    """
    if not slides:
        st.markdown(
            f"""
            <div style="
                width:100%;height:{height}px;border-radius:14px;
                background:linear-gradient(135deg,#1C2438 0%,#3a2010 60%,#C4563A 100%);
                display:flex;align-items:center;justify-content:center;
                color:#EDE4D9;font-family:'Cormorant Garamond',Georgia,serif;
                text-align:center;letter-spacing:0.04em;
                box-shadow:0 6px 28px rgba(28,36,56,0.22);
            ">
              <div>
                <div style="font-size:2rem;font-weight:600;">{city_name}</div>
                <div style="font-size:0.85rem;opacity:0.65;margin-top:0.5rem;font-style:italic;">
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
        f"</div>"
        for s in slides
    )
    dots_html = "\n".join(
        f'<div class="dot{" active" if i == 0 else ""}" data-idx="{i}"></div>'
        for i in range(len(slides))
    )

    # JS-safe metadata array (name/stars/cats per slide)
    slide_data_js = json.dumps(
        [{"name": s["name"], "stars": s["stars"], "cats": s["cats"]} for s in slides]
    )
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
  width:100%;height:{height}px;border-radius:14px;
  overflow:hidden;position:relative;
  display:flex;flex-direction:row;
  background:#1C2438;
  box-shadow:0 6px 28px rgba(28,36,56,0.30);
  user-select:none;
}}

/* ── LEFT PANEL (text) ── */
.left-panel{{
  width:46%;flex-shrink:0;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:1rem 1.2rem 0.7rem 1.2rem;
  background:#1C2438;
  position:relative;
  z-index:2;
}}

.city-badge{{
  display:inline-block;
  background:rgba(196,86,58,0.15);
  border:1px solid rgba(196,86,58,0.38);
  border-radius:999px;
  padding:0.18rem 0.65rem;
  color:#C4563A;
  font-family:'Cormorant Garamond',Georgia,serif;
  font-size:0.72rem;
  font-weight:700;
  letter-spacing:0.1em;
  text-transform:uppercase;
  align-self:flex-start;
}}

.label{{
  flex:1;
  display:flex;flex-direction:column;justify-content:center;
  color:#EDE4D9;
  font-family:'Cormorant Garamond',Georgia,serif;
  padding:0.4rem 0;
  transition:opacity 0.3s;
}}
.label-stars{{
  font-size:0.8rem;color:#FBBF24;letter-spacing:0.04em;margin-bottom:0.18rem;
}}
.label-name{{
  font-size:1.35rem;font-weight:600;line-height:1.15;letter-spacing:0.01em;
}}
.label-cats{{
  font-size:0.75rem;opacity:0.55;margin-top:0.22rem;font-style:italic;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}}

.bottom-row{{
  display:flex;align-items:center;
}}
.dots{{
  display:flex;gap:6px;align-items:center;
}}
.dot{{
  width:7px;height:7px;border-radius:50%;
  background:rgba(237,228,217,0.25);
  cursor:pointer;
  transition:background 0.3s,transform 0.3s,width 0.3s,border-radius 0.3s;
  flex-shrink:0;
}}
.dot.active{{
  background:#C4563A;transform:scale(1.15);width:18px;border-radius:4px;
}}

/* ── RIGHT PANEL (photo only) ── */
.right-panel{{
  flex:1;
  position:relative;
  overflow:hidden;
  border-radius:0 14px 14px 0;
}}

.track{{
  display:flex;height:100%;
  transition:transform 0.78s cubic-bezier(0.4,0,0.2,1);
  will-change:transform;
}}
.slide{{min-width:100%;height:100%;flex-shrink:0;}}
.slide img{{width:100%;height:100%;object-fit:cover;object-position:center;display:block;}}

/* soft left-edge fade so photo blends into the text panel */
.right-panel::before{{
  content:'';
  position:absolute;top:0;left:0;bottom:0;width:36px;
  background:linear-gradient(to right,rgba(28,36,56,0.55),transparent);
  pointer-events:none;z-index:1;
}}

/* Progress bar — spans full carousel width */
.progress-bar{{
  position:absolute;bottom:0;left:0;right:0;height:3px;
  background:rgba(237,228,217,0.07);
  z-index:5;
}}
.progress-fill{{height:100%;background:#C4563A;width:0%;transition:width linear;}}
</style>
</head>
<body>
<div class="carousel">

  <!-- LEFT: info -->
  <div class="left-panel">
    <div class="city-badge">{city_name}</div>
    <div class="label" id="label">
      <div class="label-stars" id="lbl-stars">{first["stars"]}</div>
      <div class="label-name"  id="lbl-name">{first["name"]}</div>
      <div class="label-cats"  id="lbl-cats">{first["cats"]}</div>
    </div>
    <div class="bottom-row">
      <div class="dots" id="dots">{dots_html}</div>
    </div>
  </div>

  <!-- RIGHT: sliding photos -->
  <div class="right-panel">
    <div class="track" id="track">
      {slides_html}
    </div>
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

  label.style.transition = 'opacity 0.3s';
  goTo(0);
  timer = setInterval(() => goTo(cur + 1), INTERVAL);
}})();
</script>
</body>
</html>"""

    components.html(html, height=height + 4, scrolling=False)
