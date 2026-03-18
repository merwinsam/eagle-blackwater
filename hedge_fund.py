"""
Blackwater One — AI Hedge Fund
Multi-agent pipeline: Market Data → Sentiment → Fundamentals → Quant → Risk → Portfolio
Each agent runs once, passes a structured signal forward. Clean, lean, no redundant API calls.
"""

import streamlit as st
import requests
import json
from datetime import datetime
from openai import OpenAI
import config

API   = config.FMP_API_KEY
BASE  = "https://financialmodelingprep.com/stable"

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
HF_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --hf-bg:     #050607;
  --hf-bg1:    #0a0c0f;
  --hf-bg2:    #0f1215;
  --hf-border: #1a1f28;
  --hf-gold:   #c9a84c;
  --hf-green:  #2ecc71;
  --hf-red:    #e74c3c;
  --hf-amber:  #f39c12;
  --hf-blue:   #3498db;
  --hf-purple: #9b59b6;
  --hf-txt:    #dde4ed;
  --hf-txt2:   #6a7a8a;
  --hf-txt3:   #2a3540;
}

.hf-topbar {
  background:#000;border-bottom:2px solid var(--hf-gold);
  padding:0 20px;height:48px;display:flex;align-items:center;gap:14px;
}
.hf-wordmark { font-family:'IBM Plex Mono',monospace;font-weight:600;
  font-size:1rem;color:var(--hf-gold);letter-spacing:.12em;text-transform:uppercase; }
.hf-sep { width:1px;height:20px;background:#2a1800; }
.hf-subtitle { font-family:'IBM Plex Mono',monospace;font-size:.88rem;
  color:#5a4a2a;letter-spacing:.18em;text-transform:uppercase; }
.hf-ts { font-family:'IBM Plex Mono',monospace;font-size:.86rem;
  color:#3a2a10;margin-left:auto; }

/* Pipeline track */
.hf-pipeline {
  display:flex;align-items:center;gap:0;
  background:var(--hf-bg1);border:1px solid var(--hf-border);
  padding:14px 16px;margin-bottom:12px;overflow-x:auto;
}
.hf-node {
  display:flex;flex-direction:column;align-items:center;
  min-width:90px;text-align:center;
}
.hf-node-icon {
  width:44px;height:44px;border-radius:4px;
  display:flex;align-items:center;justify-content:center;
  font-size:1.2rem;border:1px solid var(--hf-border);
  background:var(--hf-bg2);margin-bottom:5px;
  transition:all .2s;
}
.hf-node-icon.active  { border-color:var(--hf-gold);box-shadow:0 0 12px rgba(201,168,76,.2); }
.hf-node-icon.done    { border-color:var(--hf-green);box-shadow:0 0 8px rgba(46,204,113,.15); }
.hf-node-icon.running { border-color:var(--hf-amber);animation:hf-pulse 1s ease-in-out infinite; }
@keyframes hf-pulse { 0%,100%{opacity:1}50%{opacity:.5} }
.hf-node-lbl {
  font-family:'IBM Plex Mono',monospace;font-size:.66rem;
  color:var(--hf-txt2);text-transform:uppercase;letter-spacing:.10em;line-height:1.3;
}
.hf-arrow {
  color:var(--hf-border);font-size:1.2rem;padding:0 4px;flex-shrink:0;
  margin-bottom:18px;
}
.hf-arrow.lit { color:var(--hf-gold); }

/* Signal cards */
.hf-signal {
  background:var(--hf-bg1);border:1px solid var(--hf-border);
  border-left:3px solid var(--hf-border);
  padding:12px 16px;margin-bottom:6px;
  font-family:'IBM Plex Sans',sans-serif;
  transition:border-left-color .2s;
}
.hf-signal.done  { border-left-color:var(--hf-green); }
.hf-signal.warn  { border-left-color:var(--hf-amber); }
.hf-signal.risk  { border-left-color:var(--hf-red); }
.hf-signal.info  { border-left-color:var(--hf-blue); }
.hf-signal.quant { border-left-color:var(--hf-purple); }

.hf-agent-name {
  font-family:'IBM Plex Mono',monospace;font-size:.88rem;
  color:var(--hf-gold);text-transform:uppercase;letter-spacing:.14em;
  margin-bottom:5px;display:flex;align-items:center;gap:8px;
}
.hf-signal-body {
  font-size:1.0rem;color:var(--hf-txt2);line-height:1.65;
}
.hf-signal-body b { color:var(--hf-txt); }

/* Verdict */
.hf-verdict {
  padding:20px 24px;text-align:center;
  background:var(--hf-bg1);border:1px solid var(--hf-border);
  border-top:3px solid var(--hf-gold);
}
.hf-verdict-action {
  font-family:'IBM Plex Mono',monospace;font-size:2.8rem;
  font-weight:600;letter-spacing:.08em;line-height:1;
  margin-bottom:8px;
}
.hf-verdict-action.BUY  { color:var(--hf-green); }
.hf-verdict-action.SELL { color:var(--hf-red);   }
.hf-verdict-action.HOLD { color:var(--hf-amber); }
.hf-verdict-sub {
  font-family:'IBM Plex Mono',monospace;font-size:.94rem;
  color:var(--hf-txt2);letter-spacing:.10em;text-transform:uppercase;
}
.hf-verdict-reason {
  font-family:'IBM Plex Sans',sans-serif;font-size:1.0rem;
  color:var(--hf-txt2);line-height:1.7;margin-top:12px;
  border-top:1px solid var(--hf-border);padding-top:12px;
}

/* Confidence bar */
.hf-conf-bar-bg {
  background:var(--hf-bg2);border-radius:2px;height:6px;
  width:100%;margin-top:8px;
}
.hf-conf-bar-fill {
  height:6px;border-radius:2px;transition:width .6s ease;
}

/* KPI strip */
.hf-kpi-row { display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap; }
.hf-kpi {
  background:var(--hf-bg1);border:1px solid var(--hf-border);
  border-top:2px solid var(--hf-border);
  padding:8px 12px;flex:1;min-width:100px;text-align:center;
}
.hf-kpi.gold  { border-top-color:var(--hf-gold); }
.hf-kpi.green { border-top-color:var(--hf-green); }
.hf-kpi.red   { border-top-color:var(--hf-red); }
.hf-kpi.blue  { border-top-color:var(--hf-blue); }
.hf-kpi .lbl {
  font-family:'IBM Plex Mono',monospace;font-size:.98rem;
  color:var(--hf-txt3);text-transform:uppercase;letter-spacing:.12em;margin-bottom:3px;
}
.hf-kpi .val {
  font-family:'IBM Plex Mono',monospace;font-size:1.1rem;
  font-weight:600;color:var(--hf-txt);line-height:1;
}
.hf-kpi.gold  .val { color:var(--hf-gold); }
.hf-kpi.green .val { color:var(--hf-green); }
.hf-kpi.red   .val { color:var(--hf-red); }
.hf-kpi.blue  .val { color:var(--hf-blue); }

/* Log */
.hf-log {
  font-family:'IBM Plex Mono',monospace;font-size:.92rem;
  color:var(--hf-txt3);line-height:1.8;
  background:var(--hf-bg1);border:1px solid var(--hf-border);
  padding:10px 14px;max-height:160px;overflow-y:auto;
}
.hf-log .ok   { color:#2a6a3a; }
.hf-log .warn { color:#6a4a10; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHERS — single call per type, cached
# ─────────────────────────────────────────────────────────────────────────────

def fmp(endpoint):
    try:
        sep = "&" if "?" in endpoint else "?"
        r = requests.get(f"{BASE}/{endpoint}{sep}apikey={API}", timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[hf] FMP {endpoint}: {e}")
    return None

@st.cache_data(ttl=300, show_spinner=False)
def hf_market_data(sym):
    """One call — profile + latest price."""
    return fmp(f"profile?symbol={sym}")

@st.cache_data(ttl=600, show_spinner=False)
def hf_price_history(sym):
    """EOD price history for quant signals."""
    d = fmp(f"historical-price-eod/full?symbol={sym}&limit=60")
    if not d: return []
    return d if isinstance(d, list) else d.get("historical", [])

@st.cache_data(ttl=600, show_spinner=False)
def hf_fundamentals(sym):
    """Income + ratios in two calls."""
    ratios = fmp(f"ratios?symbol={sym}&limit=1")
    scores = fmp(f"financial-scores?symbol={sym}")
    return ratios, scores

@st.cache_data(ttl=600, show_spinner=False)
def hf_sentiment(sym):
    """Latest stock news for sentiment."""
    return fmp(f"news/stock?symbols={sym}&limit=15")

@st.cache_data(ttl=600, show_spinner=False)
def hf_analyst(sym):
    """Analyst estimates + DCF."""
    estimates = fmp(f"analyst-estimates?symbol={sym}&period=annual&limit=2")
    dcf       = fmp(f"discounted-cash-flow?symbol={sym}")
    return estimates, dcf

# ─────────────────────────────────────────────────────────────────────────────
# QUANT SIGNALS — computed locally, no API call
# ─────────────────────────────────────────────────────────────────────────────

def compute_quant_signals(price_data):
    """MA20/MA50 crossover, RSI, momentum. Returns dict of signals."""
    try:
        # Handle both list and dict responses from FMP
        if isinstance(price_data, list):
            records = price_data
        elif isinstance(price_data, dict):
            records = price_data.get("historical", price_data.get("data", []))
        else:
            return {"error": "No price data returned"}

        if not records or len(records) < 21:
            return {"error": "Insufficient price history"}

        # Extract closes — try multiple field names, skip zeros
        raw = []
        for r in reversed(records):
            v = r.get("close") or r.get("adjClose") or r.get("adj_close") or r.get("price")
            try:
                f = float(v)
                if f > 0:
                    raw.append(f)
            except (TypeError, ValueError):
                pass

        closes = raw
        if len(closes) < 21:
            return {"error": "Could not extract valid close prices"}

        ma20  = sum(closes[-20:]) / 20
        ma50  = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
        cur   = closes[-1]
        c6    = closes[-6]  if len(closes) >= 6  else None
        c21   = closes[-21] if len(closes) >= 21 else None
        mom5  = (cur - c6)  / c6  * 100 if c6  and c6  != 0 else 0
        mom20 = (cur - c21) / c21 * 100 if c21 and c21 != 0 else 0

        # RSI-14 — guard against all-gain or all-loss windows
        gains, losses = [], []
        for i in range(-14, 0):
            d = closes[i] - closes[i-1]
            if d > 0:   gains.append(d)
            else:       losses.append(abs(d))
        avg_g = sum(gains)  / 14 if gains  else 0
        avg_l = sum(losses) / 14 if losses else 0
        if avg_l == 0:
            rsi = 100.0          # all gains — extremely overbought
        elif avg_g == 0:
            rsi = 0.0            # all losses — extremely oversold
        else:
            rsi = 100 - (100 / (1 + avg_g / avg_l))

        above_ma20 = cur > ma20
        above_ma50 = cur > ma50 if ma50 else None
        ma_cross   = "BULLISH" if (ma20 > ma50) else "BEARISH" if ma50 else "N/A"

        signal = "BUY" if (rsi < 70 and above_ma20 and mom20 > 0) else \
                 "SELL" if (rsi > 75 or (not above_ma20 and mom20 < -5)) else "HOLD"

        return {
            "price":      round(cur, 2),
            "ma20":       round(ma20, 2),
            "ma50":       round(ma50, 2) if ma50 else None,
            "rsi":        round(rsi, 1),
            "mom5d_pct":  round(mom5, 2),
            "mom20d_pct": round(mom20, 2),
            "above_ma20": above_ma20,
            "above_ma50": above_ma50,
            "ma_cross":   ma_cross,
            "signal":     signal,
        }
    except Exception as e:
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# AGENT CALLS — one LLM call per agent, structured JSON output
# ─────────────────────────────────────────────────────────────────────────────

def llm(system: str, user: str, max_tokens=350) -> dict:
    """Single LLM call. Returns parsed JSON dict or error."""
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            max_tokens=max_tokens,
            temperature=0.2,
            response_format={"type":"json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"error": str(e), "signal": "HOLD", "confidence": 0}


def agent_market_data(sym, profile):
    """Agent 1 — Market Data Analyst. Summarises market context."""
    if not profile:
        return {"signal":"HOLD","confidence":30,"summary":"No profile data available."}
    p = profile[0] if isinstance(profile, list) else profile
    ctx = {
        "symbol":    sym,
        "price":     p.get("price"),
        "change_pct":p.get("changePercentage"),
        "mkt_cap":   p.get("marketCap"),
        "beta":      p.get("beta"),
        "range_52w": p.get("range"),
        "sector":    p.get("sector"),
        "industry":  p.get("industry"),
        "avg_volume":p.get("averageVolume"),
    }
    return llm(
        "You are a Market Data Analyst at a hedge fund. Analyse the market data and return JSON with keys: "
        "signal (BUY/HOLD/SELL), confidence (0-100), summary (2 sentences max), key_risks (list of 2).",
        f"Market data for {sym}:\n{json.dumps(ctx)}"
    )


def agent_sentiment(sym, news):
    """Agent 2 — Sentiment Analyst. Reads recent news."""
    if not news:
        return {"signal":"HOLD","confidence":40,"summary":"No news available.","tone":"NEUTRAL"}
    headlines = [f"- {a.get('title','')}" for a in (news[:10] if isinstance(news,list) else [])]
    return llm(
        "You are a Sentiment Analyst at a hedge fund. Analyse news headlines and return JSON with keys: "
        "signal (BUY/HOLD/SELL), confidence (0-100), tone (BULLISH/NEUTRAL/BEARISH), "
        "summary (2 sentences max), top_headline (most impactful headline).",
        f"Recent news for {sym}:\n" + "\n".join(headlines)
    )


def agent_fundamentals(sym, ratios, scores):
    """Agent 3 — Fundamentals Analyst."""
    r = (ratios[0] if ratios else {}) if isinstance(ratios, list) else {}
    s = (scores[0] if scores else {}) if isinstance(scores, list) else {}
    ctx = {
        "pe":              r.get("priceToEarningsRatio"),
        "pb":              r.get("priceToBookRatio"),
        "roe":             r.get("returnOnEquity"),
        "net_margin":      r.get("netProfitMargin"),
        "debt_to_equity":  r.get("debtToEquityRatio"),
        "current_ratio":   r.get("currentRatio"),
        "ev_ebitda":       r.get("enterpriseValueMultiple"),
        "piotroski":       s.get("piotroskiScore"),
        "altman_z":        s.get("altmanZScore"),
    }
    return llm(
        "You are a Fundamentals Analyst at a hedge fund. Analyse financial ratios and return JSON with keys: "
        "signal (BUY/HOLD/SELL), confidence (0-100), valuation (CHEAP/FAIR/EXPENSIVE), "
        "quality (HIGH/MEDIUM/LOW), summary (2 sentences max).",
        f"Fundamentals for {sym}:\n{json.dumps(ctx)}"
    )


def agent_quant(sym, quant):
    """Agent 4 — Quant Analyst. Uses pre-computed technical signals."""
    if "error" in quant:
        return {"signal":"HOLD","confidence":30,"summary":quant["error"],"regime":"UNKNOWN"}
    return llm(
        "You are a Quant Analyst at a hedge fund. Interpret these technical indicators and return JSON with keys: "
        "signal (BUY/HOLD/SELL), confidence (0-100), regime (TRENDING/RANGING/REVERSAL), "
        "summary (2 sentences max).",
        f"Quant signals for {sym}:\n{json.dumps(quant)}"
    )


def agent_risk(sym, market_sig, sentiment_sig, fund_sig, quant_sig, estimates, dcf):
    """Agent 5 — Risk Manager. Aggregates all signals, flags risks."""
    dcf_d   = (dcf[0]  if dcf  else {}) if isinstance(dcf,  list) else {}
    est_d   = (estimates[0] if estimates else {}) if isinstance(estimates, list) else {}
    ctx = {
        "market":      {"signal":market_sig.get("signal"),    "conf":market_sig.get("confidence")},
        "sentiment":   {"signal":sentiment_sig.get("signal"), "conf":sentiment_sig.get("confidence")},
        "fundamentals":{"signal":fund_sig.get("signal"),      "conf":fund_sig.get("confidence")},
        "quant":       {"signal":quant_sig.get("signal"),     "conf":quant_sig.get("confidence")},
        "dcf_value":   dcf_d.get("dcf"),
        "current_price":dcf_d.get("Stock Price"),
        "eps_estimate":est_d.get("epsAvg"),
    }
    votes = [ctx["market"]["signal"], ctx["sentiment"]["signal"],
             ctx["fundamentals"]["signal"], ctx["quant"]["signal"]]
    buy_votes  = votes.count("BUY")
    sell_votes = votes.count("SELL")
    hold_votes = votes.count("HOLD")
    ctx["vote_summary"] = {"BUY":buy_votes,"SELL":sell_votes,"HOLD":hold_votes}

    return llm(
        "You are a Risk Manager at a hedge fund. Review all analyst signals and return JSON with keys: "
        "risk_signal (BUY/HOLD/SELL), risk_level (LOW/MEDIUM/HIGH/EXTREME), "
        "confidence (0-100), top_risk (single biggest risk), summary (2 sentences max), "
        "position_size_pct (suggested % of portfolio: 1-10).",
        f"All signals for {sym}:\n{json.dumps(ctx)}"
    )


def agent_portfolio(sym, risk_sig, market_sig, sentiment_sig, fund_sig, quant_sig):
    """Agent 6 — Portfolio Manager. Final decision."""
    ctx = {
        "risk_signal":    risk_sig.get("risk_signal"),
        "risk_level":     risk_sig.get("risk_level"),
        "risk_confidence":risk_sig.get("confidence"),
        "position_size":  risk_sig.get("position_size_pct"),
        "market_signal":  market_sig.get("signal"),
        "sentiment_tone": sentiment_sig.get("tone"),
        "valuation":      fund_sig.get("valuation"),
        "quality":        fund_sig.get("quality"),
        "quant_regime":   quant_sig.get("regime"),
        "top_risk":       risk_sig.get("top_risk"),
    }
    return llm(
        "You are the Portfolio Manager at a hedge fund making the final trading decision. "
        "Return JSON with keys: action (BUY/HOLD/SELL), confidence (0-100), "
        "rationale (3 sentences — one for each bull/bear/risk), "
        "time_horizon (SHORT/MEDIUM/LONG term), position_size_pct (1-10), "
        "stop_loss_note (one sentence), price_target_note (one sentence).",
        f"Final brief for {sym}:\n{json.dumps(ctx)}",
        max_tokens=500
    )

# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(sym: str) -> dict:
    """
    Sequential pipeline. Fetches all data first (parallel-ish via cache),
    then runs 6 LLM agents in order. Returns full result dict.
    """
    log = []

    # ── Stage 0: Fetch all data ───────────────────────────────────────────────
    log.append(("ok",  f"[00] Fetching market data for {sym}…"))
    profile   = hf_market_data(sym)
    price_data= hf_price_history(sym)
    ratios, scores = hf_fundamentals(sym)
    news      = hf_sentiment(sym)
    estimates, dcf = hf_analyst(sym)
    log.append(("ok",  "[00] Data fetch complete."))

    # ── Stage 1: Quant (local, no LLM) ───────────────────────────────────────
    log.append(("ok",  "[01] Running quant signals…"))
    quant = compute_quant_signals(price_data)
    log.append(("ok",  f"[01] Quant: {quant.get('signal','?')} | RSI {quant.get('rsi','?')} | MA cross {quant.get('ma_cross','?')}"))

    # ── Stage 2–6: LLM agents in sequence ────────────────────────────────────
    log.append(("ok",  "[02] Market Data Analyst…"))
    market_sig = agent_market_data(sym, profile)
    log.append(("ok",  f"[02] → {market_sig.get('signal','?')} ({market_sig.get('confidence','?')}% conf)"))

    log.append(("ok",  "[03] Sentiment Analyst…"))
    sentiment_sig = agent_sentiment(sym, news)
    log.append(("ok",  f"[03] → {sentiment_sig.get('signal','?')} | tone: {sentiment_sig.get('tone','?')}"))

    log.append(("ok",  "[04] Fundamentals Analyst…"))
    fund_sig = agent_fundamentals(sym, ratios, scores)
    log.append(("ok",  f"[04] → {fund_sig.get('signal','?')} | val: {fund_sig.get('valuation','?')} | quality: {fund_sig.get('quality','?')}"))

    log.append(("ok",  "[05] Quant Analyst…"))
    quant_sig = agent_quant(sym, quant)
    log.append(("ok",  f"[05] → {quant_sig.get('signal','?')} | regime: {quant_sig.get('regime','?')}"))

    log.append(("ok",  "[06] Risk Manager…"))
    risk_sig = agent_risk(sym, market_sig, sentiment_sig, fund_sig, quant_sig, estimates, dcf)
    log.append(("ok",  f"[06] → risk: {risk_sig.get('risk_level','?')} | signal: {risk_sig.get('risk_signal','?')}"))

    log.append(("ok",  "[07] Portfolio Manager — final decision…"))
    portfolio_sig = agent_portfolio(sym, risk_sig, market_sig, sentiment_sig, fund_sig, quant_sig)
    log.append(("ok",  f"[07] → ACTION: {portfolio_sig.get('action','?')} | {portfolio_sig.get('confidence','?')}% confidence"))

    return {
        "sym":          sym,
        "quant":        quant,
        "market":       market_sig,
        "sentiment":    sentiment_sig,
        "fundamentals": fund_sig,
        "quant_agent":  quant_sig,
        "risk":         risk_sig,
        "portfolio":    portfolio_sig,
        "log":          log,
        "profile":      (profile[0] if isinstance(profile,list) and profile else {}),
        "timestamp":    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

# ─────────────────────────────────────────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────────────────────────────────────────

AGENTS = [
    ("📊", "Market Data"),
    ("📰", "Sentiment"),
    ("📋", "Fundamentals"),
    ("📐", "Quant"),
    ("🛡", "Risk Mgr"),
    ("💼", "Portfolio"),
]

def signal_color(s):
    return {"BUY":"#2ecc71","SELL":"#e74c3c","HOLD":"#f39c12"}.get(str(s).upper(),"#6a7a8a")

def conf_color(c):
    try:
        c = int(c)
        return "#2ecc71" if c>=70 else "#f39c12" if c>=45 else "#e74c3c"
    except: return "#6a7a8a"

def render_agent_card(icon, name, result, card_cls="done"):
    sig   = result.get("signal") or result.get("risk_signal") or result.get("action","?")
    conf  = result.get("confidence", 0)
    summary = result.get("summary") or result.get("rationale","")
    extras = ""
    if "tone" in result:
        extras += f' &nbsp;·&nbsp; <b>Tone:</b> {result["tone"]}'
    if "valuation" in result:
        extras += f' &nbsp;·&nbsp; <b>Val:</b> {result["valuation"]} &nbsp;·&nbsp; <b>Quality:</b> {result.get("quality","?")}'
    if "regime" in result:
        extras += f' &nbsp;·&nbsp; <b>Regime:</b> {result["regime"]}'
    if "risk_level" in result:
        extras += f' &nbsp;·&nbsp; <b>Risk:</b> {result["risk_level"]}'
    if "time_horizon" in result:
        extras += f' &nbsp;·&nbsp; <b>Horizon:</b> {result["time_horizon"]}'

    sc = signal_color(sig)
    cc = conf_color(conf)

    st.markdown(f"""
    <div class="hf-signal {card_cls}">
      <div class="hf-agent-name">
        {icon} {name}
        <span style="font-family:'IBM Plex Mono',monospace;font-size:.94rem;
                     color:{sc};font-weight:600">{sig}</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:.90rem;color:{cc}">{conf}%</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:.86rem;
                     color:#2a3540">{extras}</span>
      </div>
      <div class="hf-signal-body">{summary}</div>
      <div class="hf-conf-bar-bg">
        <div class="hf-conf-bar-fill" style="width:{min(conf,100)}%;background:{cc}"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def render_hedge_fund():
    st.markdown(HF_CSS, unsafe_allow_html=True)

    ts = datetime.utcnow().strftime("%d %b %Y · %H:%M UTC")
    st.markdown(f"""
    <div class="hf-topbar">
      <span class="hf-wordmark">Blackwater One</span>
      <div class="hf-sep"></div>
      <span class="hf-subtitle">AI Hedge Fund</span>
      <div class="hf-sep"></div>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:.66rem;color:#3a2a10;
                   border:1px solid #2a1800;padding:2px 8px">6-AGENT PIPELINE</span>
      <span class="hf-ts">{ts}</span>
    </div>
    <div style="height:12px"></div>""", unsafe_allow_html=True)

    # ── Nav ───────────────────────────────────────────────────────────────────
    if st.button("← Back", key="hf_back"):
        st.session_state.page = "eagle"
        st.rerun()

    # ── Ticker input ──────────────────────────────────────────────────────────
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:.88rem;'
                'color:#c9a84c;text-transform:uppercase;letter-spacing:.18em;'
                'padding:10px 0 6px;border-bottom:1px solid #1a1f28;margin-bottom:8px">'
                '▸ Target Security</div>', unsafe_allow_html=True)

    c1, c2, c3, _ = st.columns([1.4, 0.5, 0.6, 2.5])
    with c1:
        sym_input = st.text_input("", placeholder="Ticker (e.g. AAPL, NVDA, TSLA)…",
                                  key="hf_sym", label_visibility="collapsed")
    with c2:
        run_btn = st.button("▶ Run", use_container_width=True, key="hf_run",
                            type="primary")
    with c3:
        clear_btn = st.button("✕ Clear", use_container_width=True, key="hf_clear")

    if clear_btn:
        for k in ["hf_result","hf_running"]:
            if k in st.session_state: del st.session_state[k]
        st.rerun()

    # ── Pipeline diagram ──────────────────────────────────────────────────────
    result    = st.session_state.get("hf_result")
    is_running= st.session_state.get("hf_running", False)

    # Determine which stage is done
    done_stages = 0
    if result:
        done_stages = 6

    nodes_html = ""
    for i, (icon, label) in enumerate(AGENTS):
        if done_stages > i:
            cls = "done"
        elif is_running and done_stages == i:
            cls = "running"
        else:
            cls = ""
        nodes_html += f'<div class="hf-node"><div class="hf-node-icon {cls}">{icon}</div><div class="hf-node-lbl">{label}</div></div>'
        if i < len(AGENTS)-1:
            arrow_cls = "lit" if done_stages > i else ""
            nodes_html += f'<div class="hf-arrow {arrow_cls}">→</div>'

    st.markdown(f'<div class="hf-pipeline">{nodes_html}</div>', unsafe_allow_html=True)

    # ── Run pipeline ──────────────────────────────────────────────────────────
    if run_btn and sym_input:
        sym = sym_input.upper().strip()
        st.session_state.hf_running = True
        with st.spinner(f"Running 6-agent pipeline for {sym}…"):
            result = run_pipeline(sym)
        st.session_state.hf_result  = result
        st.session_state.hf_running = False
        st.rerun()

    if not result:
        st.markdown("""
        <div style="text-align:center;padding:50px 0;font-family:'IBM Plex Mono',monospace;
                    font-size:.98rem;color:#1a2530;letter-spacing:.12em">
          ENTER A TICKER AND PRESS ▶ RUN TO INITIATE THE PIPELINE
        </div>""", unsafe_allow_html=True)
        return

    sym    = result["sym"]
    port   = result["portfolio"]
    risk   = result["risk"]
    action = port.get("action","HOLD").upper()
    conf   = port.get("confidence", 0)
    quant  = result["quant"]
    profile= result["profile"]

    # ── KPI strip ─────────────────────────────────────────────────────────────
    price   = profile.get("price", quant.get("price","—"))
    mktcap  = profile.get("marketCap",0) or 0
    mktcap_s= f"${mktcap/1e12:.2f}T" if mktcap>1e12 else f"${mktcap/1e9:.1f}B" if mktcap else "—"

    price_str = f"${price:,.2f}" if isinstance(price,(int,float)) else str(price)
    ac = "green" if action=="BUY" else "red" if action=="SELL" else "gold"
    st.markdown(f"""
    <div class="hf-kpi-row">
      <div class="hf-kpi {ac}"><div class="lbl">Decision</div><div class="val">{action}</div></div>
      <div class="hf-kpi"><div class="lbl">Confidence</div><div class="val">{conf}%</div></div>
      <div class="hf-kpi"><div class="lbl">Risk Level</div><div class="val">{risk.get("risk_level","—")}</div></div>
      <div class="hf-kpi"><div class="lbl">Position Size</div><div class="val">{port.get("position_size_pct","—")}%</div></div>
      <div class="hf-kpi"><div class="lbl">Price</div><div class="val">{price_str}</div></div>
      <div class="hf-kpi gold"><div class="lbl">Mkt Cap</div><div class="val">{mktcap_s}</div></div>
      <div class="hf-kpi"><div class="lbl">RSI</div><div class="val">{quant.get("rsi","—")}</div></div>
      <div class="hf-kpi"><div class="lbl">MA Cross</div><div class="val">{quant.get("ma_cross","—")}</div></div>
    </div>""", unsafe_allow_html=True)

    # ── Main: Verdict | Agent signals ─────────────────────────────────────────
    left_col, right_col = st.columns([1.1, 2.0], gap="medium")

    with left_col:
        # Verdict card
        st.markdown(f"""
        <div class="hf-verdict">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:.84rem;
                      color:#5a4a2a;letter-spacing:.18em;text-transform:uppercase;
                      margin-bottom:10px">Portfolio Manager · Final Decision</div>
          <div class="hf-verdict-action {action}">{action}</div>
          <div class="hf-verdict-sub">{sym} &nbsp;·&nbsp; {conf}% confidence</div>
          <div class="hf-conf-bar-bg" style="margin:10px auto;max-width:160px">
            <div class="hf-conf-bar-fill"
                 style="width:{min(conf,100)}%;background:{signal_color(action)}"></div>
          </div>
          <div class="hf-verdict-reason">{port.get("rationale","")}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        # Stop loss + price target
        stop  = port.get("stop_loss_note","")
        tgt   = port.get("price_target_note","")
        if stop or tgt:
            st.markdown(f"""
            <div style="background:#0a0c0f;border:1px solid #1a1f28;padding:12px 14px;
                        font-family:'IBM Plex Sans',sans-serif;font-size:.92rem;color:#6a7a8a">
              {"<div style='margin-bottom:6px'><b style='color:#e74c3c'>⚠ Stop Loss:</b> "+stop+"</div>" if stop else ""}
              {"<div><b style='color:#2ecc71'>🎯 Target:</b> "+tgt+"</div>" if tgt else ""}
            </div>""", unsafe_allow_html=True)

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        # Vote tally
        votes = {"BUY":0,"HOLD":0,"SELL":0}
        for ag in ["market","sentiment","fundamentals","quant_agent","risk"]:
            s = result.get(ag,{}).get("signal") or result.get(ag,{}).get("risk_signal","HOLD")
            votes[s.upper()] = votes.get(s.upper(),0) + 1
        total = sum(votes.values()) or 1
        st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:.84rem;'
                    'color:#5a4a2a;letter-spacing:.16em;text-transform:uppercase;'
                    'margin-bottom:6px">Agent Vote Tally</div>', unsafe_allow_html=True)
        for v, n in votes.items():
            vc = signal_color(v)
            pct= int(n/total*100)
            st.markdown(f"""
            <div style="margin-bottom:4px">
              <span style="font-family:'IBM Plex Mono',monospace;font-size:.94rem;
                           color:{vc};min-width:40px;display:inline-block">{v}</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:.90rem;
                           color:#2a3540">{n} agent{'s' if n!=1 else ''}</span>
              <div style="background:#0a0c0f;height:4px;border-radius:1px;margin-top:2px">
                <div style="width:{pct}%;height:4px;background:{vc};border-radius:1px"></div>
              </div>
            </div>""", unsafe_allow_html=True)

    with right_col:
        st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:.84rem;'
                    'color:#5a4a2a;letter-spacing:.16em;text-transform:uppercase;'
                    'padding-bottom:6px;border-bottom:1px solid #1a1f28;margin-bottom:8px">'
                    'Agent Signal Chain</div>', unsafe_allow_html=True)

        render_agent_card("📊", "Market Data Analyst",  result["market"],       "info")
        render_agent_card("📰", "Sentiment Analyst",    result["sentiment"],    "warn")
        render_agent_card("📋", "Fundamentals Analyst", result["fundamentals"], "done")
        render_agent_card("📐", "Quant Analyst",        result["quant_agent"],  "quant")
        render_agent_card("🛡", "Risk Manager",         result["risk"],         "risk")

    # ── Pipeline log ──────────────────────────────────────────────────────────
    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
    with st.expander("📋 Pipeline Log", expanded=False):
        log_lines = "".join(
            f'<div class="{cls}">{msg}</div>'
            for cls, msg in result.get("log",[])
        )
        st.markdown(f'<div class="hf-log">{log_lines}</div>', unsafe_allow_html=True)
        st.caption(f"Completed: {result.get('timestamp','')}")
