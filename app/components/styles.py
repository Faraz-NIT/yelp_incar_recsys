"""Custom CSS and theme injection for the Streamlit app."""
from __future__ import annotations

import streamlit as st


GLOBAL_CSS = """
<style>
/* ---------- Font ---------- */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&display=swap');

html { font-size: 15.84px !important; }

html, body, [class*="css"], .stApp, .stMarkdown, .stText,
h1, h2, h3, h4, h5, h6, p, span, div, label, button, input, select, textarea {
    font-family: "Cormorant Garamond", "Times New Roman", Georgia, serif !important;
    font-weight: 500 !important;
}

/* ---------- Base ---------- */
:root {
    --bg-primary:    #EDE4D9;
    --bg-secondary:  #E5DDD3;
    --bg-card:       #FFFFFF;
    --bg-card-hover: #FAFAF8;
    --accent:        #C4563A;
    --accent-mid:    #A8422A;
    --accent-soft:   #C4563A12;
    --success:       #155E42;
    --warning:       #78350F;
    --danger:        #7F1D1D;
    --text-primary:  #1C2438;
    --text-secondary:#6B7280;
    --text-muted:    #9CA3AF;
    --border:        #E8E3DC;
    --radius:        16px;
    --shadow-sm:     0 1px 4px rgba(0,0,0,0.06);
    --shadow-card:   0 4px 28px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04);
    --shadow-hover:  0 10px 40px rgba(28,36,56,0.11), 0 2px 8px rgba(0,0,0,0.05);
}

/* ---------- App shell ---------- */
.stApp {
    background: var(--bg-primary) !important;
    color: var(--text-primary);
}

section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] > div {
    padding-top: 0.5rem;
}

/* ---------- Sidebar navigation ---------- */
[data-testid="stSidebarNav"] {
    padding-top: 0 !important;
    width: 100% !important;
}

[data-testid="stSidebarNav"]::before {
    content: "PAGES";
    display: block;
    font-size: 0.60rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    color: var(--text-muted);
    padding: 0.9rem 1rem 0.45rem 1rem;
    font-family: "Cormorant Garamond", serif;
}

[data-testid="stSidebarNav"] ul {
    padding: 0 0.5rem !important;
    margin: 0 !important;
    list-style: none !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 2px !important;
}

[data-testid="stSidebarNav"] ul li a {
    display: flex !important;
    align-items: center !important;
    gap: 0.65rem !important;
    padding: 0.52rem 0.75rem !important;
    border-radius: 8px !important;
    color: var(--text-secondary) !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    font-family: "Cormorant Garamond", serif !important;
    text-decoration: none !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    border-left: 2.5px solid transparent !important;
}

[data-testid="stSidebarNav"] ul li a:hover {
    background: rgba(255,255,255,0.6) !important;
    color: var(--text-primary) !important;
}

[data-testid="stSidebarNav"] ul li a[aria-current="page"] {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    font-weight: 500 !important;
    box-shadow: var(--shadow-sm) !important;
    border-left-color: var(--accent) !important;
}

/* ---------- Sidebar workspace section ---------- */
.sidebar-group-label {
    font-size: 0.60rem;
    font-weight: 700 !important;
    letter-spacing: 0.14em;
    color: var(--text-muted);
    display: block;
    padding: 0.9rem 0.5rem 0.45rem 0.5rem;
    font-family: "Cormorant Garamond", serif !important;
}

.sidebar-ws-wrap {
    padding: 0 0.5rem;
}

.sidebar-ws-item {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.52rem 0.75rem;
    border-radius: 8px;
    color: var(--text-secondary);
    font-size: 1rem;
    font-family: "Cormorant Garamond", serif;
    font-weight: 400;
    cursor: default;
    transition: background 0.15s ease, color 0.15s ease;
    border-left: 2.5px solid transparent;
    margin: 1px 0;
}

.sidebar-ws-item:hover {
    background: rgba(255,255,255,0.55);
    color: var(--text-primary);
}

/* ---------- Sidebar status card ---------- */
.sidebar-status {
    margin: 0.8rem 0.5rem 0.4rem 0.5rem;
    padding: 0.75rem 0.9rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
}

.sidebar-status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.3rem;
}

.sidebar-status-row:last-child { margin-bottom: 0; }

.sidebar-status-key {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.60rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--text-muted);
    font-family: "Cormorant Garamond", serif;
}

.sidebar-status-val {
    font-size: 0.82rem;
    color: var(--text-secondary);
    font-style: italic;
    font-family: "Cormorant Garamond", serif;
}

.dot-green { color: #155E42; }
.dot-red   { color: var(--accent); }

/* ---------- Sidebar user card ---------- */
.sidebar-user-card {
    margin: 0.4rem 0.5rem 0.5rem 0.5rem;
    padding: 0.65rem 0.9rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
    display: flex;
    align-items: center;
    gap: 0.7rem;
}

.sidebar-user-avatar {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: var(--accent);
    color: #fff;
    font-size: 0.68rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-family: "Cormorant Garamond", serif;
    letter-spacing: 0.02em;
}

.sidebar-user-name {
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-primary);
    font-family: "Cormorant Garamond", serif;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 120px;
}

.sidebar-user-role {
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    font-family: "Cormorant Garamond", serif;
}

.sidebar-user-arrow {
    margin-left: auto;
    color: var(--text-muted);
    font-size: 0.85rem;
    flex-shrink: 0;
}

/* ---------- Typography ---------- */
h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
}

.dashboard-title {
    font-size: 2.2rem;
    font-weight: 600 !important;
    color: var(--accent) !important;
    margin: 0;
    letter-spacing: 0.02em;
}

.dashboard-subtitle {
    color: var(--text-secondary);
    font-size: 1rem;
    font-weight: 500 !important;
    margin: 0.25rem 0 1.5rem 0;
}

/* ---------- Hero Card (2-column) ---------- */
.hero-card {
    background: var(--bg-card);
    border-radius: var(--radius);
    margin-bottom: 2.5rem;
    box-shadow: var(--shadow-card);
    display: flex;
    overflow: hidden;
    min-height: 290px;
}

.hero-left {
    flex: 0 0 42%;
    padding: 3rem 2.5rem 2.5rem 3rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.hero-right {
    flex: 1 1 58%;
    background: var(--bg-card);
    border-radius: 0 var(--radius) var(--radius) 0;
    overflow: hidden;
    position: relative;
    min-height: 290px;
}

.hero-right svg {
    width: 100%;
    height: 100%;
    display: block;
}

.hero-img {
    position: absolute;
    inset: 0.75rem;
    width: calc(100% - 1.5rem);
    height: calc(100% - 1.5rem);
    object-fit: cover;
    object-position: center center;
    border-radius: 12px;
}

.hero-eyebrow {
    font-size: 0.70rem;
    font-weight: 600 !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.85rem;
    display: block;
}

.hero-title {
    font-size: 3.6rem;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    line-height: 1.1;
    margin: 0 0 0.8rem 0;
    letter-spacing: 0.01em;
}

.hero-accent {
    color: var(--accent) !important;
    font-style: italic;
    font-weight: 600 !important;
}

.hero-subtitle {
    font-size: 1.1rem;
    font-weight: 500 !important;
    color: var(--text-secondary);
    line-height: 1.65;
    margin: 0 0 1.8rem 0;
    max-width: 400px;
}

.hero-pills {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.28rem 0.9rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 500 !important;
    color: var(--text-secondary);
    background: white;
    letter-spacing: 0.01em;
}

.hero-pill-dot {
    color: var(--accent);
    font-size: 0.55rem;
    line-height: 1;
}

/* ---------- Section header ---------- */
.section-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 1.2rem;
    margin-top: 0.5rem;
}

.section-title {
    font-size: 2.2rem;
    font-weight: 600 !important;
    color: var(--text-primary);
    letter-spacing: 0.01em;
}

.section-label {
    font-size: 0.70rem;
    font-weight: 500 !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
}

/* ---------- Navigation Cards ---------- */
.nav-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.7rem 1.5rem 2rem 1.5rem;
    min-height: 170px;
    box-shadow: var(--shadow-card);
    transition: box-shadow 0.22s ease, transform 0.22s ease, border-color 0.22s ease;
    position: relative;
    overflow: hidden;
}

.nav-card:hover {
    box-shadow: var(--shadow-hover);
    border-color: rgba(196,86,58,0.35);
    transform: translateY(-4px);
}

.nav-card-icon {
    margin-bottom: 0.8rem;
    display: block;
    line-height: 1;
}

.nav-card-icon svg {
    width: 36px;
    height: 36px;
    display: block;
}

.nav-card-title {
    font-size: 1.2rem;
    font-weight: 600 !important;
    color: var(--text-primary);
    margin-bottom: 0.45rem;
    letter-spacing: 0.01em;
}

.nav-card-desc {
    font-size: 0.95rem;
    font-weight: 500 !important;
    color: var(--text-secondary);
    line-height: 1.6;
}

.nav-card-arrow {
    position: absolute;
    bottom: 1rem;
    right: 1.2rem;
    color: var(--text-muted);
    font-size: 0.9rem;
    font-weight: 500 !important;
    transition: color 0.2s ease, right 0.2s ease;
}

.nav-card:hover .nav-card-arrow {
    color: var(--accent);
    right: 1rem;
}

/* ---------- Rec Cards ---------- */
.rec-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0;
    margin-bottom: 0.9rem;
    box-shadow: var(--shadow-card);
    transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: row;
    align-items: stretch;
}

.rec-card-body {
    flex: 1 1 auto;
    min-width: 0;
    padding: 1.1rem 1.3rem;
    position: relative;
}

.rec-card-photo {
    flex: 0 0 220px;
    width: 220px;
    overflow: hidden;
    border-radius: 0 var(--radius) var(--radius) 0;
}
.rec-card-photo img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
    display: block;
}

.rec-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--accent);
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
}

.rec-card::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--accent);
}

.rec-card-rank {
    position: absolute;
    top: 0.8rem;
    right: 1rem;
    font-size: 2rem;
    font-weight: 500 !important;
    color: var(--accent);
    opacity: 0.18;
    line-height: 1;
}

.rec-card-name {
    font-size: 1.35rem;
    font-weight: 600 !important;
    color: var(--text-primary);
    margin: 0 3rem 0.25rem 0;
    letter-spacing: 0.01em;
}

.rec-card-meta {
    color: var(--text-secondary);
    font-size: 0.85rem;
    font-weight: 500 !important;
    margin-bottom: 0.5rem;
}

.rec-card-why {
    color: var(--text-secondary);
    font-size: 0.92rem;
    font-weight: 500 !important;
    font-style: italic;
    line-height: 1.6;
    margin-top: 0.5rem;
    padding: 0.65rem 0.9rem;
    background: var(--accent-soft);
    border-left: 2px solid var(--accent);
    border-radius: 0 6px 6px 0;
}

/* ---------- Tags ---------- */
.tag {
    display: inline-block;
    padding: 0.12rem 0.6rem;
    margin: 0.15rem 0.3rem 0.15rem 0;
    font-size: 0.74rem;
    font-weight: 500 !important;
    background: var(--bg-secondary);
    color: var(--text-secondary);
    border-radius: 999px;
    border: 1px solid var(--border);
    letter-spacing: 0.02em;
}

.tag-accent {
    background: var(--accent-soft);
    color: var(--accent);
    border: 1px solid rgba(196,86,58,0.22);
}

.tag-success {
    background: rgba(21,94,66,0.08);
    color: var(--success);
    border: 1px solid rgba(21,94,66,0.20);
}

.tag-warning {
    background: rgba(120,53,15,0.08);
    color: var(--warning);
    border: 1px solid rgba(120,53,15,0.18);
}

/* ---------- Metric pills ---------- */
.metric-pill {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    text-align: center;
    box-shadow: var(--shadow-sm);
}

.metric-pill .label {
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.metric-pill .value {
    color: var(--accent);
    font-size: 1.6rem;
    font-weight: 600 !important;
    margin-top: 0.2rem;
}

/* ---------- Buttons ---------- */
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-family: "Cormorant Garamond", serif !important;
    font-size: 1rem !important;
    letter-spacing: 0.04em !important;
    padding: 0.55rem 1.5rem !important;
    transition: all 0.18s ease;
}

.stButton > button:hover {
    background: var(--accent-mid) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 18px rgba(196,86,58,0.25);
}

.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

/* ---------- Inputs ---------- */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stMultiSelect > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    font-family: "Cormorant Garamond", serif !important;
    font-weight: 500 !important;
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-radius: 0;
    padding: 0;
    gap: 0;
    border: none;
    border-bottom: 1.5px solid var(--border);
}

.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: var(--text-secondary);
    border-radius: 0;
    padding: 0.55rem 1.3rem;
    font-weight: 500 !important;
    font-size: 0.9rem;
    letter-spacing: 0.02em;
    border-bottom: 2.5px solid transparent;
    margin-bottom: -1.5px;
    transition: color 0.18s;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--accent) !important;
    background: transparent !important;
}

.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: var(--accent) !important;
    border-bottom: 2.5px solid var(--accent) !important;
}

/* hide the default BaseWeb highlight bar */
.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ---------- Status banner ---------- */
.status-banner {
    padding: 0.75rem 1.1rem;
    border-radius: var(--radius);
    margin-bottom: 1rem;
    border: 1px solid var(--border);
    border-left: 3px solid var(--border);
    background: var(--bg-card);
    font-size: 0.9rem;
    font-weight: 500 !important;
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
}

.status-banner.ok {
    border-left-color: var(--success);
    background: rgba(21,94,66,0.03);
}

.status-banner.warn {
    border-left-color: #D97706;
    background: rgba(120,53,15,0.03);
}

.status-banner.err {
    border-left-color: var(--danger);
    background: rgba(127,29,29,0.03);
}

/* ---------- Divider ---------- */
.section-divider {
    height: 1px;
    background: var(--border);
    margin: 1.5rem 0;
    border: none;
}

/* ---------- Metrics ---------- */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem 1.2rem !important;
    box-shadow: var(--shadow-sm) !important;
}

[data-testid="stMetricLabel"] > div,
[data-testid="stMetricLabel"] p {
    font-size: 0.70rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-muted) !important;
    font-family: "Cormorant Garamond", serif !important;
}

[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] p {
    font-size: 1.55rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    font-family: "Cormorant Garamond", serif !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.80rem !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Section sub-headers (### markdown) ---------- */
.stMarkdown h3 {
    font-size: 1.35rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    letter-spacing: 0.01em !important;
    margin-top: 1.6rem !important;
    margin-bottom: 0.6rem !important;
    padding-bottom: 0.4rem !important;
    border-bottom: 1px solid var(--border) !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Progress bar ---------- */
.stProgress > div > div > div > div {
    background-color: var(--accent) !important;
    border-radius: 999px !important;
}

.stProgress > div > div > div {
    background-color: var(--bg-secondary) !important;
    border-radius: 999px !important;
}

/* ---------- Checkbox / Radio ---------- */
.stCheckbox label p,
.stRadio label p {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Caption / helper text ---------- */
.stMarkdown p small,
[data-testid="stCaptionContainer"] p {
    color: var(--text-muted) !important;
    font-size: 0.82rem !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Expander ---------- */
details summary p {
    font-weight: 500 !important;
    color: var(--text-primary) !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Dataframe header ---------- */
[data-testid="stDataFrame"] th {
    background: var(--bg-secondary) !important;
    color: var(--text-secondary) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-family: "Cormorant Garamond", serif !important;
    font-weight: 500 !important;
}

/* ---------- Info / warning / success banners (native st.info etc.) ---------- */
[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Breadcrumb ---------- */
.breadcrumb {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin-bottom: 1.6rem;
}
.breadcrumb-sep { color: var(--border); }
.breadcrumb-active { color: var(--accent); }

/* ---------- Page header with icon badge ---------- */
.page-header-wrap {
    display: flex;
    align-items: flex-start;
    gap: 1.4rem;
    margin-bottom: 2.4rem;
}
.page-header-badge {
    width: 58px;
    height: 58px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow-sm);
    flex-shrink: 0;
    margin-top: 6px;
}
.page-header-badge img { width: 28px; height: 28px; display: block; }
.page-header-title {
    font-size: 3rem;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    line-height: 1.1;
    margin: 0;
    letter-spacing: 0.01em;
    font-family: "Cormorant Garamond", serif !important;
}
.page-header-subtitle {
    font-size: 0.95rem;
    color: var(--text-secondary);
    font-style: italic;
    margin: 0.35rem 0 0 0;
    font-weight: 500 !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Step section headers ---------- */
.step-section { margin: 2.6rem 0 0.5rem 0; }
.step-num {
    font-size: 0.64rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--accent);
    opacity: 0.55;
    display: block;
    margin-bottom: 0.45rem;
    font-family: "Cormorant Garamond", serif;
    font-style: normal;
}
.step-heading {
    font-size: 1.6rem;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0 0 0.2rem 0;
    letter-spacing: 0.01em;
    font-family: "Cormorant Garamond", serif !important;
}
.step-subtitle {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0 0 0.8rem 0;
    line-height: 1.55;
    font-weight: 500 !important;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Field label (above inputs) ---------- */
.field-label {
    font-size: 0.63rem;
    font-weight: 600 !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-muted);
    display: block;
    margin-bottom: 0.45rem;
    line-height: 1;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Pill-style radio buttons ---------- */
[data-testid="stRadio"] > div {
    display: flex !important;
    flex-direction: row !important;
    gap: 0.5rem !important;
    flex-wrap: wrap !important;
    align-items: center !important;
}
[data-testid="stRadio"] > div > label {
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.4rem !important;
    padding: 0.38rem 1.1rem !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 999px !important;
    cursor: pointer !important;
    font-size: 0.88rem !important;
    color: var(--text-secondary) !important;
    background: var(--bg-card) !important;
    transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease !important;
    font-family: "Cormorant Garamond", serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
}
[data-testid="stRadio"] > div > label:has(input:checked) {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #fff !important;
}
[data-testid="stRadio"] > div > label:has(input:checked) p {
    color: #fff !important;
}
[data-testid="stRadio"] > div > label > div:first-child {
    width: 8px !important;
    height: 8px !important;
    min-width: 8px !important;
    flex-shrink: 0 !important;
}

/* ---------- Empty state card ---------- */
.empty-state-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2.4rem 2rem;
    display: flex;
    align-items: center;
    gap: 1.4rem;
    box-shadow: var(--shadow-sm);
    margin-top: 0.5rem;
}
.empty-state-badge {
    width: 52px;
    height: 52px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.empty-state-badge img { width: 24px; height: 24px; display: block; }
.empty-state-title {
    font-size: 1.25rem;
    font-weight: 600 !important;
    color: var(--text-primary);
    margin: 0 0 0.3rem 0;
    font-family: "Cormorant Garamond", serif !important;
}
.empty-state-sub {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0;
    line-height: 1.55;
    font-family: "Cormorant Garamond", serif !important;
}

/* ---------- Sidebar logo ---------- */
[data-testid="stSidebarHeader"] {
    padding: 1rem 1rem 0.4rem 1rem !important;
}
[data-testid="stSidebarHeader"] img {
    border-radius: 10px !important;
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
}

/* Hide Streamlit branding */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }

/* Hide sidebar collapse button icon text (Material Symbols ligature fallback) */
[data-testid="stSidebarCollapseButton"] span,
[data-testid="collapsedControl"] span {
    font-size: 0 !important;
    visibility: hidden !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    opacity: 0.4;
    transition: opacity 0.2s ease;
}
[data-testid="stSidebarCollapseButton"]:hover,
[data-testid="collapsedControl"]:hover {
    opacity: 1;
}
</style>
"""


def inject_css() -> None:
    """Inject the global CSS once per page."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    """Render a styled page header."""
    st.markdown(
        f"""
        <h1 class="dashboard-title">{title}</h1>
        <p class="dashboard-subtitle">{subtitle}</p>
        """,
        unsafe_allow_html=True,
    )


def status_banner(kind: str, message: str) -> None:
    cls = {"ok": "ok", "warn": "warn", "err": "err"}.get(kind, "")
    st.markdown(
        f'<div class="status-banner {cls}">{message}</div>',
        unsafe_allow_html=True,
    )


def metric_pill(label: str, value: str) -> None:
    st.markdown(
        f'<div class="metric-pill"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def sidebar_extras(
    model_name: str = "Hybrid v2.4",
    region: str = "EU · London",
    user_id: str | None = None,
    processed_ok: bool | None = None,
    models_ok: bool | None = None,
    meta: dict | None = None,
) -> None:
    """Inject the WORKSPACE section, status card, and user card into the sidebar."""
    def _icon(body: str) -> str:
        return (
            f'<svg width="15" height="15" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" style="flex-shrink:0">{body}</svg>'
        )

    dataset_icon  = _icon('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>')
    pipeline_icon = _icon('<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M11 18H8a2 2 0 0 1-2-2V9"/>')
    settings_icon = _icon('<circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>')

    uid = user_id or ""
    avatar_label = uid[:2].upper() if uid else "DR"
    display_name = (uid[:8] + "…") if uid else "Guest"

    # Optional system-status rows
    def _status_row(label: str, ok: bool, ok_val: str, fail_val: str) -> str:
        dot = "dot-green" if ok else "dot-red"
        val = ok_val if ok else fail_val
        return (
            f'<div class="sidebar-status-row">'
            f'<span class="sidebar-status-key"><span class="{dot}">&#9679;</span>&nbsp;{label}</span>'
            f'<span class="sidebar-status-val">{val}</span>'
            f'</div>'
        )

    _data_row = (
        _status_row("DATA", processed_ok, "Ready", "Missing")
        if processed_ok is not None else ""
    )
    n_users = (meta or {}).get("n_users", "?")
    n_biz   = (meta or {}).get("n_businesses", "?")
    _models_row = (
        _status_row("MODELS", models_ok, f"{n_biz} restaurants", "Missing")
        if models_ok is not None else ""
    )

    st.sidebar.markdown(
        f"""
        <span class="sidebar-group-label">WORKSPACE</span>
        <div class="sidebar-ws-wrap">
          <div class="sidebar-ws-item">{dataset_icon} Dataset</div>
          <div class="sidebar-ws-item">{pipeline_icon} Pipelines</div>
          <div class="sidebar-ws-item">{settings_icon} Settings</div>
        </div>
        <div class="sidebar-status">
          <div class="sidebar-status-row">
            <span class="sidebar-status-key"><span class="dot-green">&#9679;</span>&nbsp;MODEL</span>
            <span class="sidebar-status-val">{model_name}</span>
          </div>
          <div class="sidebar-status-row">
            <span class="sidebar-status-key"><span class="dot-red">&#9679;</span>&nbsp;REGION</span>
            <span class="sidebar-status-val">{region}</span>
          </div>
          {_data_row}
          {_models_row}
        </div>
        <div class="sidebar-user-card">
          <div class="sidebar-user-avatar">{avatar_label}</div>
          <div>
            <div class="sidebar-user-name">{display_name}</div>
            <div class="sidebar-user-role">DRIVER &middot; PRO</div>
          </div>
          <span class="sidebar-user-arrow">&#8250;</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_logo(logo_path: "Path") -> None:
    """Display a logo at the very top of the sidebar with rounded corners."""
    if not logo_path.exists():
        return
    try:
        st.logo(str(logo_path))
    except AttributeError:
        # Streamlit < 1.35 fallback
        import base64 as _b64
        ext = logo_path.suffix.lstrip(".")
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        data = _b64.b64encode(logo_path.read_bytes()).decode()
        st.sidebar.markdown(
            f'<img src="data:image/{mime};base64,{data}" '
            f'style="width:100%;border-radius:10px;display:block;margin-bottom:0.5rem;" alt="logo"/>',
            unsafe_allow_html=True,
        )


def breadcrumb(*parts: tuple[str, bool]) -> None:
    items: list[str] = []
    for i, (label, active) in enumerate(parts):
        cls = ' class="breadcrumb-active"' if active else ""
        items.append(f"<span{cls}>{label}</span>")
        if i < len(parts) - 1:
            items.append('<span class="breadcrumb-sep">/</span>')
    st.markdown(
        f'<nav class="breadcrumb">{"".join(items)}</nav>',
        unsafe_allow_html=True,
    )


def styled_page_header(title: str, subtitle: str = "", icon_src: str = "") -> None:
    badge = (
        f'<div class="page-header-badge"><img src="{icon_src}" alt=""/></div>'
        if icon_src else ""
    )
    sub = f'<p class="page-header-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="page-header-wrap">
          {badge}
          <div>
            <h1 class="page-header-title">{title}</h1>
            {sub}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def step_header(num: str, heading: str, subtitle: str = "") -> None:
    sub = f'<p class="step-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="step-section">
          <span class="step-num">{num}</span>
          <div class="step-heading">{heading}</div>
          {sub}
        </div>
        """,
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
        f"""
        <div class="empty-state-card">
          {badge}
          <div>
            <div class="empty-state-title">{title}</div>
            {sub}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
