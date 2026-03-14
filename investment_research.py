"""
Blackwater One — Investment Research
Full-stack equity research platform with Stan Weinstein Stage Analysis.
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import config

API = config.FMP_API_KEY
BASE = "https://financialmodelingprep.com/stable"

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
IR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600&display=swap');

:root {
  --bg:       #07080a;
  --bg1:      #0d0f12;
  --bg2:      #12151a;
  --border:   #1e2530;
  --gold:     #c9a84c;
  --gold2:    #e8c97e;
  --green:    #2ecc71;
  --red:      #e74c3c;
  --amber:    #f39c12;
  --blue:     #3498db;
  --txt:      #e8ecf0;
  --txt2:     #8a96a8;
  --txt3:     #4a5568;
}

.ir-topbar {
  background: #000;
  border-bottom: 2px solid var(--gold);
  padding: 0 20px;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.ir-wordmark {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.3rem;
  color: var(--gold2);
  letter-spacing: .12em;
}
.ir-sep { width:1px; height:22px; background: #2a2000; }
.ir-subtitle {
  font-family: 'DM Mono', monospace;
  font-size: .58rem;
  color: #6a5a2a;
  letter-spacing: .16em;
  text-transform: uppercase;
}
.ir-ts {
  font-family: 'DM Mono', monospace;
  font-size: .58rem;
  color: #4a3a1a;
  margin-left: auto;
}

.ir-sec {
  font-family: 'DM Mono', monospace;
  font-size: .55rem;
  color: var(--gold);
  text-transform: uppercase;
  letter-spacing: .18em;
  padding: 10px 0 5px;
  border-bottom: 1px solid #1a1500;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ir-sec::before {
  content: '';
  display: inline-block;
  width: 2px;
  height: 10px;
  background: var(--gold);
}

.ir-kpi {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-top: 2px solid var(--gold);
  padding: 10px 14px;
  text-align: center;
}
.ir-kpi .lbl {
  font-family: 'DM Mono', monospace;
  font-size: .50rem;
  color: var(--txt3);
  text-transform: uppercase;
  letter-spacing: .12em;
  margin-bottom: 4px;
}
.ir-kpi .val {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.6rem;
  color: var(--txt);
  line-height: 1;
}
.ir-kpi .sub { font-size: .58rem; color: var(--txt2); margin-top: 2px; font-family: 'DM Mono', monospace; }
.ir-kpi.green { border-top-color: var(--green); }
.ir-kpi.green .val { color: var(--green); }
.ir-kpi.red   { border-top-color: var(--red); }
.ir-kpi.red   .val { color: var(--red); }
.ir-kpi.gold  { border-top-color: var(--gold2); }
.ir-kpi.gold  .val { color: var(--gold2); }

.ir-card {
  background: var(--bg1);
  border: 1px solid var(--border);
  padding: 14px 16px;
  margin-bottom: 6px;
  font-family: 'DM Sans', sans-serif;
  font-size: .80rem;
  color: var(--txt2);
  line-height: 1.7;
}

.stage-badge {
  display: inline-block;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.1rem;
  letter-spacing: .1em;
  padding: 6px 18px;
  border-radius: 2px;
  margin-bottom: 8px;
}
.stage-1 { background: rgba(52,152,219,.15); color: #3498db; border: 1px solid rgba(52,152,219,.3); }
.stage-2 { background: rgba(46,204,113,.15); color: #2ecc71; border: 1px solid rgba(46,204,113,.3); }
.stage-3 { background: rgba(243,156,18,.15); color: #f39c12; border: 1px solid rgba(243,156,18,.3); }
.stage-4 { background: rgba(231,76,60,.15);  color: #e74c3c; border: 1px solid rgba(231,76,60,.3); }

.verdict-buy  { color: #2ecc71; font-family: 'Bebas Neue'; font-size: 1.4rem; letter-spacing: .1em; }
.verdict-hold { color: #f39c12; font-family: 'Bebas Neue'; font-size: 1.4rem; letter-spacing: .1em; }
.verdict-sell { color: #e74c3c; font-family: 'Bebas Neue'; font-size: 1.4rem; letter-spacing: .1em; }
.verdict-wait { color: #3498db; font-family: 'Bebas Neue'; font-size: 1.4rem; letter-spacing: .1em; }

.peer-card {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-left: 2px solid var(--gold);
  padding: 7px 12px;
  margin-bottom: 3px;
  font-family: 'DM Mono', monospace;
  font-size: .68rem;
  color: var(--txt2);
  transition: border-left-color .12s;
}
.peer-card:hover { border-left-color: var(--gold2); }

.news-item {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-left: 2px solid #1e2530;
  padding: 8px 12px;
  margin-bottom: 4px;
  transition: border-left-color .12s;
}
.news-item:hover { border-left-color: var(--gold); }
.news-title {
  font-family: 'DM Sans', sans-serif;
  font-size: .78rem;
  color: var(--txt);
  line-height: 1.4;
  margin-bottom: 3px;
}
.news-title a { color: var(--txt); text-decoration: none; }
.news-title a:hover { color: var(--gold2); }
.news-meta  { font-family: 'DM Mono', monospace; font-size: .55rem; color: var(--txt3); }

.chat-wrap {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-top: 2px solid var(--gold);
  padding: 0;
}
.chat-hdr {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  font-family: 'DM Mono', monospace;
  font-size: .56rem;
  color: var(--gold);
  text-transform: uppercase;
  letter-spacing: .14em;
}
.chat-bubble-u {
  background: rgba(201,168,76,.08);
  border: 1px solid rgba(201,168,76,.15);
  border-radius: 2px;
  padding: 8px 12px;
  margin: 6px 0;
  font-family: 'DM Sans', sans-serif;
  font-size: .76rem;
  color: var(--gold2);
}
.chat-bubble-a {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 2px;
  padding: 8px 12px;
  margin: 6px 0;
  font-family: 'DM Sans', sans-serif;
  font-size: .76rem;
  color: var(--txt2);
  line-height: 1.65;
}

.fin-tab {
  background: var(--bg1);
  border: 1px solid var(--border);
}

.search-hint {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-top: none;
  max-height: 220px;
  overflow-y: auto;
}
.hint-row {
  padding: 7px 12px;
  font-family: 'DM Mono', monospace;
  font-size: .70rem;
  color: var(--txt2);
  cursor: pointer;
  border-bottom: 1px solid #0d0f12;
  display: flex;
  gap: 10px;
  align-items: center;
}
.hint-row:hover { background: rgba(201,168,76,.06); color: var(--gold2); }
.hint-ticker { color: var(--gold2); font-weight: 500; min-width: 60px; }
.hint-exch   { color: var(--txt3); font-size: .60rem; min-width: 50px; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fmp(endpoint, params=None, base=BASE):
    p = params or {}
    p["apikey"] = API
    try:
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[ir] FMP {endpoint}: {e}")
    return None

@st.cache_data(ttl=60, show_spinner=False)
def search_ticker(q):
    # Try name search first, fall back to symbol search
    data = fmp(f"search-name?query={q}&limit=10")
    if data:
        return data
    data2 = fmp(f"search?query={q}&limit=10")
    return data2 or []

@st.cache_data(ttl=3600, show_spinner=False)
def get_profile(sym):
    d = fmp(f"profile?symbol={sym}")
    return d[0] if d else {}

@st.cache_data(ttl=300, show_spinner=False)
def get_price_history(sym):
    d = fmp(f"historical-price-eod/full?symbol={sym}")
    if not d:
        return pd.DataFrame()
    # stable endpoint returns list directly; v3 returns {"historical": [...]}
    records = d if isinstance(d, list) else d.get("historical", [])
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    # Normalise column names
    for col in ["adjClose", "adj_close"]:
        if col in df.columns and "close" not in df.columns:
            df["close"] = df[col]
    return df.sort_values("date").reset_index(drop=True)

@st.cache_data(ttl=3600, show_spinner=False)
def get_peers(sym):
    d = fmp(f"stock-peers?symbol={sym}")
    return d[0].get("peersList", []) if d else []

@st.cache_data(ttl=3600, show_spinner=False)
def get_income(sym):
    d = fmp(f"income-statement?symbol={sym}&limit=6")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_income_ttm(sym):
    d = fmp(f"income-statement-ttm?symbol={sym}")
    return d[0] if d else {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_balance(sym):
    d = fmp(f"balance-sheet-statement?symbol={sym}&limit=6")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_cashflow(sym):
    d = fmp(f"cash-flow-statement?symbol={sym}&limit=6")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_scores(sym):
    d = fmp(f"financial-scores?symbol={sym}")
    return d[0] if d else {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_ratios(sym):
    # ratios-ttm: margins, current ratio, P/E TTM etc
    d_ttm = fmp(f"ratios-ttm?symbol={sym}")
    ttm = d_ttm[0] if d_ttm else {}
    # ratios (annual): ROE, ROA, D/E, P/E, P/B from most recent year
    d_ann = fmp(f"ratios?symbol={sym}&limit=1")
    ann = d_ann[0] if d_ann else {}
    # key-metrics-ttm: ROE/ROA/D-E as true TTM values
    d_km = fmp(f"key-metrics-ttm?symbol={sym}")
    km = d_km[0] if d_km else {}
    # Build merged dict — be explicit about which source wins per field
    merged = {**ann, **ttm}  # TTM margins override annual
    # For ROE/ROA/D-E prefer key-metrics-ttm, then annual
    for field, km_key, ann_key in [
        ("_roe", "returnOnEquityTTM", "returnOnEquity"),
        ("_roa", "returnOnAssetsTTM", "returnOnAssets"),
        ("_de",  "debtToEquityTTM",   "debtToEquityRatio"),
    ]:
        merged[field] = km.get(km_key) or ann.get(ann_key)
    # P/E, P/B, EV/EBITDA — prefer TTM endpoint names, fall back to annual
    merged["_pe"]  = ttm.get("peRatioTTM") or ann.get("priceToEarningsRatio")
    merged["_pb"]  = ttm.get("priceToBookRatioTTM") or ann.get("priceToBookRatio")
    merged["_evm"] = ttm.get("enterpriseValueMultipleTTM") or ann.get("enterpriseValueMultiple")
    return merged

@st.cache_data(ttl=3600, show_spinner=False)
def get_dcf(sym):
    d = fmp(f"discounted-cash-flow?symbol={sym}")
    return d[0] if d else {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_estimates(sym):
    d = fmp(f"analyst-estimates?symbol={sym}&period=annual&limit=6")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_earnings(sym):
    d = fmp(f"earnings?symbol={sym}&limit=12")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_dividends(sym):
    d = fmp(f"dividends?symbol={sym}&limit=20")
    if isinstance(d, dict):
        recs = d.get("historical", [])
    else:
        recs = d or []
    return pd.DataFrame(recs) if recs else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_owner_earnings(sym):
    d = fmp(f"owner-earnings?symbol={sym}&limit=6")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_ev(sym):
    d = fmp(f"enterprise-values?symbol={sym}&limit=6")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_rev_product(sym):
    d = fmp(f"revenue-product-segmentation?symbol={sym}")
    return d or []

@st.cache_data(ttl=3600, show_spinner=False)
def get_rev_geo(sym):
    d = fmp(f"revenue-geographic-segmentation?symbol={sym}")
    return d or []

@st.cache_data(ttl=300, show_spinner=False)
def get_news(sym):
    d = fmp(f"news/stock?symbols={sym}&limit=20")
    return d or []

@st.cache_data(ttl=3600, show_spinner=False)
def get_sector_pe(sector):
    d = fmp(f"historical-sector-pe?sector={requests.utils.quote(sector)}&limit=20")
    return pd.DataFrame(d) if d else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_industry_pe(industry):
    d = fmp(f"historical-industry-pe?industry={requests.utils.quote(industry)}&limit=20")
    return pd.DataFrame(d) if d else pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
# STAN WEINSTEIN STAGE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def weinstein_analysis(df: pd.DataFrame) -> dict:
    """
    Stan Weinstein Stage Analysis from 'Secrets for Profiting in Bull and Bear Markets'.

    Key principles:
    - Stage 1 (Basing):    Price flat, hugging 30-week MA from below. Volume low and declining.
                           MA flattening out after a decline. WAIT — do not buy yet.
    - Stage 2 (Advancing): Price breaks above 30-week MA on expanding volume. MA turns up.
                           This is the BUY zone. The longer the Stage 1 base, the bigger the move.
    - Stage 3 (Topping):   Price stalling above MA, MA flattening. Volume erratic.
                           Distribution phase. HOLD existing, do NOT add.
    - Stage 4 (Declining): Price breaks below 30-week MA on volume. MA turns down.
                           SELL / AVOID. Never buy in Stage 4.

    Additional signals used:
    - 30-week (150-day) moving average direction
    - Relative volume vs 10-week average
    - Breakout above resistance / breakdown below support
    - Price position relative to 52-week high/low
    """
    if df.empty or len(df) < 155:
        return {"stage": 0, "verdict": "INSUFFICIENT DATA", "detail": "Need at least 155 days of data."}

    # Normalise close column
    if "close" not in df.columns:
        for alt in ["adjClose", "adj_close", "Close"]:
            if alt in df.columns:
                df = df.copy()
                df["close"] = df[alt]
                break
    if "close" not in df.columns:
        return {"stage": 0, "verdict": "INSUFFICIENT DATA", "detail": "No close price column found."}

    close = df["close"].values
    vol   = df["volume"].values if "volume" in df.columns else np.ones(len(close))

    # ── Moving averages ───────────────────────────────────────────────────────
    ma30w = pd.Series(close).rolling(150).mean().values   # 30-week MA
    ma10w = pd.Series(close).rolling(50).mean().values    # 10-week MA
    ma4w  = pd.Series(close).rolling(20).mean().values    # 4-week MA

    cur   = close[-1]
    ma30  = ma30w[-1]
    ma30_4w_ago = ma30w[-20] if len(ma30w) > 20 else ma30w[0]
    ma30_slope  = (ma30 - ma30_4w_ago) / ma30_4w_ago if ma30_4w_ago else 0

    # ── Volume analysis ───────────────────────────────────────────────────────
    vol_10w_avg = np.mean(vol[-50:]) if len(vol) >= 50 else np.mean(vol)
    vol_4w_avg  = np.mean(vol[-20:]) if len(vol) >= 20 else np.mean(vol)
    vol_ratio   = vol_4w_avg / vol_10w_avg if vol_10w_avg > 0 else 1.0

    # ── 52-week range ─────────────────────────────────────────────────────────
    high52 = np.max(close[-252:]) if len(close) >= 252 else np.max(close)
    low52  = np.min(close[-252:]) if len(close) >= 252 else np.min(close)
    pct_from_high = (cur - high52) / high52
    pct_from_low  = (cur - low52)  / low52

    # ── Stage determination ───────────────────────────────────────────────────
    above_ma30 = cur > ma30
    ma30_rising= ma30_slope > 0.003
    ma30_flat  = abs(ma30_slope) <= 0.003
    ma30_falling=ma30_slope < -0.003

    # Stage 2: above MA30, MA30 rising, volume expanding
    if above_ma30 and ma30_rising and vol_ratio >= 0.95:
        stage = 2
        if pct_from_high > -0.08:
            # Near highs in Stage 2 — ideal buy zone
            verdict = "BUY"
            detail  = (f"Stage 2 Advance confirmed. Price is {abs(pct_from_high)*100:.1f}% from 52-week high "
                       f"with 30-week MA rising ({ma30_slope*100:+.2f}%/month). "
                       f"Volume ratio {vol_ratio:.2f}x vs 10-week avg. "
                       f"Weinstein: this is the optimal entry zone — the trend is your friend.")
        else:
            verdict = "BUY"
            detail  = (f"Stage 2 Advance in progress. Price {abs(pct_from_high)*100:.1f}% below 52-week high. "
                       f"30-week MA rising. Consider buying on any pullback to the MA.")

    # Stage 3: above MA30 but MA flattening, potential topping
    elif above_ma30 and ma30_flat:
        stage   = 3
        verdict = "HOLD"
        detail  = (f"Stage 3 Topping area. Price still above 30-week MA but MA is flattening "
                   f"(slope {ma30_slope*100:+.2f}%). Weinstein warns: do NOT add positions here. "
                   f"Watch for a break below the MA which signals Stage 4. "
                   f"If already long, trail your stop close to the MA.")

    # Stage 4: below MA30, MA falling — decline phase
    elif not above_ma30 and ma30_falling:
        stage   = 4
        verdict = "SELL / AVOID"
        detail  = (f"Stage 4 Decline. Price is {abs((cur-ma30)/ma30)*100:.1f}% below falling 30-week MA. "
                   f"Weinstein is unequivocal: NEVER buy in Stage 4. "
                   f"If you own this stock, sell. Wait for a new Stage 1 base to form before re-entry.")

    # Stage 1: below MA30 but MA flattening — basing/accumulation
    elif not above_ma30 and ma30_flat:
        stage   = 1
        verdict = "WAIT"
        detail  = (f"Stage 1 Basing. Price is forming a base below/at the 30-week MA which is flattening "
                   f"(slope {ma30_slope*100:+.2f}%). The longer the base, the bigger the eventual move. "
                   f"Weinstein: Do NOT buy yet — wait for a clear breakout above the MA on volume. "
                   f"Set an alert at ${ma30:.2f} (current 30-week MA).")

    # Edge cases
    elif above_ma30 and ma30_falling:
        stage   = 3
        verdict = "HOLD / REDUCE"
        detail  = (f"Late Stage 3 / early Stage 4 transition. Price still above MA but MA is turning down "
                   f"({ma30_slope*100:+.2f}%). High risk zone. Reduce exposure and tighten stops.")
    else:
        stage   = 1
        verdict = "WAIT"
        detail  = (f"Stage 1 — ambiguous basing pattern. Price near declining MA. "
                   f"Monitor for a clean breakout before committing capital.")

    return {
        "stage":      stage,
        "verdict":    verdict,
        "detail":     detail,
        "cur":        cur,
        "ma30":       ma30,
        "ma30_slope": ma30_slope,
        "vol_ratio":  vol_ratio,
        "high52":     high52,
        "low52":      low52,
        "pct_high":   pct_from_high,
        "ma30w":      ma30w,
        "ma10w":      ma10w,
    }

# ─────────────────────────────────────────────────────────────────────────────
# CHART BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_price_chart(df: pd.DataFrame, sym: str, stage_data: dict, show_stage: bool) -> go.Figure:
    df2 = df.tail(504).copy()   # 2 years
    dates = df2["date"]
    closes= df2["close"] if "close" in df2.columns else df2.get("adjClose", df2.iloc[:,0])
    vols  = df2.get("volume", pd.Series([0]*len(df2)))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25],
                        vertical_spacing=0.03)

    # ── Candlestick ───────────────────────────────────────────────────────────
    if all(c in df2.columns for c in ["open","high","low","close"]):
        fig.add_trace(go.Candlestick(
            x=dates, open=df2["open"], high=df2["high"],
            low=df2["low"], close=closes,
            increasing=dict(line=dict(color="#2ecc71", width=1), fillcolor="rgba(46,204,113,0.7)"),
            decreasing=dict(line=dict(color="#e74c3c", width=1), fillcolor="rgba(231,76,60,0.7)"),
            name=sym, showlegend=False,
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=dates, y=closes, line=dict(color="#c9a84c", width=1.5),
                                 name=sym, showlegend=False), row=1, col=1)

    # ── Stage analysis overlays ───────────────────────────────────────────────
    if show_stage and stage_data.get("stage", 0) > 0:
        n = len(df2)
        ma30_full = pd.Series(df.tail(504 + 150)["close"].values).rolling(150).mean().values[-n:]
        ma10_full = pd.Series(df.tail(504 + 50)["close"].values).rolling(50).mean().values[-n:]

        fig.add_trace(go.Scatter(
            x=dates, y=ma30_full, name="30-Week MA",
            line=dict(color="#c9a84c", width=2, dash="solid"), opacity=0.9,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=ma10_full, name="10-Week MA",
            line=dict(color="#3498db", width=1.2, dash="dot"), opacity=0.7,
        ), row=1, col=1)

        # Stage background shading
        stage_colors = {1:"rgba(52,152,219,0.04)", 2:"rgba(46,204,113,0.04)",
                        3:"rgba(243,156,18,0.04)", 4:"rgba(231,76,60,0.04)"}
        sc = stage_colors.get(stage_data["stage"], "rgba(0,0,0,0)")
        fig.add_vrect(x0=dates.iloc[max(0,len(dates)-90)], x1=dates.iloc[-1],
                      fillcolor=sc, layer="below", line_width=0, row=1, col=1)

    # ── Volume bars ───────────────────────────────────────────────────────────
    vol_colors = []
    for i in range(len(df2)):
        if i == 0:
            vol_colors.append("rgba(201,168,76,0.5)")
        else:
            vol_colors.append("rgba(46,204,113,0.5)" if closes.iloc[i] >= closes.iloc[i-1]
                              else "rgba(231,76,60,0.5)")
    fig.add_trace(go.Bar(x=dates, y=vols, name="Volume", marker_color=vol_colors,
                         showlegend=False), row=2, col=1)

    fig.update_layout(
        paper_bgcolor="#07080a", plot_bgcolor="#07080a",
        font=dict(family="DM Mono, monospace", color="#4a5568", size=10),
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=420,
        legend=dict(orientation="h", x=0, y=1.02, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=9, color="#8a96a8")),
        xaxis2=dict(gridcolor="#0d0f12", linecolor="#1e2530"),
        yaxis=dict(gridcolor="#0d0f12", linecolor="#1e2530", tickformat=",.2f"),
        yaxis2=dict(gridcolor="#0d0f12", linecolor="#1e2530"),
    )
    fig.update_xaxes(gridcolor="#0d0f12", linecolor="#1e2530")
    return fig


def build_financials_chart(inc: pd.DataFrame) -> go.Figure:
    if inc.empty:
        return go.Figure()
    cols = ["date","revenue","netIncome","operatingIncome","grossProfit"]
    cols = [c for c in cols if c in inc.columns]
    df = inc[cols].head(6).copy()
    df["date"] = df["date"].astype(str).str[:4]
    df = df.sort_values("date")

    fig = go.Figure()
    colors = {"revenue":"#3498db","grossProfit":"#2ecc71","operatingIncome":"#c9a84c","netIncome":"#e74c3c"}
    for col in [c for c in ["revenue","grossProfit","operatingIncome","netIncome"] if c in df.columns]:
        fig.add_trace(go.Bar(
            x=df["date"], y=df[col]/1e9,
            name=col.replace("I"," I").replace("P"," P").replace("G"," G").strip(),
            marker_color=colors.get(col,"#8a96a8"), opacity=0.85,
        ))
    fig.update_layout(
        barmode="group", paper_bgcolor="#07080a", plot_bgcolor="#07080a",
        font=dict(family="DM Mono", color="#4a5568", size=9),
        margin=dict(l=0,r=0,t=10,b=0), height=280,
        yaxis=dict(gridcolor="#0d0f12", title="USD Billions", tickformat=",.1f"),
        xaxis=dict(gridcolor="#0d0f12"),
        legend=dict(orientation="h", x=0, y=1.05, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=8, color="#8a96a8")),
    )
    return fig


def build_pe_chart(df: pd.DataFrame, label: str) -> go.Figure:
    if df.empty:
        return go.Figure()
    df = df.sort_values("date") if "date" in df.columns else df
    pe_col = next((c for c in ["pe","peRatio","P/E"] if c in df.columns), None)
    if not pe_col:
        return go.Figure()
    fig = go.Figure(go.Scatter(
        x=df.get("date", df.index), y=df[pe_col],
        line=dict(color="#c9a84c", width=1.5), fill="tozeroy",
        fillcolor="rgba(201,168,76,0.06)", name=label,
    ))
    fig.update_layout(
        paper_bgcolor="#07080a", plot_bgcolor="#07080a",
        font=dict(family="DM Mono", color="#4a5568", size=9),
        margin=dict(l=0,r=0,t=10,b=0), height=180,
        yaxis=dict(gridcolor="#0d0f12", title="P/E"),
        xaxis=dict(gridcolor="#0d0f12"),
    )
    return fig


def build_seg_chart(data: list, title: str) -> go.Figure:
    if not data:
        return go.Figure()
    # FMP returns [{"date": "YYYY", "segmentName": value}] OR [{"date": {"seg":val}}]
    latest = data[0] if isinstance(data[0], dict) else {}
    # Handle nested date-keyed format: {"2024-09-28": {"iPhone": 1234, ...}}
    nested = {k:v for k,v in latest.items() if isinstance(v, dict)}
    if nested:
        inner = list(nested.values())[0]
        items = {k: float(v) for k,v in inner.items() if isinstance(v,(int,float)) and v > 0}
    else:
        items = {k:float(v) for k,v in latest.items() if k != "date" and isinstance(v,(int,float)) and v > 0}
    if not items:
        return go.Figure()
    labels = list(items.keys())
    values = list(items.values())
    palette = ["#c9a84c","#3498db","#2ecc71","#e74c3c","#9b59b6","#1abc9c","#e67e22","#95a5a6"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=palette[:len(labels)], line=dict(color="#07080a", width=1)),
        textfont=dict(size=9, family="DM Mono"),
        hole=0.45,
    ))
    fig.update_layout(
        paper_bgcolor="#07080a", plot_bgcolor="#07080a",
        font=dict(family="DM Mono", color="#8a96a8", size=9),
        margin=dict(l=0,r=0,t=20,b=0), height=220,
        legend=dict(font=dict(size=8, color="#8a96a8"), bgcolor="rgba(0,0,0,0)"),
        title=dict(text=title, font=dict(size=9, color="#6a5a2a"), x=0),
        showlegend=True,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# LLM AGENT
# ─────────────────────────────────────────────────────────────────────────────

def ir_agent_reply(messages: list, context: dict) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        sym     = context.get("sym","")
        profile = context.get("profile",{})
        ratios  = context.get("ratios",{})
        scores  = context.get("scores",{})
        dcf     = context.get("dcf",{})
        stage   = context.get("stage",{})

        system = f"""You are an expert equity analyst at Blackwater Capital specializing in investment research.
You are currently analyzing {sym} — {profile.get('companyName','')}, a {profile.get('sector','')} company in the {profile.get('industry','')} industry.

Key data available:
- Current price: ${profile.get('price','N/A')} | Market cap: ${profile.get('mktCap',0)/1e9:.1f}B
- P/E (TTM): {ratios.get('_pe','N/A')} | P/B: {ratios.get('_pb','N/A')}
- ROE: {ratios.get('_roe','N/A')} | ROA: {ratios.get('_roa','N/A')}
- Piotroski Score: {scores.get('piotroskiScore','N/A')} | Altman Z: {scores.get('altmanZScore','N/A')}
- DCF Fair Value: ${dcf.get('dcf','N/A')} vs Current: ${dcf.get('Stock Price','N/A')}
- Stage Analysis: Stage {stage.get('stage','N/A')} — {stage.get('verdict','N/A')}

Rules:
- Answer questions strictly based on the data provided
- Be precise with numbers, always cite the metric name
- Never fabricate data or give financial advice
- If asked about a metric not in context, say it's not available
- Be concise and analytical — Bloomberg terminal style"""

        full = [{"role":"system","content":system}] + messages
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL, messages=full,
            max_tokens=600, temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[Agent error: {e}]"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fmt_num(v, prefix="$", suffix="", div=1, decimals=2):
    if v is None or v == "" or (isinstance(v, float) and np.isnan(v)):
        return "—"
    try:
        n = float(v) / div
        if abs(n) >= 1e12: return f"{prefix}{n/1e12:.{decimals}f}T{suffix}"
        if abs(n) >= 1e9:  return f"{prefix}{n/1e9:.{decimals}f}B{suffix}"
        if abs(n) >= 1e6:  return f"{prefix}{n/1e6:.{decimals}f}M{suffix}"
        return f"{prefix}{n:,.{decimals}f}{suffix}"
    except:
        return str(v)

def kpi(col, cls, lbl, val, sub=""):
    with col:
        st.markdown(f'<div class="ir-kpi {cls}"><div class="lbl">{lbl}</div>'
                    f'<div class="val">{val}</div><div class="sub">{sub}</div></div>',
                    unsafe_allow_html=True)

def sec(label):
    st.markdown(f'<div class="ir-sec">{label}</div>', unsafe_allow_html=True)

def fin_row(label, *vals):
    cols = st.columns([2] + [1]*len(vals))
    cols[0].markdown(f'<span style="font-family:\'DM Mono\',monospace;font-size:.70rem;color:#4a5568">{label}</span>',
                     unsafe_allow_html=True)
    for c, v in zip(cols[1:], vals):
        color = "#2ecc71" if isinstance(v, (int,float)) and v > 0 else "#e74c3c" if isinstance(v,(int,float)) and v < 0 else "#8a96a8"
        c.markdown(f'<span style="font-family:\'DM Mono\',monospace;font-size:.70rem;color:{color}">{v}</span>',
                   unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render_investment_research():
    st.markdown(IR_CSS, unsafe_allow_html=True)

    ts = datetime.now().strftime("%d %b %Y · %H:%M")
    st.markdown(f"""
    <div class="ir-topbar">
      <span class="ir-wordmark">Blackwater One</span>
      <div class="ir-sep"></div>
      <span class="ir-subtitle">Investment Research</span>
      <div class="ir-sep"></div>
      <span style="font-family:'DM Mono',monospace;font-size:.50rem;color:#4a3a1a;
                   border:1px solid #2a1800;padding:2px 8px">POWERED BY FMP</span>
      <span class="ir-ts">{ts}</span>
    </div>
    <div style="height:12px"></div>""", unsafe_allow_html=True)

    # ── Back button ───────────────────────────────────────────────────────────
    if st.button("← Back", key="ir_back"):
        st.session_state.page = "eagle"
        st.rerun()

    # ── Search bar — no dropdown, just type ticker and press Enter ──────────
    sec("Stock Search")
    sc1, sc2, _ = st.columns([2, 0.6, 2.4])
    with sc1:
        query = st.text_input("", placeholder="Enter ticker symbol (e.g. AAPL, MSFT, RELIANCE.NS)…",
                              key="ir_query", label_visibility="collapsed")
    with sc2:
        search_btn = st.button("Search →", use_container_width=True, key="ir_search_btn")

    # Resolve symbol — button click or Enter (query changed)
    if search_btn and query:
        new_sym = query.upper().strip()
        if new_sym != st.session_state.get("ir_sym", ""):
            st.session_state.ir_sym = new_sym
            # Clear all cached data for new symbol
            for k in [f"ir_chat_{new_sym}"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    elif query and not st.session_state.get("ir_sym"):
        st.session_state.ir_sym = query.upper().strip()

    sym = st.session_state.get("ir_sym", "").upper().strip()

    # If query differs from loaded sym, user wants a new stock — update on Enter
    if query and query.upper().strip() != sym and search_btn:
        sym = query.upper().strip()
        st.session_state.ir_sym = sym
        st.rerun()

    if not sym:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;font-family:'DM Mono',monospace;
                    font-size:.70rem;color:#2a2000;letter-spacing:.1em">
          ENTER A STOCK SYMBOL OR COMPANY NAME TO BEGIN RESEARCH
        </div>""", unsafe_allow_html=True)
        return

    # ── Load all data ─────────────────────────────────────────────────────────
    # Clear caches if symbol changed since last load
    if st.session_state.get("ir_last_sym") != sym:
        get_profile.clear()
        get_price_history.clear()
        get_peers.clear()
        get_income.clear()
        get_balance.clear()
        get_cashflow.clear()
        get_scores.clear()
        get_ratios.clear()
        get_dcf.clear()
        get_estimates.clear()
        get_earnings.clear()
        get_dividends.clear()
        get_owner_earnings.clear()
        get_ev.clear()
        get_rev_product.clear()
        get_rev_geo.clear()
        get_news.clear()
        st.session_state.ir_last_sym = sym

    with st.spinner(f"Loading research data for {sym}…"):
        profile   = get_profile(sym)
        price_df  = get_price_history(sym)
        peers     = get_peers(sym)
        inc_df    = get_income(sym)
        bal_df    = get_balance(sym)
        cf_df     = get_cashflow(sym)
        scores    = get_scores(sym)
        ratios    = get_ratios(sym)
        dcf       = get_dcf(sym)
        estimates = get_estimates(sym)
        earnings  = get_earnings(sym)
        dividends = get_dividends(sym)
        rev_prod  = get_rev_product(sym)
        rev_geo   = get_rev_geo(sym)
        news      = get_news(sym)
        oe_df     = get_owner_earnings(sym)
        ev_df     = get_ev(sym)

    if not profile:
        st.error(f"No data found for **{sym}**. Check the ticker and try again.")
        return

    # Run Weinstein analysis
    stage_data = weinstein_analysis(price_df)
    stage_data["sym"] = sym

    # ── 2-column layout: Main | Agent ─────────────────────────────────────────
    main_col, agent_col = st.columns([3.2, 1.0], gap="medium")

    with main_col:
        # ── Company header + profile card ─────────────────────────────────────
        price      = float(profile.get("price", 0) or 0)
        chg        = float(profile.get("change", profile.get("changes", 0)) or 0)
        chg_pct    = float(profile.get("changePercentage", 0) or 0)
        chg_color  = "#2ecc71" if chg >= 0 else "#e74c3c"
        chg_arrow  = "▲" if chg >= 0 else "▼"
        chg_cl     = "green" if chg >= 0 else "red"
        logo       = profile.get("image", "")
        name       = profile.get("companyName", sym)
        exchange   = profile.get("exchange", profile.get("exchangeShortName", ""))
        sector     = profile.get("sector", "")
        industry   = profile.get("industry", "")
        country    = profile.get("country", "")
        ceo        = profile.get("ceo", "")
        employees  = profile.get("fullTimeEmployees", "")
        website    = profile.get("website", "")
        ipo        = profile.get("ipoDate", "")
        mktcap     = float(profile.get("marketCap", profile.get("mktCap", 0)) or 0)
        rng        = profile.get("range", "")
        currency   = profile.get("currency", "USD")
        description= profile.get("description", "")
        avg_vol    = profile.get("averageVolume", 0) or 0

        def fmt_emp(e):
            try: return f"{int(str(e).replace(',','').strip()):,}"
            except: return str(e) if e else "—"

        logo_html = (f'<img src="{logo}" style="width:60px;height:60px;object-fit:contain;'
                     f'background:#fff;border-radius:6px;padding:4px;border:1px solid #2a2000">')  if logo else (
                     f'<div style="width:60px;height:60px;background:#1a1500;border:1px solid #2a2000;'
                     f'border-radius:6px;display:flex;align-items:center;justify-content:center;'
                     f'font-family:Bebas Neue;font-size:1.4rem;color:#c9a84c">{sym[:2]}</div>')

        desc_html = (f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid #1a1500;'
                     f'font-family:DM Sans,sans-serif;font-size:.78rem;color:#6a7a8a;line-height:1.75">'
                     f'{description}</div>') if description else ""

        web_display = website.replace("https://","").replace("http://","").rstrip("/") if website else "—"
        web_link    = f'<a href="{website}" target="_blank" style="color:#c9a84c;text-decoration:none">{web_display}</a>' if website else "—"

        info_rows = [
            ("Market Cap",  fmt_num(mktcap, "$", "", 1, 1)),
            ("52W Range",   rng or "—"),
            ("Avg Volume",  f"{int(avg_vol):,}" if avg_vol else "—"),
            ("CEO",         ceo or "—"),
            ("Employees",   fmt_emp(employees)),
            ("IPO Date",    ipo or "—"),
            ("Website",     web_link),
        ]
        info_grid = "".join(
            f'<span style="font-family:DM Mono,monospace;font-size:.58rem;color:#4a5568">{k}</span>'
            f'<span style="font-family:DM Mono,monospace;font-size:.58rem;color:#e8ecf0">{v}</span>'
            for k, v in info_rows
        )

        st.markdown(f"""
        <div style="background:#0d0f12;border:1px solid #1e2530;border-top:2px solid #c9a84c;
                    padding:16px 20px;margin-bottom:10px">
          <div style="display:flex;align-items:flex-start;gap:16px">
            <div style="flex-shrink:0">{logo_html}</div>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
                <span style="font-family:'Bebas Neue',sans-serif;font-size:1.9rem;
                             color:#e8c97e;letter-spacing:.07em;line-height:1">{name}</span>
                <span style="font-family:'DM Mono',monospace;font-size:.62rem;color:#4a3a1a">{sym}</span>
              </div>
              <div style="font-family:'DM Mono',monospace;font-size:.58rem;color:#3a2a10;
                          letter-spacing:.10em;margin-top:4px">
                {exchange} &nbsp;·&nbsp; {sector} &nbsp;·&nbsp; {industry} &nbsp;·&nbsp; {country}
              </div>
              <div style="display:flex;gap:24px;margin-top:12px;flex-wrap:wrap;align-items:flex-start">
                <div>
                  <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;
                               color:#e8ecf0;line-height:1">{currency} {price:,.2f}</div>
                  <div style="font-family:'DM Mono',monospace;font-size:.68rem;
                               color:{chg_color};margin-top:3px">
                    {chg_arrow} {abs(chg):.2f} &nbsp;({abs(chg_pct):.2f}%)
                  </div>
                </div>
                <div style="border-left:1px solid #1e2530;padding-left:20px;
                            display:grid;grid-template-columns:auto auto;gap:4px 18px">
                  {info_grid}
                </div>
              </div>
            </div>
          </div>
          {desc_html}
        </div>""", unsafe_allow_html=True)

        # ── KPI row ───────────────────────────────────────────────────────────
        k1,k2,k3,k4,k5,k6 = st.columns(6)
        kpi(k1, "gold",  "Market Cap",  fmt_num(mktcap, "$", "", 1, 1), "")
        kpi(k2, "",      "P/E (TTM)",   fmt_num(ratios.get("_pe"), "", "", 1, 1), "Ratio")
        kpi(k3, "",      "P/B",         fmt_num(ratios.get("_pb"), "", "", 1, 2), "Ratio")
        kpi(k4, "",      "EV/EBITDA",   fmt_num(ratios.get("_evm"), "", "", 1, 1), "TTM")
        kpi(k5, chg_cl,  "Beta",        fmt_num(profile.get("beta"), "", "", 1, 2), "vs Market")
        kpi(k6, "",      "Last Div",    fmt_num(profile.get("lastDividend"), "$", "", 1, 2), "Per share")

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        # ── Price chart ───────────────────────────────────────────────────────
        sec("Price Chart · 2 Years")
        show_stage = st.toggle("📐 Stage Analysis (Weinstein)", value=False, key="ir_stage")

        if not price_df.empty:
            fig = build_price_chart(price_df, sym, stage_data, show_stage)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Stage analysis panel
        if show_stage and stage_data.get("stage", 0) > 0:
            stage = stage_data["stage"]
            verdict = stage_data["verdict"]
            stage_names = {1:"Stage 1 — Basing", 2:"Stage 2 — Advancing",
                           3:"Stage 3 — Topping", 4:"Stage 4 — Declining"}
            verdict_cls = {"BUY":"verdict-buy","HOLD":"verdict-hold","SELL / AVOID":"verdict-sell",
                           "WAIT":"verdict-wait","HOLD / REDUCE":"verdict-hold"}.get(verdict,"verdict-hold")

            s1,s2,s3,s4,s5 = st.columns(5)
            kpi(s1, f"stage-{stage} ir-kpi", "Weinstein Stage", stage_names.get(stage, f"Stage {stage}"), "")
            kpi(s2, "", "Verdict",   f'<span class="{verdict_cls}">{verdict}</span>', "")
            kpi(s3, "", "30W MA",    f"${stage_data['ma30']:.2f}", "Support line")
            kpi(s4, "", "MA Slope",  f"{stage_data['ma30_slope']*100:+.2f}%", "Monthly")
            kpi(s5, "", "Vol Ratio", f"{stage_data['vol_ratio']:.2f}x", "vs 10-wk avg")

            st.markdown(f'<div class="ir-card" style="border-left:2px solid var(--gold);margin-top:4px">'
                        f'<b style="color:#e8c97e">Weinstein Analysis:</b> {stage_data["detail"]}</div>',
                        unsafe_allow_html=True)

        # ── Peer comparison ───────────────────────────────────────────────────
        if peers:
            sec(f"Peer Comparison — {profile.get('industry','')}")
            peer_data = []
            for p in peers[:6]:
                pr = get_profile(p)
                if pr:
                    peer_data.append({
                        "Ticker": p,
                        "Name":   pr.get("companyName","")[:25],
                        "Price":  f"${pr.get('price',0):,.2f}",
                        "Mkt Cap":fmt_num(pr.get("mktCap",0),"$","",1,1),
                        "P/E":    fmt_num(pr.get("pe",None),"","",1,1),
                        "Beta":   fmt_num(pr.get("beta",None),"","",1,2),
                    })
            if peer_data:
                pdf = pd.DataFrame(peer_data)
                st.dataframe(pdf, use_container_width=True, hide_index=True,
                             height=min(len(peer_data)*38+40, 280))

        # ── Financials ────────────────────────────────────────────────────────
        sec("Financials — Historical (5 Years) + TTM")
        ft1, ft2, ft3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

        with ft1:
            if not inc_df.empty:
                st.plotly_chart(build_financials_chart(inc_df), use_container_width=True,
                                config={"displayModeBar": False})
                yrs = inc_df["date"].astype(str).str[:4].tolist()[:5]
                rows = [
                    ("Revenue",        [fmt_num(inc_df.iloc[i].get("revenue"),      "$","",1e9,2)+"B" for i in range(min(5,len(inc_df)))]),
                    ("Gross Profit",   [fmt_num(inc_df.iloc[i].get("grossProfit"),  "$","",1e9,2)+"B" for i in range(min(5,len(inc_df)))]),
                    ("Op. Income",     [fmt_num(inc_df.iloc[i].get("operatingIncome"),"$","",1e9,2)+"B" for i in range(min(5,len(inc_df)))]),
                    ("Net Income",     [fmt_num(inc_df.iloc[i].get("netIncome"),     "$","",1e9,2)+"B" for i in range(min(5,len(inc_df)))]),
                    ("EPS",            [fmt_num(inc_df.iloc[i].get("eps"),           "$","",1,2)      for i in range(min(5,len(inc_df)))]),
                    ("EBITDA",         [fmt_num(inc_df.iloc[i].get("ebitda"),        "$","",1e9,2)+"B" for i in range(min(5,len(inc_df)))]),
                ]
                fin_row("Year", *yrs)
                st.markdown('<hr style="border-color:#1e2530;margin:4px 0">', unsafe_allow_html=True)
                for label, vals in rows:
                    fin_row(label, *vals)

        with ft2:
            if not bal_df.empty:
                yrs = bal_df["date"].astype(str).str[:4].tolist()[:5]
                rows = [
                    ("Total Assets",   [fmt_num(bal_df.iloc[i].get("totalAssets"),       "$","",1e9,1)+"B" for i in range(min(5,len(bal_df)))]),
                    ("Total Liab.",    [fmt_num(bal_df.iloc[i].get("totalLiabilities"),   "$","",1e9,1)+"B" for i in range(min(5,len(bal_df)))]),
                    ("Total Equity",   [fmt_num(bal_df.iloc[i].get("totalStockholdersEquity"),"$","",1e9,1)+"B" for i in range(min(5,len(bal_df)))]),
                    ("Cash & Equiv.",  [fmt_num(bal_df.iloc[i].get("cashAndCashEquivalents"),"$","",1e9,1)+"B" for i in range(min(5,len(bal_df)))]),
                    ("Total Debt",     [fmt_num(bal_df.iloc[i].get("totalDebt"),           "$","",1e9,1)+"B" for i in range(min(5,len(bal_df)))]),
                    ("Net Debt",       [fmt_num(bal_df.iloc[i].get("netDebt"),             "$","",1e9,1)+"B" for i in range(min(5,len(bal_df)))]),
                ]
                fin_row("Year", *yrs)
                st.markdown('<hr style="border-color:#1e2530;margin:4px 0">', unsafe_allow_html=True)
                for label, vals in rows:
                    fin_row(label, *vals)

        with ft3:
            if not cf_df.empty:
                yrs = cf_df["date"].astype(str).str[:4].tolist()[:5]
                rows = [
                    ("Operating CF",   [fmt_num(cf_df.iloc[i].get("operatingCashFlow") or cf_df.iloc[i].get("netCashProvidedByOperatingActivities"),         "$","",1e9,1)+"B" for i in range(min(5,len(cf_df)))]),
                    ("Investing CF",   [fmt_num(cf_df.iloc[i].get("netCashProvidedByInvestingActivities") or cf_df.iloc[i].get("investingActivitiesCashFlow"),"$","",1e9,1)+"B" for i in range(min(5,len(cf_df)))]),
                    ("Financing CF",   [fmt_num(cf_df.iloc[i].get("netCashProvidedByFinancingActivities") or cf_df.iloc[i].get("financingActivitiesCashFlow"),"$","",1e9,1)+"B" for i in range(min(5,len(cf_df)))]),
                    ("Free Cash Flow", [fmt_num(cf_df.iloc[i].get("freeCashFlow"),               "$","",1e9,1)+"B" for i in range(min(5,len(cf_df)))]),
                    ("CapEx",          [fmt_num(cf_df.iloc[i].get("capitalExpenditure") or cf_df.iloc[i].get("investmentsInPropertyPlantAndEquipment"),          "$","",1e9,1)+"B" for i in range(min(5,len(cf_df)))]),
                    ("Dividends Paid", [fmt_num(cf_df.iloc[i].get("commonDividendsPaid") or cf_df.iloc[i].get("netDividendsPaid"),                              "$","",1e9,1)+"B" for i in range(min(5,len(cf_df)))]),
                ]
                fin_row("Year", *yrs)
                st.markdown('<hr style="border-color:#1e2530;margin:4px 0">', unsafe_allow_html=True)
                for label, vals in rows:
                    fin_row(label, *vals)

        # ── Financial scores & ratios ─────────────────────────────────────────
        sec("Financial Health Scores")
        sc1,sc2,sc3,sc4 = st.columns(4)
        pf = scores.get("piotroskiScore") or scores.get("piotroski_score")
        az = scores.get("altmanZScore") or scores.get("altman_z_score")
        bm = scores.get("beneishMScore") or scores.get("beneish_m_score") or scores.get("beneishScore")
        wc = scores.get("workingCapital")
        kpi(sc1, "gold", "Piotroski F-Score", str(int(pf)) if pf is not None else "—", "Max 9 · Quality")
        kpi(sc2, "",     "Altman Z-Score",    f"{float(az):.2f}" if az is not None else "—", ">2.99 safe zone")
        kpi(sc3, "",     "Beneish M-Score",   f"{float(bm):.3f}" if bm is not None else "—", "<-1.78 no fraud")
        kpi(sc4, "",     "Working Capital",   fmt_num(wc,"$","",1e9,1)+"B" if wc else "—", "")

        sec("Key Ratios (TTM)")
        r1,r2,r3,r4,r5,r6 = st.columns(6)
        def pct_ratio(v):
            if v is None or v == "": return "—"
            try:
                f = float(v)
                # FMP returns margins as decimals e.g. 0.465 = 46.5%
                return f"{f*100:.1f}%" if abs(f) <= 1 else f"{f:.1f}%"
            except: return "—"
        # TTM endpoint has margins; annual ratios endpoint has ROE/ROA/D-E
        roe = ratios.get("_roe")
        roa = ratios.get("_roa")
        de  = ratios.get("_de")
        kpi(r1, "", "ROE",          pct_ratio(roe), "Return on Equity")
        kpi(r2, "", "ROA",          pct_ratio(roa), "Return on Assets")
        kpi(r3, "", "Gross Margin", pct_ratio(ratios.get("grossProfitMarginTTM") or ratios.get("grossProfitMargin")), "")
        kpi(r4, "", "Net Margin",   pct_ratio(ratios.get("netProfitMarginTTM") or ratios.get("netProfitMargin")), "")
        kpi(r5, "", "Current Ratio",fmt_num(ratios.get("currentRatioTTM") or ratios.get("currentRatio"),"","",1,2), "Liquidity")
        kpi(r6, "", "Debt/Equity",  fmt_num(de,"","",1,2), "Leverage")

        # ── DCF Valuation ─────────────────────────────────────────────────────
        if dcf:
            sec("DCF Valuation")
            dcf_price = dcf.get("dcf", 0)
            cur_price = dcf.get("Stock Price", profile.get("price", 0))
            upside    = ((dcf_price - cur_price) / cur_price * 100) if cur_price else 0
            d1,d2,d3,d4 = st.columns(4)
            kpi(d1, "gold",               "DCF Fair Value",  f"${float(dcf_price):,.2f}", "Intrinsic value")
            kpi(d2, "",                   "Current Price",   f"${float(cur_price):,.2f}", "Market price")
            kpi(d3, "green" if upside>0 else "red", "Upside / Downside", f"{upside:+.1f}%", "vs DCF")
            kpi(d4, "",                   "Date",            dcf.get("date","—")[:10], "Estimate")

        # ── Analyst Estimates ─────────────────────────────────────────────────
        if not estimates.empty:
            sec("Analyst Estimates — Next 3 Years")
            # FMP analyst-estimates field names (from API docs)
            est_show = estimates.head(6).copy()
            rename_map = {
                "date":             "Year",
                "revenueAvg":       "Est. Revenue",
                "revenueLow":       "Rev. Low",
                "revenueHigh":      "Rev. High",
                "epsAvg":           "Est. EPS",
                "epsLow":           "EPS Low",
                "epsHigh":          "EPS High",
                "netIncomeAvg":     "Est. Net Inc.",
                "ebitdaAvg":        "Est. EBITDA",
                "numAnalystsRevenue": "# Analysts",
                "numAnalystsEps":     "# EPS Analysts",
            }
            est_show = est_show.rename(columns=rename_map)
            if "Year" in est_show.columns:
                est_show["Year"] = est_show["Year"].astype(str).str[:4]
            # Format large numbers as billions
            for col in ["Est. Revenue","Rev. Low","Rev. High","Est. Net Inc.","Est. EBITDA"]:
                if col in est_show.columns:
                    est_show[col] = est_show[col].apply(
                        lambda x: f"${float(x)/1e9:.2f}B" if pd.notna(x) and x not in (0,"") else "—")
            for col in ["Est. EPS","EPS Low","EPS High"]:
                if col in est_show.columns:
                    est_show[col] = est_show[col].apply(
                        lambda x: f"${float(x):.2f}" if pd.notna(x) and x not in (0,"") else "—")
            keep = [c for c in ["Year","Est. Revenue","Est. EPS","EPS Low","EPS High","Est. Net Inc.","# Analysts"] if c in est_show.columns]
            st.dataframe(est_show[keep] if keep else est_show, use_container_width=True, hide_index=True, height=200)

        # ── Earnings & Dividends ──────────────────────────────────────────────
        ed1, ed2 = st.columns(2)
        with ed1:
            sec("Earnings History")
            if not earnings.empty:
                earn_cols = [c for c in ["date","eps","epsEstimated","revenue"] if c in earnings.columns]
                st.dataframe(earnings[earn_cols].head(8), use_container_width=True,
                             hide_index=True, height=200)
        with ed2:
            sec("Dividend History")
            if not dividends.empty:
                div_cols = [c for c in ["date","dividend","adjDividend","paymentDate"] if c in dividends.columns]
                st.dataframe(dividends[div_cols].head(8), use_container_width=True,
                             hide_index=True, height=200)

        # ── Revenue segmentation ──────────────────────────────────────────────
        if rev_prod or rev_geo:
            seg1, seg2 = st.columns(2)
            with seg1:
                sec("Revenue by Product")
                if rev_prod:
                    ch = build_seg_chart(rev_prod, "Product Segments")
                    if ch.data:
                        st.plotly_chart(ch, use_container_width=True, config={"displayModeBar":False})
            with seg2:
                sec("Revenue by Geography")
                if rev_geo:
                    ch = build_seg_chart(rev_geo, "Geographic Segments")
                    if ch.data:
                        st.plotly_chart(ch, use_container_width=True, config={"displayModeBar":False})

        # ── Sector/Industry PE ────────────────────────────────────────────────
        sector   = profile.get("sector","")
        industry = profile.get("industry","")
        if sector or industry:
            sec(f"P/E Context — {sector} Sector & {industry} Industry")
            pe1, pe2 = st.columns(2)
            with pe1:
                spe = get_sector_pe(sector)
                if not spe.empty:
                    ch = build_pe_chart(spe, f"{sector} Sector P/E")
                    if ch.data:
                        st.plotly_chart(ch, use_container_width=True, config={"displayModeBar":False})
            with pe2:
                ipe = get_industry_pe(industry)
                if not ipe.empty:
                    ch = build_pe_chart(ipe, f"{industry} Industry P/E")
                    if ch.data:
                        st.plotly_chart(ch, use_container_width=True, config={"displayModeBar":False})

        # ── Owner Earnings & Enterprise Value ─────────────────────────────────
        if not oe_df.empty or not ev_df.empty:
            oe1, oe2 = st.columns(2)
            with oe1:
                if not oe_df.empty:
                    sec("Owner Earnings (Buffett Method)")
                    oe_show = oe_df[["date","ownerEarnings","averageInvestment","growthCapex"]
                                    ].head(5) if all(c in oe_df.columns for c in ["ownerEarnings","averageInvestment","growthCapex"]) else oe_df.head(5)
                    st.dataframe(oe_show, use_container_width=True, hide_index=True, height=180)
            with oe2:
                if not ev_df.empty:
                    sec("Enterprise Value History")
                    ev_show = ev_df[["date","enterpriseValue","evToFreeCashFlow","evToOperatingCashFlow"]
                                    ].head(5) if all(c in ev_df.columns for c in ["enterpriseValue","evToFreeCashFlow","evToOperatingCashFlow"]) else ev_df.head(5)
                    st.dataframe(ev_show, use_container_width=True, hide_index=True, height=180)

        # ── Stock News ────────────────────────────────────────────────────────
        sec(f"Latest News — {sym}")
        if news:
            for a in news[:15]:
                title  = a.get("title","")
                url    = a.get("url","#")
                src    = a.get("site","") or a.get("symbol","")
                date   = (a.get("publishedDate","") or "")[:10]
                st.markdown(f"""
                <div class="news-item">
                  <div class="news-title"><a href="{url}" target="_blank">{title}</a></div>
                  <div class="news-meta">{date} · {src}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.caption("No recent news available.")

    # ── Agent sidebar ─────────────────────────────────────────────────────────
    with agent_col:
        st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-hdr">🔬 Research Agent · {sym}</div>', unsafe_allow_html=True)

        # Init chat history per symbol
        chat_key = f"ir_chat_{sym}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []

        # Chat history
        chat_container = st.container()
        with chat_container:
            if not st.session_state[chat_key]:
                st.markdown(f"""
                <div class="chat-bubble-a">
                  Hello. I'm your research agent for <b style="color:#e8c97e">{sym}</b>.<br><br>
                  I have access to all data on this page — financials, ratios, stage analysis,
                  DCF, earnings, and more. Ask me anything.
                </div>""", unsafe_allow_html=True)
            for m in st.session_state[chat_key]:
                cls = "chat-bubble-u" if m["role"] == "user" else "chat-bubble-a"
                st.markdown(f'<div class="{cls}">{m["content"]}</div>', unsafe_allow_html=True)

        # Input
        user_input = st.chat_input("Ask about this stock…", key=f"ir_input_{sym}")
        if user_input:
            st.session_state[chat_key].append({"role":"user","content":user_input})
            ctx = {"sym":sym,"profile":profile,"ratios":ratios,"scores":scores,
                   "dcf":dcf,"stage":stage_data}
            with st.spinner("Analyzing…"):
                reply = ir_agent_reply(st.session_state[chat_key], ctx)
            st.session_state[chat_key].append({"role":"assistant","content":reply})
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
