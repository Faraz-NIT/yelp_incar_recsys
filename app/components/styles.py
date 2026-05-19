"""Custom CSS and theme injection — PITSTOP design system."""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_STATIC = Path(__file__).resolve().parents[1] / "static"


def _logo_src() -> str:
    p = _STATIC / "mcgill_logo.png"
    if not p.exists():
        return ""
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/png;base64,{data}"


GLOBAL_CSS = """
<style>
/* ---------- Fonts ---------- */
@import url('https://fonts.googleapis.com/css2?family=Abril+Fatface&family=Rubik:ital,wght@0,200;0,300;0,400;0,500;1,200;1,300&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ---------- Design tokens ---------- */
:root {
  --bg:          #ececea;
  --grid:        #dbdbd6;
  --card:        #ffffff;
  --ink:         #0d0d0d;
  --ink-2:       #3a3a37;
  --muted:       #7a7a73;
  --line:        rgba(13,13,13,.08);
  --line-strong: rgba(13,13,13,.14);
  --accent:      #ff7a1a;
  --accent-soft: rgba(255,122,26,.12);
  --green:       #1e8a55;
  --green-soft:  #dff0e6;
  --red:         #c9402e;
  --red-soft:    #f7dcd6;
  --amber:       #c98c2a;
  --amber-soft:  #f5e6c8;
  --blue:        #2a6fdb;
  --blue-soft:   #dde9fa;
  --serif:  'Instrument Serif', 'Cormorant Garamond', Georgia, serif;
  --sans:   'DM Sans', ui-sans-serif, system-ui, sans-serif;
  --mono:   'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;
  --radius:    18px;
  --radius-sm: 12px;
  /* backward-compat aliases */
  --bg-primary:    #ececea;
  --bg-secondary:  #e4e4e0;
  --bg-card:       #ffffff;
  --bg-card-hover: #fafaf8;
  --accent-mid:    #e06a0f;
  --text-primary:  #0d0d0d;
  --text-secondary:#3a3a37;
  --text-muted:    #7a7a73;
  --border:        rgba(13,13,13,.12);
  --shadow-sm:   0 1px 2px rgba(13,13,13,.04), 0 4px 12px rgba(13,13,13,.06);
  --shadow-card: 0 1px 2px rgba(13,13,13,.04), 0 12px 32px rgba(13,13,13,.06);
  --shadow-hover:0 1px 2px rgba(13,13,13,.04), 0 20px 40px rgba(13,13,13,.08);
}

/* ---------- Base ---------- */
html { font-size: 15px !important; }

html, body, [class*="css"], .stApp, .stMarkdown, .stText,
h1, h2, h3, h4, h5, h6, p, span, div, label, button, input, select, textarea {
  font-family: var(--sans) !important;
  font-weight: 400 !important;
}

/* ---------- App shell ---------- */
/* Grid lives on body (fixed to viewport). .stApp is transparent so opaque
   white cards naturally block the grid — no child patching needed. */
html, body {
  background:
    linear-gradient(var(--grid) 1px, transparent 1px) 0 0 / 28px 28px,
    linear-gradient(90deg, var(--grid) 1px, transparent 1px) 0 0 / 28px 28px,
    var(--bg) !important;
  background-attachment: fixed !important;
}

.stApp {
  background: transparent !important;
  color: var(--ink) !important;
  -webkit-font-smoothing: antialiased;
}

.block-container {
  padding-top: 1.5rem !important;
  padding-bottom: 110px !important;
}

/* ---------- Hide sidebar & header ---------- */
section[data-testid="stSidebar"]     { display: none !important; }
[data-testid="collapsedControl"]     { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

[data-testid="stHeader"] { display: none !important; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }

/* Room for the fixed topnav */
section[data-testid="stMain"] .block-container,
.block-container {
  padding-top: 120px !important;
}

/* ---------- Dock ---------- */
.ps-dock {
  position: fixed;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  width: calc(100% - 16px);
  max-width: 1800px;
  background: var(--card);
  border-radius: var(--radius);
  padding: 10px 14px;
  display: flex;
  align-items: stretch;
  gap: 10px;
  flex-wrap: wrap;
  box-shadow: 0 2px 4px rgba(0,0,0,.06), 0 8px 28px rgba(0,0,0,.09);
  border: 1px solid var(--line);
}
.ps-dg {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
}
.ps-dg + .ps-dg {
  padding-left: 10px;
  border-left: 1px solid var(--line);
}
.ps-dg-label {
  font-family: var(--mono) !important;
  font-size: 10px !important;
  letter-spacing: .22em;
  text-transform: uppercase;
  color: var(--muted);
  white-space: nowrap;
}
.ps-brand { display: flex; align-items: center; gap: 10px; }
.ps-brand-mark {
  width: 34px; height: 34px; border-radius: 9px;
  background: #0d0d0d; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--serif) !important;
  font-size: 20px; line-height: 1;
  position: relative; flex-shrink: 0;
}
.ps-brand-mark::after {
  content: "";
  position: absolute; right: -2px; bottom: -2px;
  width: 9px; height: 9px; border-radius: 50%;
  background: var(--accent); border: 2px solid var(--card);
}
.ps-brand b {
  font-family: var(--serif) !important;
  font-size: 20px !important; font-weight: 400 !important;
  color: var(--ink); letter-spacing: .005em;
}
.ps-brand small {
  display: block;
  font-family: var(--mono) !important;
  font-size: 9.5px !important; letter-spacing: .22em;
  text-transform: uppercase; color: var(--muted); margin-top: 2px;
}
.ps-tabs {
  display: flex; align-items: center; gap: 2px;
  background: rgba(0,0,0,.04);
  border-radius: 10px; padding: 3px;
}
.ps-tab {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--serif) !important;
  font-size: 15px !important; letter-spacing: .003em;
  color: var(--ink-2); text-decoration: none !important;
  padding: 6px 10px; border-radius: 8px;
  white-space: nowrap;
  transition: background .12s, color .12s;
}
.ps-tab svg { width: 13px; height: 13px; color: var(--muted); flex-shrink: 0; }
.ps-tab:hover { color: var(--ink); background: rgba(255,255,255,.6); }
.ps-tab.active {
  background: #fff; color: var(--ink);
  box-shadow: 0 1px 0 rgba(0,0,0,.05), 0 2px 8px rgba(0,0,0,.05);
}
.ps-tab.active svg { color: var(--accent); }

.ps-pill {
  display: inline-flex; align-items: center; gap: 7px;
  font-family: var(--sans) !important; font-size: 13px !important;
  color: var(--ink-2); background: rgba(0,0,0,.04);
  padding: 6px 10px; border-radius: 99px;
  text-decoration: none !important;
  transition: background .12s, color .12s;
}
.ps-pill:hover { background: rgba(0,0,0,.08); color: var(--ink); }
.ps-pill .pic {
  width: 18px; height: 18px; border-radius: 5px;
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,.06); color: var(--ink-2); flex-shrink: 0;
}
.ps-pill .pic svg { width: 11px; height: 11px; }
.ps-pill .pic.acc { background: var(--accent); color: #fff; }

.ps-info {
  display: grid; gap: 3px 10px;
  grid-template-columns: auto auto auto;
  align-items: center; padding: 2px 4px;
}
.ps-info .pip { width: 6px; height: 6px; border-radius: 50%; background: var(--green); }
.ps-info .pip.am { background: var(--accent); }
.ps-info .k {
  font-family: var(--mono) !important;
  font-size: 10.5px !important; letter-spacing: .16em;
  text-transform: uppercase; color: var(--muted);
}
.ps-info .v {
  font-family: var(--serif) !important;
  font-style: italic; font-size: 15px !important; color: var(--ink);
  white-space: nowrap;
}
.ps-user {
  display: flex; align-items: center; gap: 10px;
  padding: 5px 12px 5px 5px; border-radius: 99px;
  background: rgba(0,0,0,.04); cursor: pointer; margin-left: auto;
  flex-shrink: 0;
}
.ps-user .av {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--accent); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--sans) !important;
  font-weight: 500 !important; font-size: 12px; letter-spacing: .04em;
  flex-shrink: 0;
}
.ps-user .stk { display: flex; flex-direction: column; line-height: 1.2; }
.ps-user .stk b {
  font-family: var(--serif) !important; font-size: 16px !important;
  font-weight: 400 !important; color: var(--ink);
}
.ps-user .stk small {
  font-family: var(--mono) !important; font-size: 10px !important;
  letter-spacing: .18em; text-transform: uppercase; color: var(--muted); margin-top: 1px;
}
.ps-user .chev { color: var(--muted); font-size: 18px; margin-left: 2px; }

/* ---------- Typography ---------- */
h1, h2, h3, h4, h5, h6 {
  color: var(--ink) !important;
  font-weight: 400 !important;
  font-family: var(--serif) !important;
  letter-spacing: -.005em;
}

.dashboard-title {
  font-size: 3.2rem;
  font-weight: 400 !important;
  font-family: var(--serif) !important;
  color: var(--ink) !important;
  margin: 0; letter-spacing: -.01em;
  line-height: .96;
}
.dashboard-title i { color: var(--ink-2); font-style: italic; }

.dashboard-subtitle {
  color: var(--muted);
  font-size: 14.5px;
  font-weight: 400 !important;
  margin: 0.5rem 0 1.5rem 0;
  font-family: var(--sans) !important;
}

/* ---------- Section header ---------- */
.section-header {
  display: flex; align-items: baseline;
  justify-content: space-between;
  margin-bottom: 1.2rem; margin-top: 0.5rem;
}
.section-title {
  font-size: 2rem; font-weight: 400 !important;
  font-family: var(--serif) !important;
  color: var(--ink); letter-spacing: -.005em;
}
.section-label {
  font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 500 !important;
  letter-spacing: .18em; text-transform: uppercase; color: var(--muted);
}

/* ---------- Nav Cards ---------- */
a.nav-card { display: block; text-decoration: none; color: inherit; }
.nav-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.7rem 1.5rem 2rem 1.5rem;
  min-height: 170px; box-shadow: var(--shadow-card);
  transition: box-shadow .22s ease, transform .22s ease, border-color .22s ease;
  position: relative; overflow: hidden;
}
.nav-card:hover {
  box-shadow: var(--shadow-hover);
  border-color: rgba(255,122,26,.35);
  transform: translateY(-4px);
}
.nav-card-icon { margin-bottom: .8rem; display: block; line-height: 1; }
.nav-card-icon svg { width: 36px; height: 36px; display: block; }
.nav-card-title {
  font-family: var(--serif) !important;
  font-size: 1.4rem; font-weight: 400 !important;
  color: var(--ink); margin-bottom: .45rem; letter-spacing: -.003em;
}
.nav-card-desc {
  font-size: .93rem; font-weight: 400 !important;
  color: var(--muted); line-height: 1.6;
  padding-right: 1.8rem; padding-bottom: 1.2rem;
}
.nav-card-arrow {
  position: absolute; bottom: 1rem; right: 1.2rem;
  color: var(--muted); font-size: .9rem;
  transition: color .2s ease, right .2s ease;
}
.nav-card:hover .nav-card-arrow { color: var(--accent); right: 1rem; }

/* ---------- Hero Card ---------- */
.hero-card {
  background: var(--card); border-radius: var(--radius);
  margin-bottom: 2rem;
  box-shadow: var(--shadow-card);
  display: flex; overflow: hidden; min-height: 260px;
}
.hero-left {
  flex: 0 0 42%; padding: 2.5rem 2rem 2rem 2.5rem;
  display: flex; flex-direction: column; justify-content: center;
}
.hero-right {
  flex: 1 1 58%; background: var(--card);
  border-radius: 0 var(--radius) var(--radius) 0;
  overflow: hidden; position: relative; min-height: 260px;
}
.hero-right svg { width: 100%; height: 100%; display: block; }
.hero-img {
  position: absolute; inset: .75rem;
  width: calc(100% - 1.5rem); height: calc(100% - 1.5rem);
  object-fit: cover; object-position: center center;
  border-radius: 12px;
}
.hero-eyebrow {
  font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 500 !important;
  letter-spacing: .2em; text-transform: uppercase;
  color: var(--accent); margin-bottom: .85rem; display: block;
}
.hero-title {
  font-family: var(--serif) !important;
  font-size: 3rem; font-weight: 400 !important;
  color: var(--ink) !important; line-height: 1.05;
  margin: 0 0 .8rem 0; letter-spacing: -.01em;
}
.hero-accent { color: var(--accent) !important; font-style: italic; }
.hero-subtitle {
  font-size: 1rem; font-weight: 400 !important;
  color: var(--muted); line-height: 1.65;
  margin: 0 0 1.8rem 0; max-width: 400px;
}
.hero-pills { display: flex; gap: .5rem; flex-wrap: wrap; }
.hero-pill {
  display: inline-flex; align-items: center; gap: .35rem;
  padding: .28rem .9rem; border: 1px solid var(--line);
  border-radius: 999px; font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 500 !important;
  color: var(--muted); background: white; letter-spacing: .08em;
}
.hero-pill-dot { color: var(--accent); font-size: .55rem; line-height: 1; }

/* ---------- Page header ---------- */
.page-header-wrap {
  display: flex; align-items: flex-start; gap: 1.2rem; margin-bottom: 2rem;
}
.page-header-badge {
  width: 52px; height: 52px; background: var(--card);
  border: 1px solid var(--line); border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: var(--shadow-sm); flex-shrink: 0; margin-top: 6px;
}
.page-header-badge img { width: 26px; height: 26px; display: block; }
.page-header-title {
  font-family: var(--serif) !important;
  font-size: 2.8rem; font-weight: 400 !important;
  color: var(--ink) !important; line-height: 1.05;
  margin: 0; letter-spacing: -.01em;
}
.page-header-subtitle {
  font-size: .93rem; color: var(--muted); font-style: italic;
  margin: .3rem 0 0 0; font-weight: 400 !important;
}

/* ---------- Rec Cards ---------- */
.rec-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 0;
  margin-bottom: .9rem; box-shadow: var(--shadow-card);
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
  position: relative; overflow: hidden;
  display: flex; flex-direction: row; align-items: stretch;
}
.rec-card-body {
  flex: 1 1 auto; min-width: 0;
  padding: 1.1rem 1.3rem; position: relative;
}
.rec-card-photo {
  flex: 0 0 200px; width: 200px; overflow: hidden;
  border-radius: 0 var(--radius) var(--radius) 0;
}
.rec-card-photo img {
  width: 100%; height: 100%; object-fit: cover;
  object-position: center; display: block;
}
.rec-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--accent);
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}
.rec-card::before {
  content: ""; position: absolute;
  left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--accent);
}
.rec-card-rank {
  position: absolute; top: .8rem; right: 1rem;
  font-family: var(--serif) !important;
  font-size: 2rem; font-weight: 400 !important;
  color: var(--accent); opacity: .15; line-height: 1;
}
.rec-card-name {
  font-family: var(--serif) !important;
  font-size: 1.35rem; font-weight: 400 !important;
  color: var(--ink); margin: 0 3rem .25rem 0; letter-spacing: -.003em;
}
.rec-card-meta {
  color: var(--muted); font-size: .85rem;
  font-weight: 400 !important; margin-bottom: .5rem;
}
.rec-card-why {
  color: var(--muted); font-size: .9rem;
  font-weight: 400 !important; font-style: italic;
  line-height: 1.6; margin-top: .5rem;
  padding: .6rem .9rem;
  background: var(--accent-soft);
  border-left: 2px solid var(--accent);
  border-radius: 0 6px 6px 0;
}

/* ---------- Tags ---------- */
.tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 500 !important;
  letter-spacing: .14em; text-transform: uppercase;
  padding: 4px 9px; border-radius: 999px;
  background: rgba(0,0,0,.05); color: var(--ink-2);
}
.tag .pulse {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor; animation: pulse 1.8s infinite;
}
@keyframes pulse { 0%,100%{opacity:.5} 50%{opacity:1} }
.tag-accent { background: var(--accent-soft); color: #a04a08; }
.tag-success { background: var(--green-soft); color: var(--green); }
.tag-warning { background: var(--amber-soft); color: var(--amber); }
.tag-error   { background: var(--red-soft);   color: var(--red); }
.tag-info    { background: var(--blue-soft);   color: var(--blue); }

/* ---------- Metric pills ---------- */
.metric-pill {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 1rem;
  text-align: center; box-shadow: var(--shadow-sm);
}
.metric-pill .label {
  color: var(--muted); font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 500 !important;
  text-transform: uppercase; letter-spacing: .14em;
}
.metric-pill .value {
  color: var(--accent); font-family: var(--serif) !important;
  font-size: 1.6rem; font-weight: 400 !important; margin-top: .2rem;
}

/* ---------- Status banner ---------- */
.status-banner {
  padding: .7rem 1.1rem; border-radius: var(--radius-sm);
  margin-bottom: 1rem; border: 1px solid var(--line);
  border-left: 3px solid var(--line);
  background: var(--card); font-size: .9rem; color: var(--ink);
  box-shadow: var(--shadow-sm);
}
.status-banner.ok   { border-left-color: var(--green); background: var(--green-soft); }
.status-banner.warn { border-left-color: var(--amber); background: var(--amber-soft); }
.status-banner.err  { border-left-color: var(--red);   background: var(--red-soft); }
.status-banner.info { border-left-color: var(--blue);  background: var(--blue-soft); }

/* ---------- Buttons ---------- */
.stButton > button,
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button,
[data-testid="stForm"] .stButton > button {
  background: var(--accent) !important;
  color: #0a0a0a !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 500 !important;
  font-family: var(--sans) !important;
  font-size: .93rem !important;
  letter-spacing: .01em !important;
  padding: .5rem 1.4rem !important;
  transition: all .18s ease;
}
.stButton > button:hover,
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button:hover {
  background: var(--accent-mid) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 18px rgba(255,122,26,.3);
}

/* ---------- Inputs ---------- */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stMultiSelect > div > div {
  background: var(--card) !important;
  border: 1px solid var(--line-strong) !important;
  color: var(--ink) !important;
  font-family: var(--sans) !important;
  font-weight: 400 !important;
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {
  background: transparent; border-radius: 0; padding: 0; gap: 0;
  border: none; border-bottom: 1.5px solid var(--line);
}
.stTabs [data-baseweb="tab"] {
  background: transparent; color: var(--muted); border-radius: 0;
  padding: .5rem 1.2rem; font-weight: 500 !important;
  font-size: .9rem; letter-spacing: .01em;
  border-bottom: 2.5px solid transparent;
  margin-bottom: -1.5px; transition: color .18s;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--accent) !important; background: transparent !important; }
.stTabs [aria-selected="true"] {
  background: transparent !important;
  color: var(--accent) !important;
  border-bottom: 2.5px solid var(--accent) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

/* ---------- Metrics ---------- */
[data-testid="stMetric"] {
  background: var(--card) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius-sm) !important;
  padding: 1rem 1.2rem !important;
  box-shadow: var(--shadow-sm) !important;
}
[data-testid="stMetricLabel"] > div,
[data-testid="stMetricLabel"] p {
  font-family: var(--mono) !important;
  font-size: 10.5px !important; font-weight: 500 !important;
  text-transform: uppercase !important; letter-spacing: .14em !important;
  color: var(--muted) !important;
}
[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] p {
  font-family: var(--serif) !important;
  font-size: 1.5rem !important; font-weight: 400 !important;
  color: var(--ink) !important;
}
[data-testid="stMetricDelta"] { font-family: var(--mono) !important; font-size: .78rem !important; }

/* ---------- Progress bar ---------- */
.stProgress > div > div > div > div {
  background-color: var(--accent) !important; border-radius: 999px !important;
}
.stProgress > div > div > div {
  background-color: rgba(0,0,0,.06) !important; border-radius: 999px !important;
}

/* ---------- Checkbox / Radio ---------- */
.stCheckbox label p, .stRadio label p {
  color: var(--ink) !important; font-family: var(--sans) !important;
}

/* ---------- Caption ---------- */
.stMarkdown p small,
[data-testid="stCaptionContainer"] p {
  color: var(--muted) !important; font-size: .82rem !important;
}

/* ---------- Expander ---------- */
details summary p {
  font-weight: 500 !important; color: var(--ink) !important;
}

/* ---------- Dataframe ---------- */
[data-testid="stDataFrame"] th {
  background: rgba(0,0,0,.03) !important;
  color: var(--muted) !important; font-family: var(--mono) !important;
  font-size: 10.5px !important; text-transform: uppercase !important;
  letter-spacing: .1em !important;
}

/* ---------- Alerts ---------- */
[data-testid="stAlert"] {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--line) !important;
}

/* ---------- Markdown h3 ---------- */
.stMarkdown h3 {
  font-family: var(--serif) !important;
  font-size: 1.35rem !important; font-weight: 400 !important;
  color: var(--ink) !important; letter-spacing: -.003em !important;
  margin-top: 1.6rem !important; margin-bottom: .6rem !important;
  padding-bottom: .4rem !important; border-bottom: 1px solid var(--line) !important;
}

/* ---------- Breadcrumb ---------- */
.breadcrumb {
  font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 600; letter-spacing: .18em;
  text-transform: uppercase; color: var(--muted);
  display: flex; align-items: center; gap: .55rem; margin-bottom: 1.6rem;
}
.breadcrumb-sep { color: var(--line-strong); }
.breadcrumb-active { color: var(--accent); }

/* ---------- Step headers ---------- */
.step-section { margin: 2.4rem 0 .5rem 0; }
.step-num {
  font-family: var(--mono) !important;
  font-size: 10px; font-weight: 600; letter-spacing: .2em;
  color: var(--accent); opacity: .7;
  display: block; margin-bottom: .45rem; font-style: normal;
}
.step-heading {
  font-family: var(--serif) !important;
  font-size: 1.55rem; font-weight: 400 !important;
  color: var(--ink) !important; margin: 0 0 .2rem 0; letter-spacing: -.003em;
}
.step-subtitle {
  font-size: .875rem; color: var(--muted);
  margin: 0 0 .8rem 0; line-height: 1.55; font-weight: 400 !important;
}

/* ---------- Field label ---------- */
.field-label {
  font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 600 !important;
  letter-spacing: .18em; text-transform: uppercase;
  color: var(--muted); display: block; margin-bottom: .45rem; line-height: 1;
}

/* ---------- Pill radio buttons ---------- */
[data-testid="stRadio"] > div {
  display: flex !important; flex-direction: row !important;
  gap: .5rem !important; flex-wrap: wrap !important; align-items: center !important;
}
[data-testid="stRadio"] > div > label {
  display: inline-flex !important; align-items: center !important;
  gap: .4rem !important; padding: .36rem 1rem !important;
  border: 1.5px solid var(--line-strong) !important;
  border-radius: 999px !important; cursor: pointer !important;
  font-size: .88rem !important; color: var(--muted) !important;
  background: var(--card) !important;
  transition: background .18s ease, border-color .18s ease, color .18s ease !important;
  font-family: var(--sans) !important;
}
[data-testid="stRadio"] > div > label:has(input:checked) {
  background: var(--accent) !important;
  border-color: var(--accent) !important; color: #fff !important;
}
[data-testid="stRadio"] > div > label:has(input:checked) p { color: #fff !important; }
[data-testid="stRadio"] > div > label > div:first-child {
  width: 8px !important; height: 8px !important;
  min-width: 8px !important; flex-shrink: 0 !important;
}

/* ---------- Empty state ---------- */
.empty-state-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 2.2rem 1.8rem;
  display: flex; align-items: center; gap: 1.4rem;
  box-shadow: var(--shadow-sm); margin-top: .5rem;
}
.empty-state-badge {
  width: 50px; height: 50px;
  background: rgba(0,0,0,.04); border: 1px solid var(--line);
  border-radius: 12px; display: flex; align-items: center;
  justify-content: center; flex-shrink: 0;
}
.empty-state-badge img { width: 24px; height: 24px; display: block; }
.empty-state-title {
  font-family: var(--serif) !important;
  font-size: 1.2rem; font-weight: 400 !important;
  color: var(--ink); margin: 0 0 .3rem 0;
}
.empty-state-sub {
  font-size: .875rem; color: var(--muted);
  margin: 0; line-height: 1.55;
}

/* ---------- Section divider ---------- */
.section-divider {
  height: 1px; background: var(--line); margin: 1.5rem 0; border: none;
}

/* ---------- Bordered containers (st.container with border=True) ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  --background-color: #ffffff;
  --secondary-background-color: #ffffff;
  background: #ffffff !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow-card) !important;
  overflow: hidden !important; padding: 0 !important;
  margin-top: 2rem !important; margin-bottom: 1.5rem !important;
}
/* Since body carries the grid, transparent div children inside the white card
   still show the grid. Nuke background-image and force white on all divs/sections
   inside. Buttons/spans/SVGs are excluded so their colors survive. */
[data-testid="stVerticalBlockBorderWrapper"] div,
[data-testid="stVerticalBlockBorderWrapper"] section {
  background-color: #ffffff !important;
  background-image: none !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
  padding: 0 !important; gap: .75rem !important;
}

.wizard-card-header-inner {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.1rem 1.6rem 1rem 1.6rem;
  border-bottom: 1px solid var(--line); background: var(--card);
}
.wizard-card-title {
  font-family: var(--serif) !important;
  font-size: 1.45rem; font-weight: 400;
  color: var(--ink); margin: 0; letter-spacing: -.003em;
}
.wizard-card-step {
  font-family: var(--mono) !important;
  font-size: 10.5px; font-weight: 500; letter-spacing: .18em;
  color: var(--muted); text-transform: uppercase;
}
[data-testid="stVerticalBlockBorderWrapper"] .element-container { padding: 0 1.5rem !important; }
[data-testid="stVerticalBlockBorderWrapper"] .element-container:first-child { padding: 0 !important; }
[data-testid="stVerticalBlockBorderWrapper"] .element-container:last-child { padding-bottom: 1.5rem !important; }

@keyframes wizFadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.wizard-animate { animation: wizFadeUp .28s cubic-bezier(0.22,.61,.36,1) both; }

.wizard-choice-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: .2rem; }
.wizard-choice-card {
  background: var(--card); border: 1.5px solid var(--line);
  border-radius: 12px; padding: 1.3rem 1.1rem .9rem 1.1rem;
  margin-bottom: .6rem;
  transition: border-color .18s ease, background .18s ease; cursor: default;
}
.wizard-choice-card:hover { border-color: rgba(255,122,26,.4); background: var(--bg-card-hover); }
.wizard-choice-icon { font-size: 1.5rem; display: block; margin-bottom: .55rem; line-height: 1; }
.wizard-choice-label {
  display: block; font-family: var(--serif) !important;
  font-size: 1.05rem; font-weight: 400;
  color: var(--ink); margin-bottom: .3rem;
}
.wizard-choice-desc {
  display: block; font-size: .82rem; color: var(--muted); line-height: 1.5;
}
.wizard-confirmed {
  display: flex; align-items: center; gap: .6rem;
  padding: .6rem .9rem;
  background: var(--green-soft); border: 1px solid rgba(30,138,85,.2);
  border-radius: 8px; font-size: .88rem; color: var(--green);
  font-weight: 500; margin-bottom: 1rem;
}

/* ---------- Wizard choose phase (redesign) ---------- */
.wiz-title-bar {
  padding: 1.5rem 1.8rem 1.2rem;
  border-bottom: 1px solid var(--line);
  margin: -0.5rem -1.5rem .4rem -1.5rem;
}
.wiz-hdr-title {
  font-family: var(--serif) !important;
  font-size: 1.9rem; font-weight: 400 !important;
  color: var(--ink) !important; margin: 0; letter-spacing: -.01em;
}
.wiz-card { padding: .1rem 0 .7rem 0; }
.wiz-card-icon { font-size: 1.25rem; display: block; margin-bottom: .75rem; line-height: 1; }
.wiz-card-title {
  font-family: var(--serif) !important;
  font-size: 1.2rem; color: var(--ink); margin-bottom: .35rem;
}
.wiz-card-desc { font-size: .82rem; color: var(--muted); line-height: 1.5; margin-bottom: .9rem; }
.wiz-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: .3rem; }
.wiz-tag {
  font-family: var(--mono) !important;
  font-size: 9px; letter-spacing: .13em; text-transform: uppercase;
  padding: 4px 9px; border-radius: 99px;
  border: 1px solid var(--line-strong); color: var(--muted); white-space: nowrap;
}
.wiz-tag-hot {
  color: var(--accent); border-color: rgba(255,122,26,.3);
  background: rgba(255,122,26,.07);
}
.wiz-tag-hot::before { content: "● "; font-size: 7px; vertical-align: middle; }
.wiz-footer {
  border-top: 1px solid var(--line);
  margin: .3rem -1.5rem -1.5rem -1.5rem;
  padding: .7rem 1.8rem;
  display: flex; align-items: center; gap: 1.5rem;
}
.wiz-prog-label {
  font-family: var(--mono) !important;
  font-size: 9px; letter-spacing: .18em; text-transform: uppercase;
  color: var(--muted); flex-shrink: 0;
}
.wiz-prog-track { flex: 1; height: 2px; background: var(--line); border-radius: 2px; overflow: hidden; }
.wiz-prog-fill { height: 100%; background: var(--accent); width: 33%; }
.wiz-steps {
  display: flex; gap: 1.2rem;
  font-family: var(--mono) !important;
  font-size: 9px; letter-spacing: .12em; text-transform: uppercase; flex-shrink: 0;
}
.wiz-step { color: var(--muted); }
.wiz-step.on { color: var(--ink); }
.wiz-hints {
  display: flex; justify-content: space-between; align-items: center;
  padding: .4rem 0 .9rem 0;
  font-size: .72rem; color: var(--muted);
  font-family: var(--mono) !important; letter-spacing: .02em;
}
.wiz-hints a { color: var(--muted); text-decoration: none !important; }
.wiz-hints a:hover { color: var(--ink); }

/* ---------- Discover specifics ---------- */
.disc-metrics { display: flex; gap: 2.5rem; margin-top: .9rem; }
.disc-metric-val {
  font-family: var(--serif) !important;
  font-size: 1.9rem; font-weight: 400;
  color: var(--accent); font-style: italic; line-height: 1.1;
}
.disc-metric-unit { font-size: 1.1rem; font-style: normal; }
.disc-metric-label {
  font-family: var(--mono) !important;
  font-size: 10px; font-weight: 700; letter-spacing: .18em;
  text-transform: uppercase; color: var(--muted); margin-top: .18rem;
}
.disc-pick-badge {
  position: absolute; top: .9rem; right: .9rem;
  background: #0d0d0d; color: #fff;
  font-family: var(--mono) !important;
  font-size: 10px; font-weight: 700; letter-spacing: .1em;
  padding: .22rem .65rem; border-radius: 4px; text-transform: uppercase;
}
.disc-step {
  display: flex; align-items: flex-start; gap: 1.1rem;
  margin: 2.5rem 0 1rem 0;
}
.disc-step-num {
  font-family: var(--mono) !important;
  font-size: 11px; font-style: italic; font-weight: 500;
  color: var(--accent); opacity: .6;
  min-width: 1.4rem; padding-top: .6rem; flex-shrink: 0;
}
.disc-step-head { display: flex; align-items: center; gap: .65rem; margin-bottom: .25rem; }
.disc-step-title {
  font-family: var(--serif) !important;
  font-size: 1.75rem; font-weight: 400; color: var(--ink); margin: 0; line-height: 1.1;
}
.disc-step-sub { font-size: .88rem; color: var(--muted); margin: .2rem 0 0 0; font-weight: 400; }

/* ---------- Cold-start card ---------- */
.cs-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 24px; padding: 26px 32px 24px;
  border-bottom: 1px solid var(--line); background: #ffffff;
}
.cs-head-left { flex: 1; min-width: 0; }
.cs-title {
  font-family: var(--serif) !important;
  font-size: 2.2rem !important; font-weight: 400 !important;
  line-height: 1.05; margin: 0 0 8px 0 !important;
  color: var(--ink) !important; letter-spacing: -.005em;
}
.cs-accent { color: var(--accent) !important; font-style: italic; }
.cs-subtitle {
  margin: 0; color: var(--muted); font-style: italic;
  font-size: 1rem; font-weight: 400 !important; line-height: 1.5;
}
.cs-stepper {
  display: flex; align-items: center; gap: 10px;
  flex-shrink: 0; list-style: none; padding: 0; margin: 0;
}
.cs-step-dot {
  display: flex; align-items: center; gap: 8px;
  color: var(--muted); font-family: var(--mono) !important; font-size: 11px; letter-spacing: .06em;
}
.cs-step-n {
  width: 24px; height: 24px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,.04); border: 1px solid var(--line);
  color: var(--muted); font-family: var(--mono) !important;
  font-size: 11px; font-weight: 500; flex-shrink: 0;
}
.cs-step-active .cs-step-n { background: var(--accent); border-color: var(--accent); color: #fff; }
.cs-step-active { color: var(--ink); }
.cs-step-label {
  font-family: var(--mono) !important;
  font-size: 10px; letter-spacing: .22em; text-transform: uppercase; font-weight: 500;
}
.cs-step-line { width: 32px; height: 1px; background: var(--line); flex-shrink: 0; display: inline-block; }
.cs-sec-head {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 16px; margin: 1rem 0 .55rem 0;
  padding-top: 1rem; border-top: 1px dashed var(--line);
}
.cs-sec-head-first { padding-top: .7rem; border-top: none; margin-top: .7rem; }
.cs-sec-left { display: flex; align-items: center; gap: 12px; }
.cs-sec-icon {
  width: 30px; height: 30px; border-radius: 9px;
  background: rgba(0,0,0,.04); border: 1px solid var(--line);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; color: var(--ink);
}
.cs-sec-icon svg { width: 16px; height: 16px; }
.cs-sec-label-txt {
  font-family: var(--mono) !important;
  font-size: 10px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--muted); font-weight: 600 !important; display: block; margin-bottom: 2px;
}
.cs-req {
  color: var(--accent); font-style: italic;
  font-size: 12px; letter-spacing: .02em;
  text-transform: none; margin-left: 5px; font-weight: 500 !important;
}
.cs-sec-h3 {
  font-family: var(--serif) !important;
  font-size: 1.25rem !important; font-weight: 400 !important;
  line-height: 1.1; margin: 0 !important; padding: 0 !important;
  border: none !important; border-bottom: none !important;
  color: var(--ink) !important; letter-spacing: -.003em;
}
.cs-foot-sep { height: 1px; background: var(--line); margin: 1.2rem -1.5rem 0 -1.5rem; }
.cs-foot-note { font-style: italic; color: var(--muted); font-size: .93rem; margin: 0; padding-top: .2rem; }

[data-testid="stForm"] { background: transparent !important; border: none !important; padding: 0 !important; }

/* ---------- Discover page header ---------- */
.disc-ph {
  display: flex; align-items: flex-end;
  justify-content: space-between; gap: 24px;
  margin-bottom: 1.4rem;
}
.disc-ph-title {
  font-family: var(--serif) !important;
  font-size: 3.5rem; font-weight: 400 !important;
  color: var(--ink) !important; line-height: 1.05;
  margin: 0; letter-spacing: -.01em;
}
.disc-ph-title i { color: var(--ink-2); }
.disc-ph-sub {
  color: var(--muted); font-size: 14px;
  margin: .5rem 0 0 0; max-width: 560px; line-height: 1.55;
}
.disc-ph-food {
  position: absolute;
  right: 0; top: -30px;
  height: 300px; width: auto;
  object-fit: contain;
  pointer-events: none;
  z-index: 0;
  filter: drop-shadow(0 8px 24px rgba(0,0,0,.12));
}
.disc-ph { position: relative; overflow: visible; }
.disc-ph > div, .disc-ph > a { position: relative; z-index: 1; }
.disc-ph-actions { display: flex; gap: 10px; flex-shrink: 0; align-items: center; }
.disc-btn-ghost {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 16px; border-radius: 11px;
  border: 1px solid var(--line-strong); background: #fff;
  color: var(--ink); font-family: var(--sans) !important;
  font-size: 14px; cursor: pointer; text-decoration: none !important;
  transition: background .12s;
}
.disc-btn-ghost:hover { background: #fafaf8; }
.disc-btn-accent {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 9px 16px; border-radius: 11px;
  background: var(--accent); color: #0a0a0a;
  font-family: var(--sans) !important;
  font-size: 14px; font-weight: 500; cursor: pointer;
  text-decoration: none !important;
  transition: transform .12s, box-shadow .12s;
}
.disc-btn-accent:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(255,122,26,.32); }

/* ---------- Discover filter rail ---------- */
.disc-frail-head {
  font-family: var(--serif) !important;
  font-size: 1.4rem; font-weight: 400; color: var(--ink); margin-bottom: .8rem;
}
.disc-flabel {
  font-family: var(--mono) !important;
  font-size: 10px; font-weight: 700; letter-spacing: .22em;
  text-transform: uppercase; color: var(--muted);
  display: block; margin: .8rem 0 .3rem 0;
}
.disc-fdivider { height: 1px; background: var(--line); margin: .8rem 0; }

/* ---------- Discover list header ---------- */
.disc-list-head {
  display: flex; align-items: center;
  justify-content: space-between; gap: 12px; margin-bottom: 1rem;
}
.disc-list-title {
  font-family: var(--serif) !important;
  font-size: 2rem; font-weight: 400 !important;
  color: var(--ink); margin: 0; line-height: 1;
}
.disc-list-title i { color: var(--ink-2); }
.disc-list-sort { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
.disc-sort-pill {
  background: #fff; border: 1px solid var(--line-strong);
  padding: 5px 11px; border-radius: 99px;
  color: var(--ink); font-size: 13px; white-space: nowrap;
}

/* ---------- Discover now-driving card ---------- */
.disc-nd-card {
  background: #0d0d0d; color: #fff;
  border-radius: var(--radius); padding: 18px;
  display: flex; flex-direction: column; gap: 14px;
  margin-bottom: 14px;
}
.disc-nd-label {
  font-family: var(--mono) !important;
  font-size: 10.5px; letter-spacing: .18em;
  text-transform: uppercase; color: rgba(255,255,255,.45);
}
.disc-nd-route {
  font-family: var(--serif) !important;
  font-size: 1.4rem; font-weight: 400; color: #fff;
  display: flex; align-items: center; gap: 10px;
}
.disc-nd-arrow { color: var(--accent); }
.disc-nd-stats {
  display: grid; grid-template-columns: repeat(3,1fr); gap: 12px;
  padding-top: 10px; border-top: 1px solid rgba(255,255,255,.1);
}
.disc-nd-s { display: flex; flex-direction: column; gap: 2px; }
.disc-nd-s b {
  font-family: var(--serif) !important;
  font-size: 1.5rem; font-weight: 400 !important; color: #fff !important;
}
.disc-nd-s small {
  font-family: var(--mono) !important;
  font-size: 10px; letter-spacing: .16em; text-transform: uppercase;
  color: rgba(255,255,255,.4); margin-top: 2px;
}
.disc-nd-map-link {
  display: block; text-align: center; padding: 10px;
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius-sm); color: var(--ink);
  text-decoration: none !important; font-size: 14px;
  transition: background .15s;
}
.disc-nd-map-link:hover { background: #fafaf8; }

/* ---------- Filter inline (replaces sidebar) ---------- */
.filter-inline-wrap {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius-sm); padding: .8rem 1.2rem;
  margin-bottom: 1.2rem; box-shadow: var(--shadow-sm);
}

/* ---------- Top nav bar (fixed) ---------- */
.ps-topnav {
  position: fixed;
  top: 44px;
  left: 50%;
  transform: translateX(-50%);
  width: min(calc(100vw - 20px), 1800px);
  z-index: 9998;
  background: rgba(255,255,255,0.94);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: var(--radius);
  padding: 13px 18px 13px 22px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 24px;
  box-shadow: 0 1px 0 rgba(255,255,255,.6) inset, var(--shadow-sm);
}
.ps-topnav-brand {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--serif) !important;
  font-size: 22px; letter-spacing: .005em; color: var(--ink);
  text-decoration: none;
}
.ps-topnav-brand .dot {
  width: 9px; height: 9px; border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
  flex-shrink: 0;
}
.ps-topnav-logo {
  height: 28px; width: auto; object-fit: contain; display: block;
}
.ps-dock-logo {
  height: 32px; width: auto; object-fit: contain; display: block;
}
.ps-topnav-links {
  display: flex; gap: 30px; justify-self: center;
  font-family: var(--sans) !important; font-size: 14px;
}
.ps-topnav-links a {
  color: var(--ink-2); text-decoration: none !important;
  padding: 5px 2px; position: relative;
  transition: color .15s;
}
.ps-topnav-links a:hover { color: var(--ink); }
.ps-topnav-links a.active { color: var(--ink); }
.ps-topnav-links a.active::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: -2px;
  height: 2px; background: var(--accent); border-radius: 2px;
}
.ps-topnav-cta {
  justify-self: end;
  background: var(--accent); color: #0a0a0a;
  border: none; font-family: var(--sans) !important;
  font-weight: 500; font-size: 14px;
  padding: 10px 18px; border-radius: 11px;
  cursor: pointer;
  transition: transform .12s ease, box-shadow .12s ease;
  display: inline-block; text-decoration: none !important;
}
.ps-topnav-cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(255,122,26,.32);
}

/* ---------- Hero section ---------- */
.ps-hero {
  position: relative;
  display: grid;
  place-items: center;
  padding: 8px 0 16px;
  min-height: 520px;
  overflow: hidden;
}
.ps-hero-stack {
  position: relative;
  width: 100%;
  display: flex; flex-direction: column; align-items: center;
}
.ps-headline {
  font-family: 'Rubik', var(--sans) !important;
  font-weight: 200 !important;
  text-align: center;
  font-size: 150px !important;
  line-height: .93;
  letter-spacing: -.015em;
  margin: 0;
  position: relative; z-index: 2;
  color: var(--ink) !important;
}
.ps-headline .row1 { display: block; font-size: inherit !important; font-family: inherit !important; }
.ps-headline .row2 { display: block; font-style: italic; color: var(--ink-2); font-size: inherit !important; font-family: inherit !important; }

.ps-cursor {
  font-style: normal !important;
  font-weight: 200 !important;
  color: var(--accent) !important;
  margin-left: 3px;
  animation: blink-cursor .8s step-end infinite;
  display: inline !important;
}
@keyframes blink-cursor {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}
.stMarkdown .ps-headline,
[data-testid="stMarkdownContainer"] .ps-headline {
  font-size: 150px !important;
  font-family: 'Rubik', var(--sans) !important;
  font-weight: 200 !important;
}
.stMarkdown .ps-headline span,
[data-testid="stMarkdownContainer"] .ps-headline span {
  font-family: 'Rubik', var(--sans) !important;
  font-weight: 200 !important;
}

.ps-hero-art {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -52%);
  width: min(1200px, 92%);
  z-index: 0;
  pointer-events: none;
  filter: drop-shadow(0 28px 40px rgba(0,0,0,.20));
}
.ps-hero-art img { width: 100%; height: auto; display: block; }

.ps-subline-wrap {
  position: relative; z-index: 2;
  margin-top: clamp(420px, 48vw, 620px);
  width: min(860px, 88%);
  display: flex; flex-direction: column; align-items: center; gap: 16px;
}
.ps-dashed { width: 100%; border-top: 1.5px dashed var(--ink); opacity: .65; }
.ps-subline {
  font-family: var(--mono) !important;
  font-size: clamp(11px, 1vw, 14px) !important;
  letter-spacing: .22em;
  text-transform: uppercase;
  color: var(--ink); margin: 0; text-align: center;
}

.ps-status-chip {
  position: absolute; top: 16px; left: 16px; z-index: 3;
  display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--mono) !important; font-size: 10.5px;
  letter-spacing: .18em; text-transform: uppercase; color: var(--muted);
  background: rgba(255,255,255,.7);
  border: 1px solid var(--line);
  padding: 7px 12px; border-radius: 999px;
  backdrop-filter: blur(8px);
}
.ps-status-chip .pulse-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  animation: pulseGreen 1.8s infinite;
}
@keyframes pulseGreen {
  0%   { box-shadow: 0 0 0 0 rgba(30,138,85,.55); }
  70%  { box-shadow: 0 0 0 9px rgba(30,138,85,0); }
  100% { box-shadow: 0 0 0 0 rgba(30,138,85,0); }
}
.ps-corner-meta {
  position: absolute; top: 20px; right: 16px; z-index: 3;
  text-align: right;
  font-family: var(--mono) !important; font-size: 10.5px;
  letter-spacing: .18em; text-transform: uppercase;
  color: var(--muted); line-height: 1.7;
}
.ps-corner-meta b { color: var(--ink); font-weight: 500; }
</style>
"""


def inject_css() -> None:
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Abril+Fatface&family=Rubik:ital,wght@0,200;0,300;0,400;0,500;1,200;1,300&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<h1 class="dashboard-title">{title}</h1>'
        f'<p class="dashboard-subtitle">{subtitle}</p>',
        unsafe_allow_html=True,
    )


def status_banner(kind: str, message: str) -> None:
    cls = {"ok": "ok", "warn": "warn", "err": "err", "info": "info"}.get(kind, "")
    st.markdown(f'<div class="status-banner {cls}">{message}</div>', unsafe_allow_html=True)


def metric_pill(label: str, value: str) -> None:
    st.markdown(
        f'<div class="metric-pill"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def render_topnav(current_page: str = "app") -> None:
    """Render the fixed top navigation bar on every page."""
    _nav_pages = [
        ("app",       "Home",      "./"),
        ("discover",  "Discover",  "./Discover"),
        ("admin",     "Admin",     "./Admin"),
        ("analytics", "Analytics", "./Analytics"),
    ]

    def _link(page_id: str, label: str, href: str) -> str:
        active = ' class="active"' if current_page == page_id else ""
        return f'<a href="{href}" target="_self"{active}>{label}</a>'

    links_html = "\n".join(_link(pid, lbl, href) for pid, lbl, href in _nav_pages)

    _logo = _logo_src()
    brand_html = (
        f'<img src="{_logo}" alt="McGill" class="ps-topnav-logo" />'
        if _logo else '<span class="dot"></span>Pitstop'
    )
    st.markdown(
        f"""
        <nav class="ps-topnav">
          <div class="ps-topnav-brand">{brand_html}</div>
          <div class="ps-topnav-links">{links_html}</div>
          <a class="ps-topnav-cta" href="./Discover" target="_self">Get Started</a>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def render_dock(
    current_page: str = "app",
    user_id: str | None = None,
    model_name: str = "Hybrid v2.4",
    region: str = "EU · London",
) -> None:
    """Render the PITSTOP bottom dock navigation."""

    uid = user_id or ""
    avatar_label = uid[:2].upper() if uid else "DR"
    display_name = (uid[:8] + "…") if uid else "Guest"

    def _tab(page_id: str, href: str, icon_path: str, label: str) -> str:
        active = "active" if current_page == page_id else ""
        return (
            f'<a href="{href}" class="ps-tab {active}" target="_self">'
            f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
            f'{icon_path}</svg>{label}</a>'
        )

    tabs_html = (
        _tab("app",       "./",          '<rect x="3" y="3" width="7" height="7" rx="1.2"/><rect x="14" y="3" width="7" height="7" rx="1.2"/><rect x="3" y="14" width="7" height="7" rx="1.2"/><rect x="14" y="14" width="7" height="7" rx="1.2"/>',                                                        "app")
      + _tab("discover",  "./Discover",  '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5L13.5 13.5 8.5 15.5 10.5 10.5Z"/>',                                                                                                                                                                               "Discover")
      + _tab("map",       "./Map_View",  '<path d="M9 4L3 6V20L9 18L15 20L21 18V4L15 6Z"/><path d="M9 4V18M15 6V20"/>',                                                                                                                                                                                        "Map View")
      + _tab("admin",     "./Admin",     '<path d="M12 2L20 5V11C20 16 16 20 12 22 8 20 4 16 4 11V5Z"/><path d="M9 12L11 14 15 10"/>',                                                                                                                                                                         "Admin")
      + _tab("analytics", "./Analytics", '<path d="M4 20V10M10 20V4M16 20V13M22 20H2"/>',                                                                                                                                                                                                                      "Analytics")
    )

    _dock_logo = _logo_src()
    _dock_brand_html = (
        f'<img src="{_dock_logo}" alt="McGill" class="ps-dock-logo" />'
        if _dock_logo
        else '<div class="ps-brand-mark">P</div><div><b>Pitstop</b><small>v0.4·beta</small></div>'
    )

    yelp_svg = (
        '<svg width="11" height="11" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="32" cy="32" r="32" fill="#D32323"/>'
        '<g fill="white" transform="translate(32,32)">'
        '<path d="M0,0 C-5,-4,-6,-14,0,-24 C6,-14,5,-4,0,0Z"/>'
        '<path d="M0,0 C-5,-4,-6,-14,0,-24 C6,-14,5,-4,0,0Z" transform="rotate(72)"/>'
        '<path d="M0,0 C-5,-4,-6,-14,0,-24 C6,-14,5,-4,0,0Z" transform="rotate(144)"/>'
        '<path d="M0,0 C-5,-4,-6,-14,0,-24 C6,-14,5,-4,0,0Z" transform="rotate(216)"/>'
        '<path d="M0,0 C-5,-4,-6,-14,0,-24 C6,-14,5,-4,0,0Z" transform="rotate(288)"/>'
        '</g></svg>'
    )

    pipeline_svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M11 18H8a2 2 0 0 1-2-2V9"/></svg>'
    settings_svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>'

    st.markdown(
        f"""
        <div class="ps-dock">
          <div class="ps-dg ps-brand">
            {_dock_brand_html}
          </div>

          <div class="ps-dg">
            <span class="ps-dg-label">Pages</span>
            <div class="ps-tabs">{tabs_html}</div>
          </div>

          <div class="ps-dg">
            <span class="ps-dg-label">Workspace</span>
            <a href="https://www.yelp.com/dataset" class="ps-pill" target="_blank" rel="noopener noreferrer">
              <span class="pic acc">{yelp_svg}</span>Yelp Dataset
            </a>
            <a href="#" class="ps-pill">
              <span class="pic">{pipeline_svg}</span>Pipelines
            </a>
            <a href="#" class="ps-pill">
              <span class="pic">{settings_svg}</span>Settings
            </a>
          </div>

          <div class="ps-dg">
            <div class="ps-info">
              <span class="pip"></span>
              <span class="k">Model</span>
              <span class="v">{model_name}</span>
              <span class="pip am"></span>
              <span class="k">Region</span>
              <span class="v">{region}</span>
            </div>
          </div>

          <div class="ps-user">
            <div class="av">{avatar_label}</div>
            <div class="stk">
              <b>{display_name}</b>
              <small>Driver &middot; Pro</small>
            </div>
            <span class="chev">&#8250;</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- Stubs for backward compatibility ----------

def sidebar_extras(*args, **kwargs) -> None:
    """No-op — sidebar replaced by dock navigation."""
    pass


def sidebar_logo(*args, **kwargs) -> None:
    """No-op — sidebar removed."""
    pass


def breadcrumb(*parts: tuple[str, bool]) -> None:
    items: list[str] = []
    for i, (label, active) in enumerate(parts):
        cls = ' class="breadcrumb-active"' if active else ""
        items.append(f"<span{cls}>{label}</span>")
        if i < len(parts) - 1:
            items.append('<span class="breadcrumb-sep">/</span>')
    st.markdown(f'<nav class="breadcrumb">{"".join(items)}</nav>', unsafe_allow_html=True)


def styled_page_header(title: str, subtitle: str = "", icon_src: str = "") -> None:
    badge = (
        f'<div class="page-header-badge"><img src="{icon_src}" alt=""/></div>'
        if icon_src else ""
    )
    sub = f'<p class="page-header-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="page-header-wrap">{badge}<div>'
        f'<h1 class="page-header-title">{title}</h1>{sub}</div></div>',
        unsafe_allow_html=True,
    )


def step_header(num: str, heading: str, subtitle: str = "") -> None:
    sub = f'<p class="step-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="step-section"><span class="step-num">{num}</span>'
        f'<div class="step-heading">{heading}</div>{sub}</div>',
        unsafe_allow_html=True,
    )


def field_label(text: str) -> None:
    st.markdown(f'<span class="field-label">{text}</span>', unsafe_allow_html=True)


def empty_state_card(title: str, subtitle: str = "", icon_src: str = "") -> None:
    badge = (
        f'<div class="empty-state-badge"><img src="{icon_src}" alt=""/></div>'
        if icon_src else ""
    )
    sub = f'<p class="empty-state-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="empty-state-card">{badge}<div>'
        f'<div class="empty-state-title">{title}</div>{sub}</div></div>',
        unsafe_allow_html=True,
    )
