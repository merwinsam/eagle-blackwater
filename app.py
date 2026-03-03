"""
Eagle by Blackwater — Market Monitoring & Signal Interpretation System
4-column layout: Assets | Charts+Signals | News+Econ | LiveTV+Chat
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

import config
from market_data.loader import load_all_assets, get_latest_price_summary
from market_data.news import (
    fetch_market_news, fetch_asset_news, fetch_economic_calendar,
    format_news_for_llm, format_econ_calendar_for_llm
)
from signals.engine import compute_signals
from reasoning.llm import generate_daily_summary, explain_asset_signal, chat_with_agent
from output.logger import log_signals, load_log

st.set_page_config(
    page_title="Eagle | Blackwater",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

  html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background: #0a0c0f !important;
    color: #e0e4ea !important;
  }
  #MainMenu, header, footer { display: none !important; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  .stApp { background: #0a0c0f; }

  .eagle-topbar {
    background: #0d1117;
    border-bottom: 1px solid #1e2530;
    padding: 10px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .eagle-logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.3rem;
    color: #e8c97e;
    letter-spacing: 0.05em;
  }
  .eagle-sub {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: #4a5568;
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }
  .metric-card {
    background: #0d1117;
    border: 1px solid #1e2530;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 7px;
    transition: border-color 0.2s;
  }
  .metric-card:hover { border-color: rgba(232,201,126,0.35); }
  .metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    color: #4a6080;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 3px;
  }
  .metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.0rem;
    font-weight: 700;
    color: #e0e4ea;
  }
  .regime-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .regime-calm-uptrend    { background:#0d2b1a; color:#4ade80; border:1px solid rgba(74,222,128,0.30); }
  .regime-volatile-uptrend{ background:#2b1f0d; color:#fbbf24; border:1px solid rgba(251,191,36,0.30); }
  .regime-stress-selloff  { background:#2b0d0d; color:#f87171; border:1px solid rgba(248,113,113,0.30); }
  .regime-quiet-decline   { background:#1a1a2b; color:#a78bfa; border:1px solid rgba(167,139,250,0.30); }
  .regime-volatile-chop   { background:#2b1f0d; color:#fb923c; border:1px solid rgba(251,146,60,0.30); }
  .regime-mixed           { background:#1a2030; color:#94a3b8; border:1px solid rgba(148,163,184,0.30); }
  .vol-low      { color: #4ade80; }
  .vol-normal   { color: #94a3b8; }
  .vol-elevated { color: #fbbf24; }
  .vol-extreme  { color: #f87171; }
  .section-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    color: #4a6080;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    padding: 7px 0 4px 0;
    border-bottom: 1px solid #1e2530;
    margin-bottom: 8px;
  }
  .stButton button {
    background: #0d1117 !important;
    border: 1px solid #1e2530 !important;
    color: #94a3b8 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.68rem !important;
    border-radius: 6px !important;
    transition: all 0.15s !important;
  }
  .stButton button:hover {
    border-color: rgba(232,201,126,0.55) !important;
    color: #e8c97e !important;
  }
  .chat-msg-user {
    background: #1a2030;
    border: 1px solid #2a3548;
    border-radius: 8px;
    padding: 9px 12px;
    margin-bottom: 8px;
    font-size: 0.78rem;
    color: #c8d4e4;
  }
  .chat-msg-eagle {
    background: #0f1922;
    border: 1px solid #1e3048;
    border-left: 3px solid #e8c97e;
    border-radius: 8px;
    padding: 9px 12px;
    margin-bottom: 8px;
    font-size: 0.78rem;
    color: #d0dcea;
    line-height: 1.6;
  }
  .chat-msg-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.52rem;
    color: #4a6080;
    text-transform: uppercase;
    margin-bottom: 3px;
    letter-spacing: 0.1em;
  }
  .flag-item {
    font-size: 0.72rem;
    padding: 5px 9px;
    border-radius: 6px;
    margin-bottom: 4px;
    background: #0f1520;
    border: 1px solid #1e2530;
    font-family: 'Space Mono', monospace;
    line-height: 1.4;
  }

  /* News cards */
  .news-card {
    background: #0d1117;
    border: 1px solid #1e2530;
    border-radius: 6px;
    padding: 9px 11px;
    margin-bottom: 6px;
    transition: border-color 0.15s;
  }
  .news-card:hover { border-color: rgba(232,201,126,0.25); }
  .news-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    color: #c8d4e4;
    line-height: 1.4;
    margin-bottom: 4px;
  }
  .news-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.56rem;
    color: #4a6080;
  }
  .news-tag {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 0.5rem;
    padding: 1px 5px;
    border-radius: 3px;
    margin-left: 5px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    vertical-align: middle;
  }
  .tag-political  { background:#1a1a2b; color:#a78bfa; }
  .tag-macro      { background:#1f1a0d; color:#fbbf24; }
  .tag-market     { background:#0d2b1a; color:#4ade80; }
  .tag-earnings   { background:#0d1f2b; color:#38bdf8; }
  .tag-geopolit   { background:#2b0d0d; color:#f87171; }

  /* Econ calendar */
  .econ-event {
    padding: 5px 8px 5px 10px;
    border-left: 2px solid #1e2530;
    margin-bottom: 5px;
    font-family: 'Space Mono', monospace;
    font-size: 0.62rem;
    color: #94a3b8;
    background: #0d1117;
    border-radius: 0 4px 4px 0;
  }
  .econ-event.high   { border-left-color: #f87171; background: rgba(248,113,113,0.04); }
  .econ-event.medium { border-left-color: #fbbf24; background: rgba(251,191,36,0.03); }
  .econ-event.low    { border-left-color: #1e2530; }

  /* Live TV panel */
  .tv-panel {
    background: #0d1117;
    border: 1px solid #1e2530;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 8px;
  }
  .tv-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    color: #4a6080;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 6px 10px;
    background: #090c10;
    border-bottom: 1px solid #1e2530;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tv-live-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #f87171;
    display: inline-block;
    animation: livepulse 1.5s ease-in-out infinite;
  }
  @keyframes livepulse {
    0%,100% { opacity:1; }
    50%     { opacity:0.3; }
  }
  .tv-panel iframe {
    display: block;
    width: 100%;
    border: none;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: #0a0c0f; }
  ::-webkit-scrollbar-thumb { background: #1e2530; border-radius: 2px; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { background:transparent; gap:3px; }
  .stTabs [data-baseweb="tab"] {
    background:#0d1117; border:1px solid #1e2530; border-radius:6px;
    color:#4a6080; font-family:'Space Mono',monospace; font-size:0.6rem; padding:5px 12px;
  }
  .stTabs [aria-selected="true"] {
    background:#1a2030 !important; border-color:rgba(232,201,126,0.35) !important; color:#e8c97e !important;
  }
  .stTabs [data-baseweb="tab-border"] { display:none; }
  .stTabs [data-baseweb="tab-panel"]  { padding:0; }

  .stTextInput input {
    background:#0d1117 !important; border:1px solid #1e2530 !important;
    color:#e0e4ea !important; border-radius:8px !important;
    font-family:'Space Mono',monospace !important; font-size:0.75rem !important;
  }
  .stTextInput input:focus {
    border-color:rgba(232,201,126,0.55) !important;
    box-shadow:0 0 0 2px rgba(232,201,126,0.12) !important;
  }
  hr { border-color:#1e2530 !important; }
  [data-testid="column"] { padding:0 3px !important; }

  /* ── LOGIN SCREEN ── */
  .login-wrap {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #0a0c0f;
  }
  .login-card {
    width: 420px;
    background: #0d1117;
    border: 1px solid #1e2530;
    border-radius: 16px;
    padding: 48px 44px 40px;
    position: relative;
    box-shadow: 0 0 60px rgba(232,201,126,0.06), 0 24px 48px rgba(0,0,0,0.5);
  }
  .login-card::before {
    content: "";
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(232,201,126,0.4), transparent);
  }
  .login-eagle { font-size:2.8rem; text-align:center; margin-bottom:6px; }
  .login-title {
    font-family: "Syne", sans-serif;
    font-weight: 800;
    font-size: 1.6rem;
    color: #e8c97e;
    text-align: center;
    letter-spacing: 0.04em;
    margin-bottom: 2px;
  }
  .login-subtitle {
    font-family: "Space Mono", monospace;
    font-size: 0.6rem;
    color: #4a5568;
    text-align: center;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 10px;
  }
  .login-desc {
    font-family: "Syne", sans-serif;
    font-size: 0.82rem;
    color: #6a7a8c;
    text-align: center;
    line-height: 1.65;
    margin-bottom: 28px;
    padding: 0 4px;
  }
  .login-error {
    background: rgba(248,113,113,0.08);
    border: 1px solid rgba(248,113,113,0.25);
    border-radius: 8px;
    padding: 8px 14px;
    font-family: "Space Mono", monospace;
    font-size: 0.68rem;
    color: #f87171;
    text-align: center;
    margin-bottom: 14px;
  }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
defaults = {
    "chat_history": [],
    "signals": {},
    "daily_summary": "",
    "selected_asset": config.FMP_ASSETS[0],
    "data_loaded": False,
    "assets_data": {},
    "news_general": [],
    "news_asset": {},
    "econ_calendar": [],
    "news_loaded": False,
    "active_tv": "bloomberg",
    "logged_in": False,
    "current_user": "",
    "login_error": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── AUTHORIZED USERS ──────────────────────────────────────────────────────────
USERS = {
    "merwinsam01":  {"password": "Merwin123",  "display": "Merwin Samuel"},
    "sherwinsam96": {"password": "Sherwin123", "display": "Sherwin Samuel"},
}

# ── LOGIN WALL ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.markdown("""
        <div style="padding-top:60px">
          <div style="font-size:3rem;text-align:center;margin-bottom:8px;filter:drop-shadow(0 0 16px rgba(232,201,126,0.35))">🦅</div>
          <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.7rem;color:#e8c97e;
                      text-align:center;letter-spacing:0.04em;margin-bottom:4px">Eagle</div>
          <div style="font-family:'Space Mono',monospace;font-size:0.6rem;color:#4a5568;
                      text-align:center;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:18px">
            by Blackwater Trading
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:0.85rem;color:#6a7a8c;
                      text-align:center;line-height:1.7;margin-bottom:28px;padding:0 8px">
            A private market intelligence platform combining real-time asset signals,
            macro data, political &amp; economic news feeds, and AI-powered analysis.
            Monitors momentum, volatility, correlation, and market regimes across equities,
            commodities, and crypto — synthesized daily by the Eagle agent.
            <br><br>
            <span style="color:#2a3548;font-size:0.75rem;letter-spacing:0.05em">
              Authorized access only.
            </span>
          </div>
          <hr style="border:none;border-top:1px solid #1e2530;margin-bottom:24px">
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.get("login_error"):
            st.markdown(
                f'<div style="background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.25);'
                f'border-radius:8px;padding:9px 14px;font-family:Space Mono,monospace;font-size:0.68rem;'
                f'color:#f87171;text-align:center;margin-bottom:14px">'
                f'⚠ {st.session_state.login_error}</div>',
                unsafe_allow_html=True
            )

        username = st.text_input("Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("Password", placeholder="Enter your password", type="password", key="login_pass")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("Login  →", use_container_width=True, key="login_btn"):
            u = username.strip()
            p = password.strip()
            if u in USERS and USERS[u]["password"] == p:
                st.session_state.logged_in    = True
                st.session_state.current_user = USERS[u]["display"]
                st.session_state.login_error  = ""
                st.rerun()
            else:
                st.session_state.login_error = "Invalid credentials. Access denied."
                st.rerun()

        st.markdown("""
        <div style="text-align:center;margin-top:20px;font-family:'Space Mono',monospace;
                    font-size:0.52rem;color:#1e2530;letter-spacing:0.12em">
          PRIVATE PLATFORM · UNAUTHORIZED ACCESS PROHIBITED
        </div>""", unsafe_allow_html=True)

    st.stop()

# ── Helpers ────────────────────────────────────────────────────────────────────
def regime_class(r):
    return {"calm uptrend":"regime-calm-uptrend","volatile uptrend":"regime-volatile-uptrend",
            "stress selloff":"regime-stress-selloff","quiet decline":"regime-quiet-decline",
            "volatile chop":"regime-volatile-chop"}.get(r,"regime-mixed")

def vol_class(s):
    return {"low":"vol-low","normal":"vol-normal","elevated":"vol-elevated","extreme":"vol-extreme"}.get(s,"")

def fmt_pct(v,d=1):
    if v is None or (isinstance(v,float) and np.isnan(v)): return "—"
    return f"{v*100:+.{d}f}%"

def fmt_num(v,d=2):
    if v is None or (isinstance(v,float) and np.isnan(v)): return "—"
    return f"{v:.{d}f}"

def news_tag(title:str):
    t = title.lower()
    if any(w in t for w in ["fed","rate","inflation","gdp","cpi","jobs","payroll","fomc","treasury","yield","economy","recession","interest","monetary","fiscal","debt","deficit","tariff","trade"]): return ("macro","tag-macro")
    if any(w in t for w in ["war","sanction","nato","china","russia","taiwan","conflict","strike","military","troops","nuclear","ceasefire","diplomat"]): return ("geopolit","tag-geopolit")
    if any(w in t for w in ["earnings","revenue","profit","eps","guidance","beat","miss","quarterly","results"]): return ("earnings","tag-earnings")
    if any(w in t for w in ["politic","democrat","republican","vote","bill","regulation","sec","doj","president","congress","senate","election","govern","white house","trump","biden"]): return ("political","tag-political")
    return ("market","tag-market")

def impact_class(impact:str):
    i = str(impact).lower()
    if i in ("high","3","red"): return "high"
    if i in ("medium","moderate","2","orange","yellow"): return "medium"
    return "low"

# ── Chart theme ────────────────────────────────────────────────────────────────
CT = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Mono, monospace", color="#4a6080", size=9),
    xaxis=dict(gridcolor="#1e2530", linecolor="#1e2530", zeroline=False),
    yaxis=dict(gridcolor="#1e2530", linecolor="#1e2530", zeroline=False),
    margin=dict(l=6, r=6, t=22, b=6),
)

def price_chart(sig):
    p = sig["_prices"].tail(120)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=p.index, y=p.values, mode="lines",
        line=dict(color="#e8c97e",width=1.5), fill="tozeroy", fillcolor="rgba(232,201,126,0.06)"))
    fig.update_layout(title=f"{sig['symbol']} — Price (120d)", **CT, height=170)
    return fig

def vol_chart(sig):
    rv = sig["_rv_series"].dropna().tail(120)
    fig = go.Figure()
    fig.add_hrect(y0=0,               y1=config.VOL_LOW,       fillcolor="rgba(74,222,128,0.07)",  line_width=0)
    fig.add_hrect(y0=config.VOL_LOW,  y1=config.VOL_NORMAL,    fillcolor="rgba(148,163,184,0.05)", line_width=0)
    fig.add_hrect(y0=config.VOL_NORMAL,y1=config.VOL_ELEVATED, fillcolor="rgba(251,191,36,0.07)",  line_width=0)
    fig.add_hrect(y0=config.VOL_ELEVATED,y1=1.0,               fillcolor="rgba(248,113,113,0.10)", line_width=0)
    fig.add_trace(go.Scatter(x=rv.index,y=rv.values,mode="lines",line=dict(color="#fb923c",width=1.4)))
    fig.update_layout(title="Realized Volatility (20d ann.)", **CT, height=155)
    return fig

def momentum_chart(sig):
    z = sig["_z_series"].dropna().tail(120)
    colors = ["#4ade80" if v>0 else "#f87171" for v in z.values]
    fig = go.Figure()
    fig.add_hline(y=1,  line=dict(color="rgba(74,222,128,0.30)",  dash="dash",width=1))
    fig.add_hline(y=-1, line=dict(color="rgba(248,113,113,0.30)", dash="dash",width=1))
    fig.add_hline(y=0,  line=dict(color="#1e2530",width=1))
    fig.add_trace(go.Bar(x=z.index,y=z.values,marker_color=colors))
    fig.update_layout(title="Momentum Z-Score (20d)", **CT, height=155)
    return fig

def drawdown_chart(sig):
    dd = sig["_dd_series"].tail(120)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dd.index,y=dd.values*100,mode="lines",
        line=dict(color="#a78bfa",width=1.4), fill="tozeroy", fillcolor="rgba(167,139,250,0.08)"))
    fig.update_layout(title="Drawdown (60d rolling max)", **CT, height=155)
    return fig

def correlation_heatmap(signals_dict):
    syms = [s for s,v in signals_dict.items() if v and "_rets" in v]
    if len(syms)<2: return None
    rets_df = pd.concat({s:signals_dict[s]["_rets"].tail(60) for s in syms},axis=1).dropna()
    if rets_df.empty: return None
    corr = rets_df.corr().round(2)
    fig = go.Figure(data=go.Heatmap(
        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
        colorscale=[[0,"#1a2030"],[0.5,"#2a3548"],[1,"#e8c97e"]],
        text=corr.values, texttemplate="%{text:.2f}", showscale=False, zmin=-1, zmax=1,
    ))
    fig.update_layout(title="60d Rolling Correlations", **CT, height=190)
    return fig

# ── TOP BAR ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="eagle-topbar">
  <span style="font-size:1.4rem">🦅</span>
  <div>
    <div class="eagle-logo">EAGLE</div>
    <div class="eagle-sub">Blackwater Capital · Market Intelligence</div>
  </div>
  <div style="flex:1"></div>
  <div style="display:flex;align-items:center;gap:14px">
    <div style="font-family:'Space Mono',monospace;font-size:0.6rem;color:#4a6080">
      {datetime.now().strftime("%A, %B %d %Y  %H:%M")}
    </div>
    <div style="font-family:'Space Mono',monospace;font-size:0.6rem;color:#e8c97e;
                background:rgba(232,201,126,0.08);border:1px solid rgba(232,201,126,0.2);
                border-radius:20px;padding:3px 12px;letter-spacing:0.06em">
      👤 {st.session_state.current_user}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 4-COLUMN LAYOUT ────────────────────────────────────────────────────────────
col_assets, col_charts, col_news, col_media = st.columns([0.9, 2.1, 1.2, 1.3], gap="small")

# ══════════════════════════════════════════════════════════════════════════════
# COL 1 — Assets + Correlation + Flags
# ══════════════════════════════════════════════════════════════════════════════
with col_assets:
    st.markdown('<div style="padding:10px 6px 0 6px">', unsafe_allow_html=True)

    lcol, rcol = st.columns([3,1])
    with lcol:
        refresh_clicked = st.button("⟳  Refresh", use_container_width=True)
    with rcol:
        if st.button("↩", use_container_width=True, key="logout_btn"):
            st.session_state.logged_in   = False
            st.session_state.current_user= ""
            st.rerun()
    if refresh_clicked:
        st.cache_data.clear()
        for k in ["data_loaded","signals","daily_summary","news_general","news_asset","econ_calendar","news_loaded"]:
            if k in ("news_general","econ_calendar"):    st.session_state[k] = []
            elif k == "news_asset":                      st.session_state[k] = {}
            elif k in ("data_loaded","news_loaded"):     st.session_state[k] = False
            elif k == "daily_summary":                   st.session_state[k] = ""
            else:                                        st.session_state[k] = {}
        st.rerun()

    # Load market data
    if not st.session_state.data_loaded:
        with st.spinner("Loading data..."):
            assets_data = load_all_assets(days=252)
            st.session_state.assets_data = assets_data
        if assets_data:
            peer_rets = assets_data.get("SPY", pd.DataFrame()).get("returns") if "SPY" in assets_data else None
            sigs = {}
            for sym, df in assets_data.items():
                sigs[sym] = compute_signals(sym, df, None if sym=="SPY" else peer_rets)
            st.session_state.signals = sigs
            st.session_state.data_loaded = True

    # Load news
    if not st.session_state.news_loaded and st.session_state.data_loaded:
        with st.spinner("Fetching news..."):
            st.session_state.news_general  = fetch_market_news(limit=30)
            st.session_state.econ_calendar = fetch_economic_calendar(days_ahead=7)
            for sym in list(st.session_state.assets_data.keys()):
                st.session_state.news_asset[sym] = fetch_asset_news(sym, limit=8)
            st.session_state.news_loaded = True
        if not st.session_state.daily_summary and st.session_state.signals:
            with st.spinner("Generating brief..."):
                news_ctx = format_news_for_llm(st.session_state.news_general, max_items=15)
                econ_ctx = format_econ_calendar_for_llm(st.session_state.econ_calendar, max_items=8)
                summary  = generate_daily_summary(st.session_state.signals, news_ctx, econ_ctx)
                st.session_state.daily_summary = summary
                log_signals(st.session_state.signals, summary)

    signals       = st.session_state.signals
    price_summary = get_latest_price_summary(st.session_state.assets_data) if st.session_state.assets_data else {}

    # Asset list
    st.markdown('<div class="section-header">Assets</div>', unsafe_allow_html=True)
    for sym in list(st.session_state.assets_data.keys()):
        sig    = signals.get(sym, {})
        ps     = price_summary.get(sym, {})
        price  = ps.get("price", 0)
        chg    = ps.get("change_pct", 0)
        regime = sig.get("market_regime","—") if sig else "—"
        is_sel = sym == st.session_state.selected_asset
        chg_col= "#4ade80" if chg>=0 else "#f87171"
        if st.button(f"{'▶ ' if is_sel else ''}{sym}   ${price:,.2f}", key=f"ab_{sym}", use_container_width=True):
            st.session_state.selected_asset = sym
        st.markdown(f"""
        <div style="padding:1px 8px 5px;border-bottom:1px solid #0f1520;margin-bottom:2px">
          <span style="color:{chg_col};font-family:'Space Mono',monospace;font-size:0.62rem">{chg*100:+.2f}%</span>
          <span class="regime-badge {regime_class(regime)}" style="font-size:0.42rem;padding:1px 6px;float:right">{regime}</span>
        </div>""", unsafe_allow_html=True)

    # Correlation
    st.markdown('<div class="section-header" style="margin-top:12px">Correlations</div>', unsafe_allow_html=True)
    if signals:
        fig_c = correlation_heatmap(signals)
        if fig_c:
            st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar":False})

    # Flags
    st.markdown('<div class="section-header" style="margin-top:6px">Active Flags</div>', unsafe_allow_html=True)
    all_flags = [(sym,f) for sym,sig in signals.items() if sig for f in sig.get("risk_flags",[]) if "✅" not in f]
    if all_flags:
        for sym,f in all_flags[:5]:
            st.markdown(f'<div class="flag-item"><b>{sym}</b> — {f}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="flag-item">✅ No active risk flags</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COL 2 — Charts + Signals + Summary + Chat
# ══════════════════════════════════════════════════════════════════════════════
with col_charts:
    st.markdown('<div style="padding:10px 10px 0 4px">', unsafe_allow_html=True)

    selected = st.session_state.selected_asset
    sig = signals.get(selected, {})
    ps  = price_summary.get(selected, {})

    if not sig:
        st.info("Loading signals…")
    else:
        regime    = sig.get("market_regime","mixed")
        chg       = ps.get("change_pct", 0)
        chg_color = "#4ade80" if chg>=0 else "#f87171"

        # Asset header
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:12px">
          <div>
            <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.5rem;color:#e8c97e">{selected}</div>
            <div style="font-family:'Space Mono',monospace;font-size:0.6rem;color:#4a6080">Updated: {sig.get('date','—')}</div>
          </div>
          <div>
            <div style="font-family:'Space Mono',monospace;font-size:1.2rem;font-weight:700;color:#e0e4ea">${sig.get('price',0):,.2f}</div>
            <div style="color:{chg_color};font-family:'Space Mono',monospace;font-size:0.72rem">{chg*100:+.2f}% today</div>
          </div>
          <div style="flex:1"></div>
          <span class="regime-badge {regime_class(regime)}">{regime}</span>
        </div>
        """, unsafe_allow_html=True)

        # Scorecard
        m1,m2,m3,m4,m5 = st.columns(5)
        for col_m, label, value, sub in [
            (m1,"Momentum",   fmt_pct(sig.get("momentum_20d")), ""),
            (m2,"Z-Score",    fmt_num(sig.get("momentum_zscore")), ""),
            (m3,"Vol (Ann.)", fmt_pct(sig.get("vol_20d_ann")),
             f'<span class="{vol_class(sig.get("vol_state",""))}">{sig.get("vol_state","—")}</span>'),
            (m4,"Max DD",     fmt_pct(sig.get("max_drawdown_60d")), ""),
            (m5,"Corr SPY",   fmt_num(sig.get("corr_to_peer")), sig.get("corr_state","—")),
        ]:
            with col_m:
                st.markdown(f"""<div class="metric-card">
                  <div class="metric-label">{label}</div>
                  <div class="metric-value">{value}</div>
                  <div style="font-family:'Space Mono',monospace;font-size:0.6rem;color:#4a6080;margin-top:2px">{sub}</div>
                </div>""", unsafe_allow_html=True)

        # Chart tabs
        t1,t2,t3,t4 = st.tabs(["Price","Volatility","Momentum","Drawdown"])
        with t1: st.plotly_chart(price_chart(sig),    use_container_width=True, config={"displayModeBar":False})
        with t2: st.plotly_chart(vol_chart(sig),      use_container_width=True, config={"displayModeBar":False})
        with t3: st.plotly_chart(momentum_chart(sig), use_container_width=True, config={"displayModeBar":False})
        with t4: st.plotly_chart(drawdown_chart(sig), use_container_width=True, config={"displayModeBar":False})

        # Flags
        st.markdown(f'<div class="section-header" style="margin-top:8px">Risk Flags — {selected}</div>', unsafe_allow_html=True)
        for f in sig.get("risk_flags",[]):
            st.markdown(f'<div class="flag-item">{f}</div>', unsafe_allow_html=True)

        # Daily summary
        st.markdown('<div class="section-header" style="margin-top:10px">Eagle Daily Summary</div>', unsafe_allow_html=True)
        if st.session_state.daily_summary:
            st.markdown(f"""<div style="background:#0d1117;border:1px solid #1e2530;border-left:3px solid #e8c97e;
                border-radius:8px;padding:14px;font-size:0.78rem;line-height:1.7;
                color:#c8d4e4;white-space:pre-wrap;font-family:'Syne',sans-serif;">
                {st.session_state.daily_summary}</div>""", unsafe_allow_html=True)
        else:
            st.info("No summary yet — click Refresh.")

        if st.button(f"🔍 Deep-dive: {selected}", use_container_width=True):
            asset_news_fmt = format_news_for_llm(
                st.session_state.news_asset.get(selected,[]) + st.session_state.news_general[:5], max_items=10)
            with st.spinner("Analyzing..."):
                expl = explain_asset_signal(sig, news_context=asset_news_fmt)
                st.session_state.chat_history.append({"role":"assistant","content":f"**Deep-dive: {selected}**\n\n{expl}"})
            st.rerun()

    # History
    with st.expander("📋 Signal History", expanded=False):
        log_df = load_log()
        if not log_df.empty:
            cols  = ["date","symbol","momentum_regime","vol_state","market_regime","risk_flags"]
            avail = [c for c in cols if c in log_df.columns]
            st.dataframe(log_df[avail].tail(50).sort_values("date",ascending=False),
                         use_container_width=True, height=180)
        else:
            st.caption("No history yet.")

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COL 3 — News Feed + Economic Calendar + Chat
# ══════════════════════════════════════════════════════════════════════════════
with col_news:
    st.markdown('<div style="padding:10px 8px 0 4px">', unsafe_allow_html=True)

    # ── Chat agent at the top of the news column ───────────────────────────────
    st.markdown("""
    <div style="padding:10px 12px 8px;border-bottom:1px solid #1e2530;margin-bottom:8px">
      <div style="font-family:'Space Mono',monospace;font-size:0.68rem;color:#e8c97e;letter-spacing:0.1em;text-transform:uppercase">
        🦅 Eagle Agent <span style="color:#4a6080;font-size:0.52rem">· news-aware</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Chat messages
    chat_area = st.container()
    with chat_area:
        if not st.session_state.chat_history:
            st.markdown("""
            <div style="color:#4a6080;font-family:'Space Mono',monospace;font-size:0.65rem;line-height:1.9;padding:4px">
              Eagle ready. Ask about:<br>
              · Market regimes &amp; signals<br>
              · How news connects to data<br>
              · Geopolitical &amp; macro risk<br>
              · Upcoming economic events<br>
              · Volatility &amp; drawdown<br>
              <span style="color:#2a3548;font-size:0.6rem">No trades · No price predictions</span>
            </div>""", unsafe_allow_html=True)
        else:
            for msg in st.session_state.chat_history[-14:]:
                content = msg["content"].replace("\n","<br>")
                if msg["role"] == "user":
                    st.markdown(f'<div class="chat-msg-user"><div class="chat-msg-label">You</div>{content}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-msg-eagle"><div class="chat-msg-label" style="color:#e8c97e">Eagle</div>{content}</div>', unsafe_allow_html=True)

    # Quick prompts
    st.markdown('<div class="section-header">Quick Questions</div>', unsafe_allow_html=True)
    qc = st.columns(2)
    qprompts = ["Overall regime?","Top news impact?","Geopolitical risk?","Macro events?","Vol comparison","Corr concerns?"]
    for i,p in enumerate(qprompts):
        with qc[i%2]:
            if st.button(p, key=f"qp_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role":"user","content":p})
                with st.spinner(""):
                    reply = chat_with_agent(
                        st.session_state.chat_history, st.session_state.signals,
                        news_context=format_news_for_llm(st.session_state.news_general,12),
                        econ_context=format_econ_calendar_for_llm(st.session_state.econ_calendar),
                    )
                st.session_state.chat_history.append({"role":"assistant","content":reply})
                st.rerun()

    user_input = st.text_input("Message Eagle", placeholder="Ask about markets or news...",
                               label_visibility="collapsed", key="chat_input")
    sc, cc = st.columns([3,1])
    with sc:
        send = st.button("Send →", use_container_width=True, key="send_btn")
    with cc:
        if st.button("Clear", use_container_width=True, key="clear_btn"):
            st.session_state.chat_history = []
            st.rerun()

    if send and user_input.strip():
        st.session_state.chat_history.append({"role":"user","content":user_input.strip()})
        with st.spinner("Eagle thinking..."):
            reply = chat_with_agent(
                st.session_state.chat_history, st.session_state.signals,
                news_context=format_news_for_llm(st.session_state.news_general,12),
                econ_context=format_econ_calendar_for_llm(st.session_state.econ_calendar),
            )
        st.session_state.chat_history.append({"role":"assistant","content":reply})
        st.rerun()

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    # ── News Feed ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Latest Headlines</div>', unsafe_allow_html=True)

    # Asset news first
    asset_headlines = st.session_state.news_asset.get(selected, [])
    all_news = asset_headlines[:4] + [n for n in st.session_state.news_general if n not in asset_headlines]
    for item in all_news[:18]:
        title  = item.get("title", item.get("headline",""))
        date   = str(item.get("publishedDate", item.get("date","") ))[:10]
        source = item.get("site", item.get("source",""))
        url    = item.get("url","#")
        if not title: continue
        tag_name, tag_cls = news_tag(title)
        st.markdown(f"""
        <div class="news-card">
          <div class="news-title">
            <a href="{url}" target="_blank" style="color:#c8d4e4;text-decoration:none">{title}</a>
            <span class="news-tag {tag_cls}">{tag_name}</span>
          </div>
          <div class="news-meta">{date} · {source}</div>
        </div>""", unsafe_allow_html=True)

    # ── Economic Calendar ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header" style="margin-top:14px">Economic Calendar — 7 Days</div>', unsafe_allow_html=True)
    cal = st.session_state.econ_calendar
    if cal:
        for ev in cal[:14]:
            name   = ev.get("event", ev.get("name",""))
            date   = str(ev.get("date",""))[:10]
            impact = ev.get("impact", ev.get("importance",""))
            actual = ev.get("actual","")
            est    = ev.get("estimate", ev.get("consensus",""))
            ic     = impact_class(str(impact))
            imp_color = {"high":"#f87171","medium":"#fbbf24","low":"#4a6080"}.get(ic,"#4a6080")
            country = ev.get("country","")
            st.markdown(f"""
            <div class="econ-event {ic}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <span style="color:#e0e4ea;font-weight:700;font-size:0.63rem">{name}</span>
                <span style="color:{imp_color};font-size:0.58rem;white-space:nowrap;margin-left:6px">● {impact}</span>
              </div>
              <div style="color:#4a6080;font-size:0.58rem;margin-top:2px">
                {date}{f' · {country}' if country else ''}
                {f' <span style="color:#94a3b8">est {est}</span>' if est else ''}
                {f' <span style="color:#e8c97e">act {actual}</span>' if actual else ''}
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption("No upcoming events loaded.")

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COL 4 — Live TV (Bloomberg + Al Jazeera)
# ══════════════════════════════════════════════════════════════════════════════
with col_media:
    st.markdown('<div style="padding:10px 8px 0 4px">', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Live Market TV</div>', unsafe_allow_html=True)

    # Channel selector
    tv_col1, tv_col2 = st.columns(2)
    with tv_col1:
        if st.button("📺 Bloomberg", use_container_width=True, key="tv_bloomberg"):
            st.session_state.active_tv = "bloomberg"
    with tv_col2:
        if st.button("📺 Al Jazeera", use_container_width=True, key="tv_aljazeera"):
            st.session_state.active_tv = "aljazeera"

    # Active channel
    active = st.session_state.active_tv
    if active == "bloomberg":
        channel_label = "BLOOMBERG LIVE"
        # Extract YouTube video ID for embed
        yt_embed = "https://www.youtube.com/embed/iEpJwprxDdk?autoplay=1&mute=1"
    else:
        channel_label = "AL JAZEERA LIVE"
        yt_embed = "https://www.youtube.com/embed/gCNeDWCI0vo?autoplay=1&mute=1"

    st.markdown(f"""
    <div class="tv-panel" style="margin-top:6px">
      <div class="tv-label">
        <span class="tv-live-dot"></span>
        {channel_label}
      </div>
      <iframe
        src="{yt_embed}"
        height="195"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen>
      </iframe>
    </div>
    """, unsafe_allow_html=True)

    # Second channel (muted/thumbnail)
    if active == "bloomberg":
        other_label = "AL JAZEERA"
        other_embed = "https://www.youtube.com/embed/gCNeDWCI0vo?mute=1"
    else:
        other_label = "BLOOMBERG"
        other_embed = "https://www.youtube.com/embed/iEpJwprxDdk?mute=1"

    st.markdown(f"""
    <div class="tv-panel">
      <div class="tv-label" style="color:#4a6080">
        <span style="width:5px;height:5px;border-radius:50%;background:#4a6080;display:inline-block"></span>
        {other_label} · MUTED
      </div>
      <iframe
        src="{other_embed}"
        height="145"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen>
      </iframe>
    </div>
    """, unsafe_allow_html=True)

    # ── News → Signal synthesis ────────────────────────────────────────────────
    st.markdown('<div class="section-header" style="margin-top:8px">News × Signal Link</div>', unsafe_allow_html=True)
    if st.button("🔗 Connect News to Signals", use_container_width=True, key="synth_btn"):
        asset_news_fmt = format_news_for_llm(
            st.session_state.news_asset.get(selected,[]) + st.session_state.news_general, max_items=12)
        econ_ctx = format_econ_calendar_for_llm(st.session_state.econ_calendar)
        with st.spinner("Eagle connecting dots..."):
            synthesis = explain_asset_signal(signals.get(selected,{}), news_context=asset_news_fmt)
        st.session_state.chat_history.append({"role":"assistant","content":f"**News synthesis for {selected}:**\n\n{synthesis}"})
        st.markdown(f"""<div style="background:#0d1117;border:1px solid #1e2530;border-left:3px solid #a78bfa;
            border-radius:8px;padding:12px;font-size:0.75rem;line-height:1.7;color:#c8d4e4;
            white-space:pre-wrap;font-family:'Syne',sans-serif;margin-top:8px">
            {synthesis}</div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

