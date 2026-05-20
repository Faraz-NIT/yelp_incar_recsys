"""Process page: interactive diagram of how the recommendation pipeline works."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from app.components.styles import inject_css, render_dock, render_topnav  # noqa: E402

st.set_page_config(
    page_title="Process",
    page_icon="·",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
render_topnav("process")

_HTML_PATH = ROOT / "app" / "static" / "recommendations_flow.html"

html_content = _HTML_PATH.read_text(encoding="utf-8")

# Embed inside a scrollable iframe using a data URI so Streamlit doesn't
# strip the inline styles or block external font requests.
b64 = base64.b64encode(html_content.encode("utf-8")).decode()
src = f"data:text/html;base64,{b64}"

st.markdown(
    f"""
    <style>
      /* Remove Streamlit's default page padding so the diagram fills edge-to-edge */
      [data-testid="stAppViewContainer"] > section {{
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
      }}
      .process-frame {{
        width: 100%;
        border: none;
        display: block;
      }}
    </style>
    <iframe
      src="{src}"
      class="process-frame"
      height="3200"
      scrolling="yes"
      sandbox="allow-same-origin allow-scripts"
    ></iframe>
    """,
    unsafe_allow_html=True,
)

render_dock("process")
