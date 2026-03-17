"""
Blackwater One — Market Intelligence Terminal
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

import config
from clm import render_clm
from weather_commodities import render_weather_commodities
from geoint import render_geoint
from investment_research import render_investment_research
from hedge_fund import render_hedge_fund
from market_data.loader import load_all_assets, get_latest_price_summary
from market_data.news import (
    fetch_market_news, fetch_asset_news, fetch_economic_calendar,
    format_news_for_llm, format_econ_calendar_for_llm
)
from signals.engine import compute_signals
from reasoning.llm import generate_daily_summary, explain_asset_signal, chat_with_agent
from output.logger import log_signals, load_log

import base64 as _b64_early, os as _os_early
_logo_path_early = _os_early.path.join(_os_early.path.dirname(_os_early.path.abspath(__file__)), "logo.jpeg")

st.set_page_config(
    page_title="Blackwater One",
    page_icon=_logo_path_early if _os_early.path.exists(_logo_path_early) else "♞",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS — Improved readability & visual hierarchy
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');

  :root {
    --bg-base:    #060809;
    --bg-panel:   #0b0e12;
    --bg-card:    #101418;
    --bg-hover:   #161c24;
    --border:     #1a2330;
    --border-mid: #253040;
    --gold:       #e8c97e;
    --gold-dim:   #b89a52;
    --gold-glow:  rgba(232,201,126,0.10);
    --text-pri:   #f0f4f8;
    --text-sec:   #7a8fa8;
    --text-dim:   #3d5570;
    --green:      #00d084;
    --red:        #ff4d6a;
    --amber:      #f5a623;
    --blue:       #4f9eff;
    --purple:     #9b7ff0;
    --orange:     #ff7c3a;
  }

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: var(--bg-base) !important;
    color: var(--text-pri) !important;
    font-size: 13px;
    line-height: 1.5;
  }
  #MainMenu, header, footer { display:none !important; }
  .block-container { padding:0 !important; max-width:100% !important; }
  .stApp { background: var(--bg-base); }
  [data-testid="column"] { padding: 0 3px !important; }

  /* ── TOP BAR — Bloomberg-style black bar ── */
  .topbar {
    background: #000000;
    border-bottom: 2px solid var(--gold);
    padding: 0 20px;
    height: 48px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .topbar-logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.05rem;
    color: var(--gold);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .topbar-sep {
    width: 1px; height: 22px;
    background: #2a3040;
  }
  .topbar-sub {
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 0.12em;
    font-family: 'Space Mono', monospace;
    text-transform: uppercase;
  }
  .topbar-pill {
    background: rgba(0,208,132,0.12);
    border: 1px solid rgba(0,208,132,0.25);
    border-radius: 3px;
    padding: 2px 10px;
    font-size: 0.62rem;
    color: var(--green);
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .topbar-user {
    background: var(--gold-glow);
    border: 1px solid rgba(232,201,126,0.15);
    border-radius: 3px;
    padding: 3px 12px;
    font-size: 0.65rem;
    color: var(--gold);
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .topbar-time {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }
  .topbar-logo-img {
    height: 28px;
    width: 28px;
    object-fit: contain;
    filter: brightness(0) invert(1);
    opacity: 0.85;
  }

  /* ── SECTION HEADERS — Bloomberg ticker-bar style ── */
  .sec-hdr {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    font-weight: 700;
    color: var(--gold);
    text-transform: uppercase;
    letter-spacing: 0.20em;
    padding: 8px 0 5px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .sec-hdr::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 10px;
    background: var(--gold);
    border-radius: 1px;
    flex-shrink: 0;
  }
  .group-label {
    font-size: 0.6rem;
    font-weight: 700;
    color: var(--text-dim);
    padding: 6px 0 3px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-family: 'Space Mono', monospace;
  }

  /* ── ASSET ROWS ── */
  .asset-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 8px;
    border-radius: 3px;
    margin-bottom: 2px;
    cursor: pointer;
    transition: background 0.1s;
    border: 1px solid transparent;
    border-left: 2px solid transparent;
  }
  .asset-item:hover { background: var(--bg-hover); border-left-color: var(--text-dim); }
  .asset-item.sel   { background: var(--bg-hover); border-left-color: var(--gold); }
  .asset-sym  { font-size: 0.78rem; font-weight: 600; color: var(--text-pri); font-family: 'Space Mono', monospace; }
  .asset-name { font-size: 0.60rem; color: var(--text-dim); margin-top: 1px; }
  .asset-price-sm { font-family: 'Space Mono', monospace; font-size: 0.72rem; color: var(--text-pri); text-align:right; }
  .chg-pos { color: var(--green); font-size: 0.64rem; font-family: 'Space Mono', monospace; }
  .chg-neg { color: var(--red);   font-size: 0.64rem; font-family: 'Space Mono', monospace; }

  /* ── METRIC CARDS — terminal data box style ── */
  .metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-top: 2px solid var(--border-mid);
    border-radius: 0;
    padding: 10px 12px;
    margin-bottom: 6px;
    transition: border-top-color 0.15s;
  }
  .metric-card:hover { border-top-color: var(--gold); }
  .metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.54rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 5px;
  }
  .metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.0rem;
    font-weight: 700;
    color: var(--text-pri);
    line-height: 1.1;
  }
  .metric-sub {
    font-size: 0.62rem;
    color: var(--text-sec);
    margin-top: 3px;
  }
  .vol-low      { color: var(--green)  !important; }
  .vol-normal   { color: var(--text-sec) !important; }
  .vol-elevated { color: var(--amber)  !important; }
  .vol-extreme  { color: var(--red)    !important; }

  /* ── REGIME BADGE ── */
  .regime-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 2px;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-family: 'Space Mono', monospace;
  }
  .r-calm-uptrend     { background:rgba(0,208,132,0.10);  color:#00d084; border:1px solid rgba(0,208,132,0.25); }
  .r-volatile-uptrend { background:rgba(245,166,35,0.10); color:#f5a623; border:1px solid rgba(245,166,35,0.25); }
  .r-stress-selloff   { background:rgba(255,77,106,0.12); color:#ff4d6a; border:1px solid rgba(255,77,106,0.30); }
  .r-quiet-decline    { background:rgba(155,127,240,0.10);color:#9b7ff0; border:1px solid rgba(155,127,240,0.25); }
  .r-volatile-chop    { background:rgba(255,124,58,0.10); color:#ff7c3a; border:1px solid rgba(255,124,58,0.25); }
  .r-mixed            { background:rgba(122,143,168,0.08);color:#7a8fa8; border:1px solid rgba(122,143,168,0.20); }

  /* ── FLAG ITEMS ── */
  .flag-item {
    font-size: 0.72rem;
    padding: 6px 10px;
    border-radius: 2px;
    margin-bottom: 4px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 2px solid var(--text-dim);
    color: var(--text-sec);
    line-height: 1.45;
  }

  /* ── ASSET HEADER BOX ── */
  .asset-header {
    background: #000000;
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 0;
    padding: 12px 16px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 18px;
  }
  .asset-sym-lg {
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    font-size: 1.5rem;
    color: var(--gold);
    line-height: 1;
    letter-spacing: 0.04em;
  }
  .asset-name-lg {
    font-size: 0.66rem;
    color: var(--text-dim);
    margin-top: 4px;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.06em;
  }
  .asset-price-lg {
    font-family: 'Space Mono', monospace;
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--text-pri);
  }

  /* ── SUMMARY BOX ── */
  .summary-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 0;
    padding: 14px 16px;
    font-size: 0.78rem;
    line-height: 1.8;
    color: var(--text-sec);
    white-space: pre-wrap;
    margin-top: 4px;
    font-family: 'Inter', sans-serif;
  }

  /* ── NEWS CARDS ── */
  .news-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 0;
    border-left: 2px solid transparent;
    padding: 8px 12px;
    margin-bottom: 5px;
    transition: border-left-color 0.15s, background 0.12s;
  }
  .news-card:hover { border-left-color: var(--gold); background: var(--bg-hover); }
  .news-title {
    font-size: 0.84rem;
    font-weight: 500;
    color: var(--text-pri);
    line-height: 1.4;
    margin-bottom: 4px;
  }
  .news-title a { color: var(--text-pri) !important; text-decoration: none; }
  .news-title a:hover { color: var(--gold) !important; }
  .news-meta  { font-size: 0.60rem; color: var(--text-dim); font-family: 'Space Mono', monospace; }
  .news-tag {
    display: inline-block;
    font-size: 0.50rem;
    font-family: 'Space Mono', monospace;
    padding: 1px 5px;
    border-radius: 1px;
    margin-left: 6px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    vertical-align: middle;
  }
  .tag-political { background:rgba(155,127,240,0.15); color:#9b7ff0; }
  .tag-macro     { background:rgba(245,166,35,0.15);  color:#f5a623; }
  .tag-market    { background:rgba(0,208,132,0.12);   color:#00d084; }
  .tag-earnings  { background:rgba(79,158,255,0.15);  color:#4f9eff; }
  .tag-geopolit  { background:rgba(255,77,106,0.15);  color:#ff4d6a; }
  .tag-india     { background:rgba(255,124,58,0.15);  color:#ff7c3a; }

  /* ── ECON CALENDAR ── */
  .econ-event {
    padding: 7px 10px 7px 12px;
    border-left: 2px solid var(--border-mid);
    margin-bottom: 5px;
    font-size: 0.70rem;
    color: var(--text-sec);
    background: var(--bg-card);
    border-radius: 0;
    line-height: 1.4;
  }
  .econ-event.high   { border-left-color: #ff4d6a; }
  .econ-event.medium { border-left-color: #f5a623; }

  /* ── CHAT ── */
  .chat-header {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    background: #000;
  }
  .chat-header-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--gold);
    font-family: 'Space Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .chat-header-sub {
    font-size: 0.60rem;
    color: var(--text-dim);
    font-family: 'Space Mono', monospace;
  }
  .chat-msg-user {
    background: var(--bg-hover);
    border: 1px solid var(--border-mid);
    border-radius: 0 6px 6px 6px;
    padding: 9px 13px;
    margin-bottom: 6px;
    font-size: 0.76rem;
    color: var(--text-pri);
    line-height: 1.55;
  }
  .chat-msg-eagle {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 0 6px 6px 6px;
    padding: 9px 13px;
    margin-bottom: 6px;
    font-size: 0.76rem;
    color: var(--text-sec);
    line-height: 1.65;
  }
  .chat-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.54rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 4px;
  }
  .chat-label-eagle { color: var(--gold-dim) !important; }

  /* ── TV PANEL ── */
  .tv-panel {
    background: #000;
    border: 1px solid var(--border);
    border-radius: 0;
    overflow: hidden;
    margin-bottom: 6px;
  }
  .tv-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    padding: 6px 10px;
    background: #000;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .live-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #ff4d6a;
    display: inline-block;
    animation: livepulse 1.5s ease-in-out infinite;
  }
  @keyframes livepulse { 0%,100%{opacity:1} 50%{opacity:0.2} }
  .tv-panel iframe { display:block; width:100%; border:none; }

  /* ── BUTTONS — flat terminal style ── */
  .stButton button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-sec) !important;
    font-size: 0.70rem !important;
    border-radius: 2px !important;
    padding: 5px 10px !important;
    transition: all 0.1s !important;
    font-family: 'Space Mono', monospace !important;
    letter-spacing: 0.04em !important;
  }
  .stButton button:hover {
    border-color: var(--gold) !important;
    color: var(--gold) !important;
    background: rgba(232,201,126,0.06) !important;
  }

  /* Asset list buttons — smaller to fit long Indian index names */
  [data-testid="column"]:first-child .stButton button {
    font-size: 0.64rem !important;
    padding: 4px 6px !important;
    text-align: left !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }

  /* ── TABS ── */
  .stTabs [data-baseweb="tab-list"] { background:transparent; gap:2px; border-bottom: 1px solid var(--border); }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: var(--text-dim);
    font-size: 0.66rem;
    font-family: 'Space Mono', monospace;
    padding: 6px 14px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .stTabs [aria-selected="true"] {
    background: transparent !important;
    border-bottom: 2px solid var(--gold) !important;
    color: var(--gold) !important;
  }
  .stTabs [data-baseweb="tab-border"] { display:none; }
  .stTabs [data-baseweb="tab-panel"]  { padding: 8px 0 0; }

  /* ── TEXT INPUT ── */
  .stTextInput input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-pri) !important;
    border-radius: 2px !important;
    font-size: 0.78rem !important;
    padding: 7px 11px !important;
    font-family: 'Inter', sans-serif !important;
  }
  .stTextInput input:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 2px rgba(232,201,126,0.10) !important;
  }
  .stTextInput input::placeholder { color: var(--text-dim) !important; }

  /* ── SCROLLBAR ── */
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 2px; }

  /* ── EXPANDER ── */
  .streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    color: var(--text-sec) !important;
    font-size: 0.70rem !important;
    font-family: 'Space Mono', monospace !important;
  }

  /* ── LOGIN SCREEN ── */
  .login-outer {
    display: flex;
    justify-content: center;
    padding-top: 80px;
  }
  .login-card {
    width: 400px;
    background: #000;
    border: 1px solid var(--border-mid);
    border-top: 3px solid var(--gold);
    border-radius: 0;
    padding: 44px 40px 36px;
    box-shadow: 0 0 60px rgba(232,201,126,0.05), 0 24px 48px rgba(0,0,0,0.7);
  }
  .login-error {
    background: rgba(255,77,106,0.08);
    border: 1px solid rgba(255,77,106,0.22);
    border-radius: 2px;
    padding: 8px 12px;
    font-size: 0.70rem;
    color: #ff4d6a;
    font-family: 'Space Mono', monospace;
    text-align: center;
    margin-bottom: 14px;
  }

  hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
defaults = {
    "chat_history":    [],
    "signals":         {},
    "daily_summary":   "",
    "selected_asset":  config.FMP_ASSETS[0],
    "active_group":    "\U0001f1fa\U0001f1f8 US Markets",
    "data_loaded":     False,
    "assets_data":     {},
    "news_general":    [],
    "news_asset":      {},
    "econ_calendar":   [],
    "news_loaded":     False,
    "active_tv":       "bloomberg",
    "logged_in":       False,
    "current_user":    "",
    "login_error":     "",
    # page router
    "page":            "eagle",
    # CLM
    "clm_contracts":   [],
    "clm_extracted":   None,
    "clm_insight":     None,
    # Weather
    "wc_loaded":       False,
    "wc_weather":      {},
    "wc_commodities":  {},
    "wc_insight":      "",
    # Flight Intelligence
    "at_loaded":       False,
    "at_hub_data":     {},
    "at_insight":      "",
    "at_selected_hub": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── AUTHORIZED USERS ───────────────────────────────────────────────────────────
def _load_users():
    display_names = {
        "merwinsam01":  "Merwin Samuel",
        "sherwinsam96": "Sherwin Samuel",
        "u.tamilmaran": "Tamilmaran",
    }
    try:
        return {
            u: {"password": p, "display": display_names.get(u, u)}
            for u, p in st.secrets["users"].items()
        }
    except:
        return {}

USERS = _load_users()

# ── LOGIN WALL ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    _, cc, _ = st.columns([1, 1.1, 1])
    with cc:
        st.markdown('<div style="height:60px"></div>', unsafe_allow_html=True)

        # Logo — chess horse piece with transparent bg
        import base64, os
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.jpeg")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            st.markdown(f"""
            <div style="text-align:center;margin-bottom:16px">
              <img src="data:image/jpeg;base64,{logo_b64}"
                   style="height:72px;width:72px;object-fit:contain;
                          mix-blend-mode:lighten;filter:brightness(1.1) contrast(1.05);"
                   alt="Blackwater One"/>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:2.2rem;text-align:center;margin-bottom:16px;color:#e8c97e">♞</div>',
                        unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center;margin-bottom:28px">
          <div style="font-family:'Space Mono',monospace;font-weight:700;font-size:1.4rem;
                      color:#e8c97e;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px">
            BLACKWATER ONE
          </div>
          <div style="font-family:'Space Mono',monospace;font-size:0.55rem;color:#3d5570;
                      letter-spacing:0.28em;text-transform:uppercase;margin-bottom:18px">
            Market Intelligence Terminal
          </div>
          <div style="width:100%;height:1px;background:linear-gradient(90deg,transparent,rgba(232,201,126,0.3),transparent);margin-bottom:18px"></div>
          <div style="font-size:0.78rem;color:#7a8fa8;line-height:1.8;max-width:300px;margin:0 auto 24px;font-family:'Inter',sans-serif">
            Real-time signals across US &amp; Indian markets — momentum, volatility,
            drawdown — fused with macro news and AI-powered analysis.
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.get("login_error"):
            st.markdown(f'<div class="login-error">⚠ {st.session_state.login_error}</div>', unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("Password", placeholder="Enter your password",
                                 type="password", key="login_pass")
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

        if st.button("LOGIN →", use_container_width=True, key="login_btn"):
            u, p = username.strip(), password.strip()
            if u in USERS and USERS[u]["password"] == p:
                st.session_state.logged_in    = True
                st.session_state.current_user = USERS[u]["display"]
                st.session_state.login_error  = ""
                st.rerun()
            else:
                st.session_state.login_error = "Invalid credentials. Access denied."
                st.rerun()

        st.markdown("""
        <div style="text-align:center;margin-top:20px;font-size:0.55rem;color:#1e2a38;
                    font-family:'Space Mono',monospace;letter-spacing:0.16em">
          PRIVATE · AUTHORIZED ACCESS ONLY
        </div>""", unsafe_allow_html=True)
    st.stop()

# ── PAGE ROUTER ────────────────────────────────────────────────────────────────
if st.session_state.get("page") == "clm":
    render_clm()
    st.stop()

if st.session_state.get("page") == "weather":
    render_weather_commodities()
    st.stop()

if st.session_state.get("page") == "geoint":
    render_geoint()
    st.stop()

if st.session_state.get("page") == "globe_fullscreen":
    from geoint import render_globe_fullscreen
    render_globe_fullscreen()
    st.stop()

if st.session_state.get("page") == "investment_research":
    render_investment_research()
    st.stop()

if st.session_state.get("page") == "hedge_fund":
    render_hedge_fund()
    st.stop()

# ── HELPERS ────────────────────────────────────────────────────────────────────
def regime_class(r):
    return {"calm uptrend":"r-calm-uptrend","volatile uptrend":"r-volatile-uptrend",
            "stress selloff":"r-stress-selloff","quiet decline":"r-quiet-decline",
            "volatile chop":"r-volatile-chop"}.get(r,"r-mixed")

def vol_class(s):
    return {"low":"vol-low","normal":"vol-normal","elevated":"vol-elevated","extreme":"vol-extreme"}.get(s,"")

def fmt_pct(v, d=1):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{v*100:+.{d}f}%"

def fmt_num(v, d=2):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{v:.{d}f}"

def asset_display(sym):
    return config.INDIA_LABELS.get(sym, sym)

def news_tag(title: str):
    t = title.lower()
    if any(w in t for w in ["nifty","sensex","bse","nse","india","rupee","rbi","sebi","modi","dalal"]): return ("india","tag-india")
    if any(w in t for w in ["fed","rate","inflation","gdp","cpi","jobs","fomc","treasury","yield","recession","monetary","tariff","trade"]): return ("macro","tag-macro")
    if any(w in t for w in ["war","sanction","nato","china","russia","taiwan","conflict","military","nuclear","ceasefire"]): return ("geopolit","tag-geopolit")
    if any(w in t for w in ["earnings","revenue","profit","eps","guidance","beat","miss","quarterly"]): return ("earnings","tag-earnings")
    if any(w in t for w in ["politic","democrat","republican","vote","bill","regulation","president","congress","trump","biden","govern"]): return ("political","tag-political")
    return ("market","tag-market")

def impact_class(impact: str):
    i = str(impact).lower()
    if i in ("high","3","red"): return "high"
    if i in ("medium","moderate","2","orange","yellow"): return "medium"
    return "low"

# ── CHART THEME ────────────────────────────────────────────────────────────────
CT = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#4a6080", size=10),
    xaxis=dict(gridcolor="#1e2a38", linecolor="#1e2a38", zeroline=False,
               tickfont=dict(size=9, color="#4a6080")),
    yaxis=dict(gridcolor="#1e2a38", linecolor="#1e2a38", zeroline=False,
               tickfont=dict(size=9, color="#4a6080")),
    margin=dict(l=8, r=8, t=28, b=8),
    title_font=dict(size=11, color="#8a9bb0", family="Inter, sans-serif"),
)

def price_chart(sig):
    p = sig["_prices"].tail(120)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=p.index, y=p.values, mode="lines",
        line=dict(color="#e8c97e", width=1.8),
        fill="tozeroy", fillcolor="rgba(232,201,126,0.05)"))
    fig.update_layout(title=f"{asset_display(sig['symbol'])} · Price (120d)", **CT, height=185)
    return fig

def vol_chart(sig):
    rv = sig["_rv_series"].dropna().tail(120)
    fig = go.Figure()
    fig.add_hrect(y0=0,                  y1=config.VOL_LOW,       fillcolor="rgba(74,222,128,0.06)",  line_width=0)
    fig.add_hrect(y0=config.VOL_LOW,     y1=config.VOL_NORMAL,    fillcolor="rgba(148,163,184,0.04)", line_width=0)
    fig.add_hrect(y0=config.VOL_NORMAL,  y1=config.VOL_ELEVATED,  fillcolor="rgba(251,191,36,0.06)",  line_width=0)
    fig.add_hrect(y0=config.VOL_ELEVATED,y1=1.0,                  fillcolor="rgba(248,113,113,0.08)", line_width=0)
    fig.add_trace(go.Scatter(x=rv.index, y=rv.values, mode="lines",
        line=dict(color="#fb923c", width=1.6)))
    fig.update_layout(title="Realized Volatility (20d, ann.)", **CT, height=165)
    return fig

def momentum_chart(sig):
    z = sig["_z_series"].dropna().tail(120)
    colors = ["#4ade80" if v > 0 else "#f87171" for v in z.values]
    fig = go.Figure()
    fig.add_hline(y=1,  line=dict(color="rgba(74,222,128,0.35)",  dash="dash", width=1))
    fig.add_hline(y=-1, line=dict(color="rgba(248,113,113,0.35)", dash="dash", width=1))
    fig.add_hline(y=0,  line=dict(color="#1e2a38", width=1))
    fig.add_trace(go.Bar(x=z.index, y=z.values, marker_color=colors, opacity=0.85))
    fig.update_layout(title="Momentum Z-Score (20d)", **CT, height=165)
    return fig

def drawdown_chart(sig):
    dd = sig["_dd_series"].tail(120)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dd.index, y=dd.values * 100, mode="lines",
        line=dict(color="#a78bfa", width=1.6),
        fill="tozeroy", fillcolor="rgba(167,139,250,0.07)"))
    fig.update_layout(title="Drawdown % (60d rolling max)", **CT, height=165)
    return fig

def correlation_heatmap(signals_dict):
    syms = [s for s, v in signals_dict.items() if v and "_rets" in v]
    if len(syms) < 2: return None
    rets = pd.concat({s: signals_dict[s]["_rets"].tail(60) for s in syms}, axis=1).dropna()
    if rets.empty: return None
    corr = rets.corr().round(2)
    # Use display labels
    labels = [asset_display(s) for s in corr.columns]
    fig = go.Figure(data=go.Heatmap(
        z=corr.values, x=labels, y=labels,
        colorscale=[[0,"#131920"],[0.5,"#1e2a38"],[1,"#e8c97e"]],
        text=corr.values, texttemplate="%{text:.2f}",
        textfont=dict(size=9, color="#eef2f7"),
        showscale=False, zmin=-1, zmax=1,
    ))
    fig.update_layout(title="Cross-Asset Correlation (60d)", **CT, height=210)
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
import base64 as _b64, os as _os
_logo_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logo.jpeg")
_logo_html = ""
if _os.path.exists(_logo_path):
    with open(_logo_path, "rb") as _f:
        _logo_b64 = _b64.b64encode(_f.read()).decode()
    _logo_html = (f'<img src="data:image/jpeg;base64,{_logo_b64}" class="topbar-logo-img" '
                  f'style="mix-blend-mode:lighten;filter:brightness(1.1);" alt="BW"/>')
else:
    _logo_html = '<span style="font-size:1.1rem;color:#e8c97e">♞</span>'

st.markdown(f"""
<div class="topbar">
  {_logo_html}
  <span class="topbar-logo">Blackwater One</span>
  <div class="topbar-sep"></div>
  <span class="topbar-sub">Market Intelligence Terminal</span>
  <div style="flex:1"></div>
  <span class="topbar-pill">● Live</span>
  <span class="topbar-time">{datetime.now().strftime("%d %b %Y · %H:%M")}</span>
  <span class="topbar-user">▲ {st.session_state.current_user}</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 4-COLUMN LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
col_assets, col_charts, col_news, col_media = st.columns([0.9, 2.1, 1.2, 1.3], gap="small")

# ══════════════════════════════════════════════════════════════════════════════
# COL 1 — Assets
# ══════════════════════════════════════════════════════════════════════════════
with col_assets:
    st.markdown('<div style="padding:12px 8px 0">', unsafe_allow_html=True)

    # Refresh + Logout
    rb, lb = st.columns([3, 1])
    with rb:
        refresh = st.button("⟳ Refresh", use_container_width=True)
    with lb:
        if st.button("↩", use_container_width=True, key="logout_btn"):
            st.session_state.logged_in    = False
            st.session_state.current_user = ""
            st.rerun()

    if refresh:
        st.cache_data.clear()
        for k in ["data_loaded","signals","daily_summary","news_general","news_asset","econ_calendar","news_loaded"]:
            if k in ("news_general","econ_calendar"): st.session_state[k] = []
            elif k == "news_asset":                   st.session_state[k] = {}
            elif k in ("data_loaded","news_loaded"):  st.session_state[k] = False
            elif k == "daily_summary":                st.session_state[k] = ""
            else:                                     st.session_state[k] = {}
        st.rerun()

    # ── Load market data ───────────────────────────────────────────────────────
    if not st.session_state.data_loaded:
        with st.spinner("Loading market data…"):
            assets_data = load_all_assets(days=252)
            st.session_state.assets_data = assets_data
        if assets_data:
            peer_rets = (
                assets_data["SPY"]["returns"]
                if "SPY" in assets_data and not assets_data["SPY"].empty
                else None
            )
            sigs = {}
            for sym, df in assets_data.items():
                peer = None if sym in ("SPY", "^NSEI", "^BSESN") else peer_rets
                try:
                    s = compute_signals(sym, df, peer)
                    if s:
                        sigs[sym] = s
                except Exception as e:
                    print(f"[signals] {sym} failed: {e}")
            st.session_state.signals     = sigs
            st.session_state.data_loaded = True
            if st.session_state.selected_asset not in sigs:
                st.session_state.selected_asset = next(iter(sigs), config.FMP_ASSETS[0])
        else:
            # Data failed to load — show actionable error
            st.error(
                "⚠️ Market data failed to load. "
                "Check your FMP API key in Streamlit secrets, then click ⟳ Refresh."
            )

    # ── Load news ──────────────────────────────────────────────────────────────
    if not st.session_state.news_loaded and st.session_state.data_loaded:
        with st.spinner("Fetching news..."):
            st.session_state.news_general  = fetch_market_news(limit=30)
            st.session_state.econ_calendar = fetch_economic_calendar(days_ahead=7)
            for sym in list(st.session_state.assets_data.keys()):
                st.session_state.news_asset[sym] = fetch_asset_news(sym, limit=6)
            st.session_state.news_loaded = True
        if not st.session_state.daily_summary and st.session_state.signals:
            with st.spinner("Generating brief..."):
                news_ctx = format_news_for_llm(st.session_state.news_general, 15)
                econ_ctx = format_econ_calendar_for_llm(st.session_state.econ_calendar, 8)
                summary  = generate_daily_summary(st.session_state.signals, news_ctx, econ_ctx)
                st.session_state.daily_summary = summary
                log_signals(st.session_state.signals, summary)

    signals       = st.session_state.signals
    price_summary = get_latest_price_summary(st.session_state.assets_data) if st.session_state.assets_data else {}

    # ── Asset groups ───────────────────────────────────────────────────────────
    for group_name, group_syms in config.ASSET_GROUPS.items():
        loaded_syms = [s for s in group_syms if s in signals or s in price_summary]
        if not loaded_syms:
            continue
        st.markdown(f'<div class="group-label">{group_name}</div>', unsafe_allow_html=True)
        for sym in loaded_syms:
            sig    = signals.get(sym, {})
            ps     = price_summary.get(sym, {})
            price  = ps.get("price", 0)
            chg    = ps.get("change_pct", 0)
            is_sel = sym == st.session_state.selected_asset
            chg_cl = "chg-pos" if chg >= 0 else "chg-neg"
            chg_arrow = "▲" if chg >= 0 else "▼"
            display = asset_display(sym)

            if st.button(
                f"{'▶ ' if is_sel else ''}{display}",
                key=f"ab_{sym}", use_container_width=True
            ):
                st.session_state.selected_asset = sym
                st.rerun()

            is_indian = sym.startswith("^")
            price_fmt = f"₹{price:,.2f}" if is_indian else f"${price:,.2f}"
            st.markdown(f"""
            <div style="padding:1px 10px 6px;margin-bottom:2px;border-bottom:1px solid #0b0e12">
              <span style="font-family:'Space Mono',monospace;font-size:0.72rem;color:#f0f4f8">
                {price_fmt}
              </span>
              <span class="{chg_cl}" style="margin-left:8px">{chg_arrow} {abs(chg*100):.2f}%</span>
            </div>""", unsafe_allow_html=True)

    # ── Active flags ───────────────────────────────────────────────────────────
    st.markdown('<div class="sec-hdr">Active Flags</div>', unsafe_allow_html=True)
    all_flags = [
        (sym, f) for sym, sig in signals.items() if sig
        for f in sig.get("risk_flags", []) if "✅" not in f
    ]
    if all_flags:
        for sym, f in all_flags[:6]:
            st.markdown(
                f'<div class="flag-item"><span style="color:#e8c97e;font-weight:600">{asset_display(sym)}</span> — {f}</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown('<div class="flag-item" style="color:#4ade80">✅ No active risk flags</div>',
                    unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COL 2 — Charts + Signals
# ══════════════════════════════════════════════════════════════════════════════
with col_charts:
    st.markdown('<div style="padding:12px 10px 0 4px">', unsafe_allow_html=True)

    selected = st.session_state.selected_asset
    sig = signals.get(selected, {})
    ps  = price_summary.get(selected, {})

    if not sig:
        st.info("Loading signals…")
    else:
        regime    = sig.get("market_regime", "mixed")
        chg       = ps.get("change_pct", 0)
        chg_color = "#4ade80" if chg >= 0 else "#f87171"
        chg_arrow = "▲" if chg >= 0 else "▼"
        display   = asset_display(selected)
        currency  = "₹" if selected.startswith("^") else "$"

        # ── Asset header ──────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="asset-header">
          <div style="flex:1">
            <div class="asset-sym-lg">{display}</div>
            <div class="asset-name-lg">{selected} · Updated {sig.get('date','—')}</div>
          </div>
          <div style="text-align:right">
            <div class="asset-price-lg">{currency}{sig.get('price', 0):,.2f}</div>
            <div style="color:{chg_color};font-size:0.78rem;margin-top:3px;font-family:'Space Mono',monospace">
              {chg_arrow} {abs(chg*100):.2f}% today
            </div>
          </div>
          <span class="regime-badge {regime_class(regime)}">{regime}</span>
        </div>
        """, unsafe_allow_html=True)

        # ── Scorecard ─────────────────────────────────────────────────────────
        m1, m2, m3, m4, m5 = st.columns(5)
        for col_m, label, value, sub in [
            (m1, "Momentum 20d", fmt_pct(sig.get("momentum_20d")), ""),
            (m2, "Mom Z-Score",  fmt_num(sig.get("momentum_zscore")), ""),
            (m3, "Realized Vol", fmt_pct(sig.get("vol_20d_ann")),
             f'<span class="{vol_class(sig.get("vol_state",""))}">{sig.get("vol_state","—")}</span>'),
            (m4, "Max DD 60d",   fmt_pct(sig.get("max_drawdown_60d")), ""),
            (m5, "Corr to Peer", fmt_num(sig.get("corr_to_peer")), sig.get("corr_state","—")),
        ]:
            with col_m:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-label">{label}</div>
                  <div class="metric-value">{value}</div>
                  <div class="metric-sub">{sub}</div>
                </div>""", unsafe_allow_html=True)

        # ── Chart tabs ────────────────────────────────────────────────────────
        t1, t2, t3, t4 = st.tabs(["Price", "Volatility", "Momentum", "Drawdown"])
        with t1: st.plotly_chart(price_chart(sig),    use_container_width=True, config={"displayModeBar": False})
        with t2: st.plotly_chart(vol_chart(sig),      use_container_width=True, config={"displayModeBar": False})
        with t3: st.plotly_chart(momentum_chart(sig), use_container_width=True, config={"displayModeBar": False})
        with t4: st.plotly_chart(drawdown_chart(sig), use_container_width=True, config={"displayModeBar": False})

        # ── Risk flags ────────────────────────────────────────────────────────
        st.markdown(f'<div class="sec-hdr" style="margin-top:12px">Risk Flags — {display}</div>', unsafe_allow_html=True)
        for f in sig.get("risk_flags", []):
            st.markdown(f'<div class="flag-item">{f}</div>', unsafe_allow_html=True)

        # ── Eagle Daily Summary (collapsed) ───────────────────────────────────
        with st.expander("📋 Eagle Daily Summary", expanded=False):
            if st.session_state.daily_summary:
                st.markdown(f'<div class="summary-box">{st.session_state.daily_summary}</div>', unsafe_allow_html=True)
            else:
                st.info("No summary yet — click Refresh.")

        if st.button(f"🔍 Deep-dive: {display}", use_container_width=True):
            news_fmt = format_news_for_llm(
                st.session_state.news_asset.get(selected, []) + st.session_state.news_general[:5], 10)
            with st.spinner("Analyzing..."):
                expl = explain_asset_signal(sig, news_context=news_fmt)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": f"**Deep-dive: {display}**\n\n{expl}"}
                )
            st.rerun()

    with st.expander("📋 Signal History", expanded=False):
        log_df = load_log()
        if not log_df.empty:
            cols  = ["date","symbol","momentum_regime","vol_state","market_regime","risk_flags"]
            avail = [c for c in cols if c in log_df.columns]
            st.dataframe(log_df[avail].tail(50).sort_values("date", ascending=False),
                         use_container_width=True, height=180)
        else:
            st.caption("No history yet.")

    # ── Economic Calendar ──────────────────────────────────────────────────────
    st.markdown('<div class="sec-hdr" style="margin-top:14px">Economic Calendar — 7 Days</div>', unsafe_allow_html=True)
    for ev in st.session_state.econ_calendar[:14]:
        name    = ev.get("event", ev.get("name", ""))
        date    = str(ev.get("date", ""))[:10]
        impact  = ev.get("impact", ev.get("importance", ""))
        actual  = ev.get("actual", "")
        est     = ev.get("estimate", ev.get("consensus", ""))
        country = ev.get("country", "")
        ic      = impact_class(str(impact))
        imp_color = {"high": "#f87171", "medium": "#fbbf24", "low": "#4a6080"}.get(ic, "#4a6080")
        st.markdown(f"""
        <div class="econ-event {ic}">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="color:#eef2f7;font-weight:500;font-size:0.74rem">{name}</span>
            <span style="color:{imp_color};font-size:0.65rem;white-space:nowrap;margin-left:8px">● {impact}</span>
          </div>
          <div style="color:#4a6080;font-size:0.65rem;margin-top:3px">
            {date}{f' · {country}' if country else ''}
            {f' <span style="color:#8a9bb0">· est {est}</span>' if est else ''}
            {f' <span style="color:#e8c97e">· act {actual}</span>' if actual else ''}
          </div>
        </div>""", unsafe_allow_html=True)
    if not st.session_state.econ_calendar:
        st.caption("No upcoming events loaded.")

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COL 3 — Chat + News + Calendar
# ══════════════════════════════════════════════════════════════════════════════
with col_news:
    st.markdown('<div style="padding:12px 8px 0 4px">', unsafe_allow_html=True)

    # ── Eagle Chat ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="chat-header">
      <span style="font-size:1rem">🦅</span>
      <div>
        <div class="chat-header-title">Eagle Agent</div>
        <div class="chat-header-sub">news-aware · signal-grounded</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown("""
        <div style="font-size:0.78rem;color:#4a6080;line-height:2;padding:4px 2px">
          Eagle is ready. Ask about:<br>
          <span style="color:#8a9bb0">· Market regimes &amp; signals</span><br>
          <span style="color:#8a9bb0">· How news connects to data</span><br>
          <span style="color:#8a9bb0">· Indian vs US market dynamics</span><br>
          <span style="color:#8a9bb0">· Geopolitical &amp; macro risk</span><br>
          <span style="color:#8a9bb0">· Upcoming economic events</span><br>
          <span style="color:#2a3548;font-size:0.7rem">No trade recommendations · No price predictions</span>
        </div>""", unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_history[-14:]:
            content = msg["content"].replace("\n", "<br>")
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-msg-user">
                  <div class="chat-label">You</div>
                  {content}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-msg-eagle">
                  <div class="chat-label chat-label-eagle">Eagle</div>
                  {content}
                </div>""", unsafe_allow_html=True)

    user_input = st.text_input("Message Eagle", placeholder="Ask about markets or news...",
                               label_visibility="collapsed", key="chat_input")
    sc, cc2 = st.columns([3, 1])
    with sc:
        send = st.button("Send →", use_container_width=True, key="send_btn")
    with cc2:
        if st.button("Clear", use_container_width=True, key="clear_btn"):
            st.session_state.chat_history = []
            st.rerun()

    if send and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
        with st.spinner("Eagle thinking..."):
            reply = chat_with_agent(
                st.session_state.chat_history, st.session_state.signals,
                news_context=format_news_for_llm(st.session_state.news_general, 12),
                econ_context=format_econ_calendar_for_llm(st.session_state.econ_calendar),
            )
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # ── News Feed ──────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-hdr">Latest Headlines</div>', unsafe_allow_html=True)
    asset_headlines = st.session_state.news_asset.get(selected, [])
    all_news = asset_headlines[:4] + [n for n in st.session_state.news_general if n not in asset_headlines]
    for item in all_news[:16]:
        title  = item.get("title", item.get("headline", ""))
        date   = str(item.get("publishedDate", item.get("date", "")))[:10]
        source = item.get("site", item.get("source", ""))
        url    = item.get("url", "#")
        if not title: continue
        tag_name, tag_cls = news_tag(title)
        st.markdown(f"""
        <div class="news-card">
          <div class="news-title">
            <a href="{url}" target="_blank">{title}</a>
            <span class="news-tag {tag_cls}">{tag_name}</span>
          </div>
          <div class="news-meta">{date} · {source}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COL 4 — Live TV + News Synthesis + Blackwater Tools
# ══════════════════════════════════════════════════════════════════════════════
with col_media:
    st.markdown('<div style="padding:12px 8px 0 4px">', unsafe_allow_html=True)

    st.markdown('<div class="sec-hdr">Live Market TV</div>', unsafe_allow_html=True)

    tv1, tv2 = st.columns(2)
    with tv1:
        if st.button("📺 Bloomberg", use_container_width=True, key="tv_b"):
            st.session_state.active_tv = "bloomberg"
    with tv2:
        if st.button("📺 Al Jazeera", use_container_width=True, key="tv_a"):
            st.session_state.active_tv = "aljazeera"

    active      = st.session_state.active_tv
    main_label  = "BLOOMBERG LIVE"     if active == "bloomberg" else "AL JAZEERA LIVE"
    main_embed  = ("https://www.youtube.com/embed/iEpJwprxDdk?autoplay=1&mute=1" if active == "bloomberg"
                   else "https://www.youtube.com/embed/gCNeDWCI0vo?autoplay=1&mute=1")
    other_label = "AL JAZEERA · MUTED" if active == "bloomberg" else "BLOOMBERG · MUTED"
    other_embed = ("https://www.youtube.com/embed/gCNeDWCI0vo?mute=1" if active == "bloomberg"
                   else "https://www.youtube.com/embed/iEpJwprxDdk?mute=1")

    st.markdown(
        f'<div class="tv-panel" style="margin-top:6px">'
        f'<div class="tv-label"><span class="live-dot"></span>{main_label}</div>'
        f'<iframe src="{main_embed}" height="195"'
        ' allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"'
        ' allowfullscreen></iframe></div>'
        f'<div class="tv-panel">'
        f'<div class="tv-label" style="color:#4a6080">'
        '<span style="width:5px;height:5px;border-radius:50%;background:#4a6080;display:inline-block"></span>'
        f'{other_label}</div>'
        f'<iframe src="{other_embed}" height="145"'
        ' allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"'
        ' allowfullscreen></iframe></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-hdr" style="margin-top:10px">News × Signal Link</div>', unsafe_allow_html=True)
    if st.button("🔗 Connect News to Signals", use_container_width=True, key="synth_btn"):
        news_fmt = format_news_for_llm(
            st.session_state.news_asset.get(selected, []) + st.session_state.news_general, 12)
        with st.spinner("Eagle connecting dots..."):
            synthesis = explain_asset_signal(signals.get(selected, {}), news_context=news_fmt)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"**News synthesis for {asset_display(selected)}:**\n\n{synthesis}"}
        )
        st.markdown(
            f'<div style="background:#131920;border:1px solid #1e2a38;border-left:3px solid #a78bfa;'
            'border-radius:0 10px 10px 0;padding:14px 16px;font-size:0.78rem;line-height:1.75;'
            f'color:#8a9bb0;white-space:pre-wrap;margin-top:8px">{synthesis}</div>',
            unsafe_allow_html=True,
        )

    # ── Blackwater Tools ────────────────────────────────────────────────────
    st.markdown('<div class="sec-hdr" style="margin-top:10px">Blackwater Tools</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    if st.button("🏦 Hedge Fund", use_container_width=True, key="open_hf"):
        st.session_state.page = "hedge_fund"
        st.rerun()

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    if st.button("🔬 Investment Research", use_container_width=True, key="open_ir"):
        st.session_state.page = "investment_research"
        st.rerun()

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    if st.button("⚖️ Blackwater Legal", use_container_width=True, key="open_clm"):
        st.session_state.page = "clm"
        st.rerun()

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    if st.button("🌦 Weather Intelligence", use_container_width=True, key="open_weather"):
        st.session_state.page = "weather"
        st.rerun()



    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    if st.button("🌍 Geopolitical Intelligence", use_container_width=True, key="open_geoint"):
        st.session_state.page = "geoint"
        st.session_state.gi_loaded = False
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
