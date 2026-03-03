"""
Eagle by Blackwater — Market Monitoring & Signal Interpretation System
US + Indian Markets | 4-column layout | Improved readability
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
from market_data.loader import load_all_assets, get_latest_price_summary
from market_data.news import (
    fetch_market_news, fetch_asset_news, fetch_economic_calendar,
    format_news_for_llm, format_econ_calendar_for_llm
)
from signals.engine import compute_signals
from reasoning.llm import generate_daily_summary, explain_asset_signal, chat_with_agent
from output.logger import log_signals, load_log

st.set_page_config(
    page_title="Eagle by Blackwater",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS — Improved readability & visual hierarchy
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');

  :root {
    --bg-base:    #090b0e;
    --bg-panel:   #0e1218;
    --bg-card:    #131920;
    --bg-hover:   #1a2230;
    --border:     #1e2a38;
    --border-mid: #2a3a4e;
    --gold:       #e8c97e;
    --gold-dim:   #b89a52;
    --gold-glow:  rgba(232,201,126,0.12);
    --text-pri:   #eef2f7;
    --text-sec:   #8a9bb0;
    --text-dim:   #4a6080;
    --green:      #4ade80;
    --red:        #f87171;
    --amber:      #fbbf24;
    --blue:       #60a5fa;
    --purple:     #a78bfa;
    --orange:     #fb923c;
  }

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: var(--bg-base) !important;
    color: var(--text-pri) !important;
    font-size: 14px;
    line-height: 1.5;
  }
  #MainMenu, header, footer { display:none !important; }
  .block-container { padding:0 !important; max-width:100% !important; }
  .stApp { background: var(--bg-base); }
  [data-testid="column"] { padding: 0 4px !important; }

  /* ── TOP BAR ── */
  .topbar {
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    height: 52px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 1px 0 var(--border);
  }
  .topbar-logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.15rem;
    color: var(--gold);
    letter-spacing: 0.03em;
  }
  .topbar-sep {
    width: 1px; height: 24px;
    background: var(--border-mid);
  }
  .topbar-sub {
    font-size: 0.72rem;
    color: var(--text-dim);
    letter-spacing: 0.08em;
    font-family: 'Space Mono', monospace;
  }
  .topbar-user {
    background: var(--gold-glow);
    border: 1px solid rgba(232,201,126,0.20);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.72rem;
    color: var(--gold);
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.05em;
  }
  .topbar-time {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-dim);
  }

  /* ── SECTION HEADERS ── */
  .sec-hdr {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    padding: 10px 0 6px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 10px;
  }
  .group-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-sec);
    padding: 8px 0 4px;
    letter-spacing: 0.05em;
  }

  /* ── ASSET ROWS ── */
  .asset-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 10px;
    border-radius: 7px;
    margin-bottom: 3px;
    cursor: pointer;
    transition: background 0.15s;
    border: 1px solid transparent;
  }
  .asset-item:hover { background: var(--bg-hover); border-color: var(--border); }
  .asset-item.sel   { background: var(--bg-hover); border-color: rgba(232,201,126,0.25); }
  .asset-sym  { font-size: 0.82rem; font-weight: 600; color: var(--text-pri); }
  .asset-name { font-size: 0.66rem; color: var(--text-dim); margin-top: 1px; }
  .asset-price-sm { font-family: 'Space Mono', monospace; font-size: 0.78rem; color: var(--text-pri); text-align:right; }
  .chg-pos { color: var(--green); font-size: 0.68rem; }
  .chg-neg { color: var(--red);   font-size: 0.68rem; }

  /* ── METRIC CARDS ── */
  .metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
    transition: border-color 0.2s, background 0.2s;
  }
  .metric-card:hover { border-color: var(--border-mid); background: var(--bg-hover); }
  .metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 6px;
  }
  .metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-pri);
    line-height: 1.1;
  }
  .metric-sub {
    font-size: 0.66rem;
    color: var(--text-sec);
    margin-top: 4px;
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
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: capitalize;
  }
  .r-calm-uptrend     { background:rgba(74,222,128,0.10); color:#4ade80; border:1px solid rgba(74,222,128,0.25); }
  .r-volatile-uptrend { background:rgba(251,191,36,0.10); color:#fbbf24; border:1px solid rgba(251,191,36,0.25); }
  .r-stress-selloff   { background:rgba(248,113,113,0.12); color:#f87171; border:1px solid rgba(248,113,113,0.30); }
  .r-quiet-decline    { background:rgba(167,139,250,0.10); color:#a78bfa; border:1px solid rgba(167,139,250,0.25); }
  .r-volatile-chop    { background:rgba(251,146,60,0.10);  color:#fb923c; border:1px solid rgba(251,146,60,0.25); }
  .r-mixed            { background:rgba(148,163,184,0.08); color:#94a3b8; border:1px solid rgba(148,163,184,0.20); }

  /* ── FLAG ITEMS ── */
  .flag-item {
    font-size: 0.75rem;
    padding: 7px 11px;
    border-radius: 7px;
    margin-bottom: 5px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-sec);
    line-height: 1.45;
  }

  /* ── ASSET HEADER BOX ── */
  .asset-header {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .asset-sym-lg {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.8rem;
    color: var(--gold);
    line-height: 1;
  }
  .asset-name-lg {
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-top: 3px;
  }
  .asset-price-lg {
    font-family: 'Space Mono', monospace;
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text-pri);
  }

  /* ── SUMMARY BOX ── */
  .summary-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 0 10px 10px 0;
    padding: 16px 18px;
    font-size: 0.82rem;
    line-height: 1.75;
    color: var(--text-sec);
    white-space: pre-wrap;
    margin-top: 4px;
  }

  /* ── NEWS CARDS ── */
  .news-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 13px;
    margin-bottom: 7px;
    transition: border-color 0.15s, background 0.15s;
  }
  .news-card:hover { border-color: var(--border-mid); background: var(--bg-hover); }
  .news-title {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-pri);
    line-height: 1.45;
    margin-bottom: 5px;
  }
  .news-title a { color: var(--text-pri) !important; text-decoration: none; }
  .news-title a:hover { color: var(--gold) !important; }
  .news-meta  { font-size: 0.65rem; color: var(--text-dim); font-family: 'Space Mono', monospace; }
  .news-tag {
    display: inline-block;
    font-size: 0.55rem;
    font-family: 'Space Mono', monospace;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 6px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    vertical-align: middle;
  }
  .tag-political { background:rgba(167,139,250,0.15); color:#a78bfa; }
  .tag-macro     { background:rgba(251,191,36,0.15);  color:#fbbf24; }
  .tag-market    { background:rgba(74,222,128,0.12);  color:#4ade80; }
  .tag-earnings  { background:rgba(96,165,250,0.15);  color:#60a5fa; }
  .tag-geopolit  { background:rgba(248,113,113,0.15); color:#f87171; }
  .tag-india     { background:rgba(251,146,60,0.15);  color:#fb923c; }

  /* ── ECON CALENDAR ── */
  .econ-event {
    padding: 8px 10px 8px 13px;
    border-left: 2px solid var(--border-mid);
    margin-bottom: 6px;
    font-size: 0.74rem;
    color: var(--text-sec);
    background: var(--bg-card);
    border-radius: 0 7px 7px 0;
    line-height: 1.4;
  }
  .econ-event.high   { border-left-color: #f87171; }
  .econ-event.medium { border-left-color: #fbbf24; }

  /* ── CHAT ── */
  .chat-header {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .chat-header-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-pri);
  }
  .chat-header-sub {
    font-size: 0.65rem;
    color: var(--text-dim);
    font-family: 'Space Mono', monospace;
  }
  .chat-msg-user {
    background: var(--bg-hover);
    border: 1px solid var(--border-mid);
    border-radius: 10px 10px 4px 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 0.8rem;
    color: var(--text-pri);
    line-height: 1.5;
  }
  .chat-msg-eagle {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 4px 10px 10px 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 0.8rem;
    color: var(--text-sec);
    line-height: 1.65;
  }
  .chat-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 5px;
  }
  .chat-label-eagle { color: var(--gold-dim) !important; }

  /* ── TV PANEL ── */
  .tv-panel {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 8px;
  }
  .tv-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 7px 12px;
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .live-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #f87171;
    display: inline-block;
    animation: livepulse 1.5s ease-in-out infinite;
  }
  @keyframes livepulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .tv-panel iframe { display:block; width:100%; border:none; }

  /* ── BUTTONS ── */
  .stButton button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-sec) !important;
    font-size: 0.75rem !important;
    border-radius: 7px !important;
    padding: 6px 12px !important;
    transition: all 0.15s !important;
    font-family: 'Inter', sans-serif !important;
  }
  .stButton button:hover {
    border-color: rgba(232,201,126,0.4) !important;
    color: var(--gold) !important;
    background: var(--bg-hover) !important;
  }

  /* ── TABS ── */
  .stTabs [data-baseweb="tab-list"] { background:transparent; gap:4px; }
  .stTabs [data-baseweb="tab"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 7px;
    color: var(--text-dim);
    font-size: 0.72rem;
    font-family: 'Inter', sans-serif;
    padding: 6px 14px;
  }
  .stTabs [aria-selected="true"] {
    background: var(--bg-hover) !important;
    border-color: rgba(232,201,126,0.35) !important;
    color: var(--gold) !important;
  }
  .stTabs [data-baseweb="tab-border"] { display:none; }
  .stTabs [data-baseweb="tab-panel"]  { padding: 8px 0 0; }

  /* ── TEXT INPUT ── */
  .stTextInput input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-pri) !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    padding: 8px 12px !important;
  }
  .stTextInput input:focus {
    border-color: rgba(232,201,126,0.5) !important;
    box-shadow: 0 0 0 3px rgba(232,201,126,0.08) !important;
  }
  .stTextInput input::placeholder { color: var(--text-dim) !important; }

  /* ── SCROLLBAR ── */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 3px; }

  /* ── EXPANDER ── */
  .streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 7px !important;
    color: var(--text-sec) !important;
    font-size: 0.75rem !important;
  }

  /* ── LOGIN SCREEN ── */
  .login-outer {
    display: flex;
    justify-content: center;
    padding-top: 80px;
  }
  .login-card {
    width: 440px;
    background: var(--bg-panel);
    border: 1px solid var(--border-mid);
    border-radius: 18px;
    padding: 48px 44px 40px;
    box-shadow: 0 0 80px rgba(232,201,126,0.07), 0 32px 64px rgba(0,0,0,0.5);
  }
  .login-glow {
    position: absolute;
    width: 200px; height: 1px;
    top: 0; left: 50%; transform: translateX(-50%);
    background: linear-gradient(90deg, transparent, rgba(232,201,126,0.5), transparent);
    border-radius: 50%;
  }
  .login-error {
    background: rgba(248,113,113,0.08);
    border: 1px solid rgba(248,113,113,0.25);
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 0.75rem;
    color: #f87171;
    text-align: center;
    margin-bottom: 16px;
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
    "active_group":    "🇺🇸 US Markets",
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
    "page":            "eagle",   # page router
    "clm_contracts":   [],        # CLM contract store
    "clm_extracted":   None,      # CLM AI extraction buffer
    "clm_insight":     None,      # CLM AI insight cache
    "wc_loaded":       False,     # Weather & Commodities data flag
    "wc_weather":      {},        # Weather cache
    "wc_commodities":  {},        # Commodity prices cache
    "wc_insight":      "",        # Weather AI insight
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
        st.markdown('<div style="font-size:3rem;text-align:center;margin-bottom:10px">🦅</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:24px">
          <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.8rem;
                      color:#e8c97e;letter-spacing:0.02em;margin-bottom:4px">
            Eagle by Blackwater
          </div>
          <div style="font-family:'Space Mono',monospace;font-size:0.62rem;color:#4a6080;
                      letter-spacing:0.2em;text-transform:uppercase;margin-bottom:20px">
            Market Intelligence Platform
          </div>
          <div style="font-size:0.85rem;color:#8a9bb0;line-height:1.75;max-width:340px;margin:0 auto 28px">
            Real-time signals across US &amp; Indian markets — momentum, volatility,
            drawdown, correlation — fused with macro news, economic calendars,
            and AI-powered daily analysis by the Eagle agent.
          </div>
          <div style="width:180px;height:1px;background:linear-gradient(90deg,transparent,rgba(232,201,126,0.4),transparent);margin:0 auto 28px"></div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.get("login_error"):
            st.markdown(f'<div class="login-error">⚠ {st.session_state.login_error}</div>', unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("Password", placeholder="Enter your password",
                                 type="password", key="login_pass")
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

        if st.button("Login →", use_container_width=True, key="login_btn"):
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
        <div style="text-align:center;margin-top:22px;font-size:0.6rem;color:#2a3548;
                    font-family:'Space Mono',monospace;letter-spacing:0.1em">
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
st.markdown(f"""
<div class="topbar">
  <span style="font-size:1.3rem">🦅</span>
  <span class="topbar-logo">Eagle by Blackwater</span>
  <div class="topbar-sep"></div>
  <span class="topbar-sub">Market Intelligence</span>
  <div style="flex:1"></div>
  <span class="topbar-time">{datetime.now().strftime("%b %d %Y · %H:%M")}</span>
  <span class="topbar-user">👤 {st.session_state.current_user}</span>
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

    if not st.session_state.data_loaded:
        with st.spinner("Loading market data..."):
            assets_data = load_all_assets(days=252)
            st.session_state.assets_data = assets_data
        if assets_data:
            peer_rets = assets_data.get("SPY", pd.DataFrame()).get("returns") if "SPY" in assets_data else None
            sigs = {}
            for sym, df in assets_data.items():
                peer = None if sym in ("SPY", "^NSEI", "^BSESN") else peer_rets
                sigs[sym] = compute_signals(sym, df, peer)
            st.session_state.signals     = sigs
            st.session_state.data_loaded = True
            if st.session_state.selected_asset not in sigs:
                st.session_state.selected_asset = next(iter(sigs), config.FMP_ASSETS[0])

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

    for group_name, group_syms in config.ASSET_GROUPS.items():
        loaded_syms = [s for s in group_syms if s in signals]
        if not loaded_syms:
            continue
        st.markdown(f'<div class="group-label">{group_name}</div>', unsafe_allow_html=True)
        for sym in loaded_syms:
            ps        = price_summary.get(sym, {})
            price     = ps.get("price", 0)
            chg       = ps.get("change_pct", 0)
            is_sel    = sym == st.session_state.selected_asset
            chg_cl    = "chg-pos" if chg >= 0 else "chg-neg"
            chg_arrow = "▲" if chg >= 0 else "▼"
            display   = asset_display(sym)

            if st.button(
                f"{'● ' if is_sel else '  '}{display}",
                key=f"ab_{sym}", use_container_width=True
            ):
                st.session_state.selected_asset = sym
                st.rerun()

            st.markdown(f"""
            <div style="padding:1px 10px 6px;margin-bottom:2px;border-bottom:1px solid #0e1218">
              <span style="font-family:'Space Mono',monospace;font-size:0.72rem;color:#eef2f7">
                ${price:,.2f}
              </span>
              <span class="{chg_cl}" style="margin-left:8px">{chg_arrow} {abs(chg*100):.2f}%</span>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-hdr" style="margin-top:14px">Correlations</div>', unsafe_allow_html=True)
    if signals:
        fig_c = correlation_heatmap(signals)
        if fig_c:
            st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})

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

        st.markdown(f"""
        <div class="asset-header">
          <div style="flex:1">
            <div class="asset-sym-lg">{display}</div>
            <div class="asset-name-lg">{selected} · Updated {sig.get('date','—')}</div>
          </div>
          <div style="text-align:right">
            <div class="asset-price-lg">${sig.get('price', 0):,.2f}</div>
            <div style="color:{chg_color};font-size:0.78rem;margin-top:3px;font-family:'Space Mono',monospace">
              {chg_arrow} {abs(chg*100):.2f}% today
            </div>
          </div>
          <span class="regime-badge {regime_class(regime)}">{regime}</span>
        </div>
        """, unsafe_allow_html=True)

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

        t1, t2, t3, t4 = st.tabs(["Price", "Volatility", "Momentum", "Drawdown"])
        with t1: st.plotly_chart(price_chart(sig),    use_container_width=True, config={"displayModeBar": False})
        with t2: st.plotly_chart(vol_chart(sig),      use_container_width=True, config={"displayModeBar": False})
        with t3: st.plotly_chart(momentum_chart(sig), use_container_width=True, config={"displayModeBar": False})
        with t4: st.plotly_chart(drawdown_chart(sig), use_container_width=True, config={"displayModeBar": False})

        st.markdown(f'<div class="sec-hdr" style="margin-top:12px">Risk Flags — {display}</div>', unsafe_allow_html=True)
        for f in sig.get("risk_flags", []):
            st.markdown(f'<div class="flag-item">{f}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-hdr" style="margin-top:14px">Eagle Daily Summary</div>', unsafe_allow_html=True)
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

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COL 3 — Chat + News + Calendar
# ══════════════════════════════════════════════════════════════════════════════
with col_news:
    st.markdown('<div style="padding:12px 8px 0 4px">', unsafe_allow_html=True)

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

    st.markdown('<div class="sec-hdr">Quick Questions</div>', unsafe_allow_html=True)
    qc = st.columns(2)
    for i, p in enumerate(["Overall regime?","Top news impact?","India vs US?",
                            "Geopolitical risk?","Macro events?","Vol comparison"]):
        with qc[i % 2]:
            if st.button(p, key=f"qp_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.spinner(""):
                    reply = chat_with_agent(
                        st.session_state.chat_history, st.session_state.signals,
                        news_context=format_news_for_llm(st.session_state.news_general, 12),
                        econ_context=format_econ_calendar_for_llm(st.session_state.econ_calendar),
                    )
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

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

    st.markdown('<div class="sec-hdr" style="margin-top:16px">Economic Calendar — 7 Days</div>', unsafe_allow_html=True)
    for ev in st.session_state.econ_calendar[:14]:
        name      = ev.get("event", ev.get("name", ""))
        date      = str(ev.get("date", ""))[:10]
        impact    = ev.get("impact", ev.get("importance", ""))
        actual    = ev.get("actual", "")
        est       = ev.get("estimate", ev.get("consensus", ""))
        country   = ev.get("country", "")
        ic        = impact_class(str(impact))
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
# COL 4 — Live TV + News Synthesis + Tools
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
    main_embed  = "https://www.youtube.com/embed/iEpJwprxDdk?autoplay=1&mute=1" if active == "bloomberg" \
                  else "https://www.youtube.com/embed/gCNeDWCI0vo?autoplay=1&mute=1"
    other_label = "AL JAZEERA · MUTED" if active == "bloomberg" else "BLOOMBERG · MUTED"
    other_embed = "https://www.youtube.com/embed/gCNeDWCI0vo?mute=1" if active == "bloomberg" \
                  else "https://www.youtube.com/embed/iEpJwprxDdk?mute=1"

    st.markdown(f"""
    <div class="tv-panel" style="margin-top:6px">
      <div class="tv-label">
        <span class="live-dot"></span>{main_label}
      </div>
      <iframe src="{main_embed}" height="195"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen></iframe>
    </div>
    <div class="tv-panel">
      <div class="tv-label" style="color:#4a6080">
        <span style="width:5px;height:5px;border-radius:50%;background:#4a6080;display:inline-block"></span>
        {other_label}
      </div>
      <iframe src="{other_embed}" height="145"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen></iframe>
    </div>
    """, unsafe_allow_html=True)

    # ── News × Signal Synthesis ────────────────────────────────────────────────
    st.markdown('<div class="sec-hdr" style="margin-top:10px">News × Signal Link</div>', unsafe_allow_html=True)
    if st.button("🔗 Connect News to Signals", use_container_width=True, key="synth_btn"):
        news_fmt = format_news_for_llm(
            st.session_state.news_asset.get(selected, []) + st.session_state.news_general, 12)
        with st.spinner("Eagle connecting dots..."):
            synthesis = explain_asset_signal(signals.get(selected, {}), news_context=news_fmt)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"**News synthesis for {asset_display(selected)}:**\n\n{synthesis}"}
        )
        st.markdown(f"""
        <div style="background:#131920;border:1px solid #1e2a38;border-left:3px solid #a78bfa;
             border-radius:0 10px 10px 0;padding:14px 16px;font-size:0.78rem;line-height:1.75;
             color:#8a9bb0;white-space:pre-wrap;margin-top:8px">
          {synthesis}
        </div>""", unsafe_allow_html=True)

    # ── Blackwater Tools ───────────────────────────────────────────────────────
    st.markdown('<div class="sec-hdr" style="margin-top:10px">Blackwater Tools</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    if st.button("⚖️ Blackwater Legal", use_container_width=True, key="open_clm"):
        st.session_state.page = "clm"
        st.rerun()

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    if st.button("🌍 Weather Intelligence", use_container_width=True, key="open_weather"):
        st.session_state.page = "weather"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
