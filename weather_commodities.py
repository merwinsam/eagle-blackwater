"""
Blackwater Weather Intelligence — Commodity Futures Map
Live prices via FMP stable endpoints + OpenWeather conditions
"""
import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime
from openai import OpenAI
import config

# ── Commodity-producing regions ────────────────────────────────────────────────
COMMODITY_REGIONS = [
    # Energy
    {"name": "Brent Crude",     "region": "North Sea",           "lat": 61.0,  "lon":   2.0,  "commodity": "BZUSD",  "type": "energy", "emoji": "🛢️"},
    {"name": "WTI Crude",       "region": "Texas, US",           "lat": 31.5,  "lon": -99.0,  "commodity": "CLUSD",  "type": "energy", "emoji": "🛢️"},
    {"name": "Natural Gas",     "region": "Gulf Coast, US",      "lat": 29.5,  "lon": -91.0,  "commodity": "NGUSD",  "type": "energy", "emoji": "🔥"},
    {"name": "LNG Hub",         "region": "Qatar",               "lat": 25.3,  "lon":  51.2,  "commodity": "NGUSD",  "type": "energy", "emoji": "🔥"},
    # Grains
    {"name": "Wheat",           "region": "Kansas, US",          "lat": 38.5,  "lon": -98.5,  "commodity": "KEUSX",  "type": "grain",  "emoji": "🌾"},
    {"name": "Corn",            "region": "Iowa, US",            "lat": 42.0,  "lon": -93.5,  "commodity": "ZCUSX",  "type": "grain",  "emoji": "🌽"},
    {"name": "Soybeans",        "region": "Mato Grosso, Brazil", "lat": -13.0, "lon": -55.0,  "commodity": "ZSUSX",  "type": "grain",  "emoji": "🫘"},
    {"name": "Black Sea Wheat", "region": "Ukraine",             "lat": 49.0,  "lon":  32.0,  "commodity": "KEUSX",  "type": "grain",  "emoji": "🌾"},
    {"name": "Wheat",           "region": "Western Australia",   "lat": -32.0, "lon": 117.0,  "commodity": "KEUSX",  "type": "grain",  "emoji": "🌾"},
    # Softs
    {"name": "Coffee",          "region": "Colombia",            "lat":   4.5, "lon": -74.0,  "commodity": "KCUSX",  "type": "soft",   "emoji": "☕"},
    {"name": "Cocoa",           "region": "Ivory Coast",         "lat":   6.8, "lon":  -5.3,  "commodity": "CCUSD",  "type": "soft",   "emoji": "🍫"},
    {"name": "Sugar",           "region": "Cerrado, Brazil",     "lat": -18.0, "lon": -47.0,  "commodity": "SBUSX",  "type": "soft",   "emoji": "🍬"},
    {"name": "Cotton",          "region": "Texas, US",           "lat": 33.5,  "lon":-101.0,  "commodity": "CTUSX",  "type": "soft",   "emoji": "🌿"},
    {"name": "Palm Oil",        "region": "Malaysia",            "lat":   3.1, "lon": 101.7,  "commodity": "SBUSX",  "type": "soft",   "emoji": "🌴"},
    # Metals
    {"name": "Gold",            "region": "Witwatersrand, SA",   "lat": -26.0, "lon":  27.0,  "commodity": "GCUSD",  "type": "metal",  "emoji": "🥇"},
    {"name": "Copper",          "region": "Atacama, Chile",      "lat": -23.0, "lon": -68.0,  "commodity": "HGUSD",  "type": "metal",  "emoji": "🔶"},
    {"name": "Iron Ore",        "region": "Pilbara, Australia",  "lat": -22.5, "lon": 118.5,  "commodity": "HGUSD",  "type": "metal",  "emoji": "⛏️"},
    {"name": "Silver",          "region": "Nevada, US",          "lat": 39.5,  "lon":-116.0,  "commodity": "SIUSD",  "type": "metal",  "emoji": "🥈"},
]

# Exact symbols confirmed from FMP /stable/batch-commodity-quotes response
# (canonical_key, display_name, type, fmp_symbol)
# USX-denominated symbols return prices in cents — we divide by 100
FMP_COMMODITIES = [
    # Metals
    ("GCUSD",  "Gold",        "metal",  "GCUSD",  1),
    ("SIUSD",  "Silver",      "metal",  "SIUSD",  1),
    ("HGUSD",  "Copper",      "metal",  "HGUSD",  1),
    # Energy
    ("CLUSD",  "WTI Crude",   "energy", "CLUSD",  1),
    ("BZUSD",  "Brent Crude", "energy", "BZUSD",  1),
    ("NGUSD",  "Nat Gas",     "energy", "NGUSD",  1),
    # Grains  (USX = cents/bushel → divide by 100 to get dollars)
    ("KEUSX",  "Wheat",       "grain",  "KEUSX",  100),
    ("ZCUSX",  "Corn",        "grain",  "ZCUSX",  100),
    ("ZSUSX",  "Soybeans",    "grain",  "ZSUSX",  100),
    # Softs
    ("KCUSX",  "Coffee",      "soft",   "KCUSX",  100),
    ("CCUSD",  "Cocoa",       "soft",   "CCUSD",  1),
    ("SBUSX",  "Sugar",       "soft",   "SBUSX",  100),
    ("CTUSX",  "Cotton",      "soft",   "CTUSX",  100),
]

# Map every API symbol back to its canonical key
_SYM_TO_CANON = {}
for _c, _, _, _s, _ in FMP_COMMODITIES:
    _SYM_TO_CANON[_c] = _c
    _SYM_TO_CANON[_s] = _c

# Divisor for each canonical (1 for USD, 100 for USX cents)
_DIVISOR = {_c: _d for _c, _, _, _, _d in FMP_COMMODITIES}

TYPE_COLORS = {
    "energy": "#fb923c",
    "grain":  "#fbbf24",
    "soft":   "#4ade80",
    "metal":  "#60a5fa",
}

# ── CSS ────────────────────────────────────────────────────────────────────────
WC_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
@keyframes slidein { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

.wc-header {
  background: #0e1218; border-bottom: 1px solid #1e2a38;
  padding: 0 28px; height: 52px;
  display: flex; align-items: center; gap: 16px;
}
.wc-logo { font-family:'Syne',sans-serif; font-weight:800; font-size:1.1rem; color:#e8c97e; }
.wc-sep  { width:1px; height:22px; background:#2a3a4e; }
.wc-sub  { font-family:'Space Mono',monospace; font-size:.63rem; color:#4a6080; letter-spacing:.1em; text-transform:uppercase; }

.wc-kpi { background:#0e1218; border:1px solid #1e2a38; border-radius:10px; padding:14px 16px; text-align:center; animation:slidein .4s ease; }
.wc-kpi.bull    { border-top:2px solid #4ade80; }
.wc-kpi.bear    { border-top:2px solid #f87171; }
.wc-kpi.watch   { border-top:2px solid #fbbf24; }
.wc-kpi.neutral { border-top:2px solid #2a3a4e; }
.kpi-label { font-family:'Space Mono',monospace; font-size:.57rem; color:#4a6080; text-transform:uppercase; letter-spacing:.14em; margin-bottom:6px; }
.kpi-val   { font-family:'Space Mono',monospace; font-size:1.35rem; font-weight:700; color:#e8c97e; line-height:1; }
.kpi-sub   { font-size:.63rem; color:#8a9bb0; margin-top:5px; }

.sec-hdr { font-family:'Space Mono',monospace; font-size:.63rem; font-weight:700; color:#4a6080; text-transform:uppercase; letter-spacing:.18em; padding:10px 0 7px; border-bottom:1px solid #1e2a38; margin-bottom:12px; }

.ticker-wrap  { background:#0e1218; border:1px solid #1e2a38; border-radius:8px; padding:9px 16px; margin-bottom:14px; overflow-x:auto; }
.ticker-inner { display:flex; gap:0; align-items:center; min-width:max-content; }
.tick-item  { display:flex; align-items:center; gap:6px; padding:0 16px 0 0; flex-shrink:0; }
.tick-sep   { width:1px; height:20px; background:#1e2a38; margin-right:16px; flex-shrink:0; }
.tick-sym   { font-family:'Space Mono',monospace; font-size:.64rem; color:#4a6080; font-weight:700; }
.tick-name  { font-size:.64rem; color:#8a9bb0; }
.tick-price { font-family:'Space Mono',monospace; font-size:.8rem; color:#eef2f7; font-weight:700; }
.tick-pos   { font-family:'Space Mono',monospace; font-size:.68rem; color:#4ade80; }
.tick-neg   { font-family:'Space Mono',monospace; font-size:.68rem; color:#f87171; }

.map-legend { background:rgba(9,11,14,.92); border:1px solid #1e2a38; border-radius:8px; padding:8px 16px; display:flex; gap:20px; align-items:center; flex-wrap:wrap; font-family:'Space Mono',monospace; font-size:.62rem; margin-bottom:10px; }
.leg-item { display:flex; align-items:center; gap:6px; }
.leg-dot  { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
.leg-ring { width:12px; height:12px; border-radius:50%; border:2px solid; flex-shrink:0; }

.com-group-hdr { font-size:.62rem; font-weight:700; color:#4a6080; text-transform:uppercase; letter-spacing:.12em; padding:8px 0 4px; font-family:'Space Mono',monospace; }
.com-row { background:#0e1218; border:1px solid #1e2a38; border-radius:8px; padding:9px 13px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center; animation:slidein .3s ease; transition:border-color .15s; }
.com-row:hover   { border-color:#2a3a4e; }
.com-row.bull-row { border-left:2px solid #4ade80; }
.com-row.bear-row { border-left:2px solid #f87171; }
.com-row.flat-row { border-left:2px solid #2a3a4e; }
.com-name  { font-size:.8rem; font-weight:600; color:#eef2f7; }
.com-sym   { font-family:'Space Mono',monospace; font-size:.58rem; color:#4a6080; margin-top:2px; }
.com-price { font-family:'Space Mono',monospace; font-size:.86rem; color:#eef2f7; font-weight:700; }
.com-na    { font-family:'Space Mono',monospace; font-size:.72rem; color:#4a6080; }

.wcard       { background:#0e1218; border:1px solid #1e2a38; border-radius:8px; padding:13px 15px; margin-bottom:7px; animation:slidein .3s ease; }
.wcard.bull  { border-left:3px solid #4ade80; }
.wcard.bear  { border-left:3px solid #f87171; }
.wcard.watch { border-left:3px solid #fbbf24; }
.wcard-top    { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:9px; }
.wcard-name   { font-size:.83rem; font-weight:600; color:#eef2f7; }
.wcard-region { font-family:'Space Mono',monospace; font-size:.59rem; color:#4a6080; margin-top:2px; }
.wcard-stats  { display:flex; gap:14px; flex-wrap:wrap; }
.ws-label { font-family:'Space Mono',monospace; font-size:.56rem; color:#4a6080; text-transform:uppercase; }
.ws-val   { font-size:.78rem; color:#eef2f7; font-weight:600; margin-top:2px; }
.ws-gold  { color:#e8c97e !important; }

.sig-pill      { display:inline-block; padding:2px 9px; border-radius:12px; font-size:.59rem; font-family:'Space Mono',monospace; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.sig-bull      { background:rgba(74,222,128,.12);  color:#4ade80; border:1px solid rgba(74,222,128,.3); }
.sig-bear      { background:rgba(248,113,113,.12); color:#f87171; border:1px solid rgba(248,113,113,.3); }
.sig-watch     { background:rgba(251,191,36,.12);  color:#fbbf24; border:1px solid rgba(251,191,36,.3); }

.insight-box { background:#0e1218; border:1px solid #1e2a38; border-left:3px solid #e8c97e; border-radius:0 10px 10px 0; padding:14px 18px; font-size:.8rem; line-height:1.8; color:#8a9bb0; white-space:pre-wrap; animation:slidein .4s ease; }
.alert-box   { background:rgba(248,113,113,.07); border:1px solid rgba(248,113,113,.2); border-left:3px solid #f87171; border-radius:0 8px 8px 0; padding:10px 14px; margin-bottom:6px; font-size:.74rem; color:#f87171; line-height:1.5; }
.debug-warn  { background:rgba(251,191,36,.07); border:1px solid rgba(251,191,36,.2); border-radius:8px; padding:10px 14px; font-size:.72rem; font-family:'Space Mono',monospace; color:#fbbf24; margin-bottom:10px; }
</style>
"""

# ── DATA FETCHERS ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=180)
def fetch_all_commodities():
    """
    FMP stable endpoints:
      Primary:  /stable/batch-commodity-quotes?short=true  → {symbol, price, change($), volume}
      Fallback: /stable/quote?symbol=ZW                    → [{price, changePercentage, dayHigh, dayLow, …}]

    Key insight: FMP uses short CBOT symbols for grains/softs (ZW, ZC, ZS, KC, CC, SB, CT)
    but XUSD format for metals/energy (GCUSD, CLUSD, etc.)
    _SYM_TO_CANON maps both forms back to our canonical keys.
    """
    api_key = config.FMP_API_KEY
    results = {}

    # ── 1. Batch ──────────────────────────────────────────────────────────────
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/stable/batch-commodity-quotes"
            f"?short=true&apikey={api_key}",
            timeout=12,
        )
        if r.status_code == 200:
            for item in r.json():
                sym   = item.get("symbol", "")
                canon = _SYM_TO_CANON.get(sym)
                price = float(item.get("price") or 0)
                if canon and price:
                    div  = _DIVISOR.get(canon, 1)
                    chg  = float(item.get("change") or 0)
                    price_adj = price / div
                    chg_adj   = chg / div
                    prev = price_adj - chg_adj
                    pct  = round((chg_adj / prev * 100), 4) if prev else 0.0
                    results[canon] = {
                        "price":             price_adj,
                        "changesPercentage": pct,
                        "change":            chg_adj,
                        "volume":            item.get("volume", 0),
                        "dayHigh":           0.0,
                        "dayLow":            0.0,
                        "_source":           f"batch/{sym}",
                    }
    except Exception:
        pass

    # ── 2. Individual fallback for anything still missing ─────────────────────
    missing = [
        (canon, fmp_sym)
        for canon, _, _, fmp_sym, _ in FMP_COMMODITIES
        if canon not in results or not results[canon].get("price")
    ]
    for canon, fmp_sym in missing:
        try:
            r = requests.get(
                f"https://financialmodelingprep.com/stable/quote"
                f"?symbol={fmp_sym}&apikey={api_key}",
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                item = (data[0] if isinstance(data, list) and data
                        else data if isinstance(data, dict) else {})
                price = float(item.get("price") or 0)
                if price:
                    div = _DIVISOR.get(canon, 1)
                    results[canon] = {
                        "price":             price / div,
                        "changesPercentage": float(item.get("changePercentage") or 0),
                        "change":            float(item.get("change") or 0) / div,
                        "volume":            item.get("volume", 0),
                        "dayHigh":           float(item.get("dayHigh") or 0) / div,
                        "dayLow":            float(item.get("dayLow") or 0) / div,
                        "yearHigh":          float(item.get("yearHigh") or 0) / div,
                        "yearLow":           float(item.get("yearLow") or 0) / div,
                        "previousClose":     float(item.get("previousClose") or 0) / div,
                        "name":              item.get("name", ""),
                        "_source":           f"individual/{fmp_sym}",
                    }
        except Exception:
            pass

    return results


@st.cache_data(ttl=600)
def fetch_weather(lat, lon):
    api_key = st.secrets.get("OPENWEATHER_API_KEY", "")
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&exclude=minutely,alerts",
            timeout=8,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={api_key}&units=metric",
            timeout=8,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def parse_weather(data):
    if not data:
        return {}
    if "current" in data:
        cur = data["current"]
        return {
            "temp":        round(cur.get("temp", 0), 1),
            "feels_like":  round(cur.get("feels_like", 0), 1),
            "humidity":    cur.get("humidity", 0),
            "wind_speed":  round(cur.get("wind_speed", 0), 1),
            "description": cur.get("weather", [{}])[0].get("description", "").title(),
            "icon":        cur.get("weather", [{}])[0].get("main", ""),
            "rain_1h":     cur.get("rain", {}).get("1h", 0),
            "alerts":      data.get("alerts", []),
        }
    return {
        "temp":        round(data.get("main", {}).get("temp", 0), 1),
        "feels_like":  round(data.get("main", {}).get("feels_like", 0), 1),
        "humidity":    data.get("main", {}).get("humidity", 0),
        "wind_speed":  round(data.get("wind", {}).get("speed", 0), 1),
        "description": data.get("weather", [{}])[0].get("description", "").title(),
        "icon":        data.get("weather", [{}])[0].get("main", ""),
        "rain_1h":     data.get("rain", {}).get("1h", 0),
        "alerts":      [],
    }


def fmt_price(p):
    if not p:
        return "—"
    if p >= 1000:  return f"${p:,.2f}"
    if p >= 1:     return f"${p:.3f}"
    return f"${p:.4f}"


def weather_signal(w, ctype):
    if not w:
        return "watch", "No data"
    temp = w.get("temp", 20)
    wind = w.get("wind_speed", 0)
    rain = w.get("rain_1h", 0)
    desc = w.get("description", "").lower()

    if ctype == "energy":
        if temp < -5 or wind > 15:               return "bull", "Cold snap / storm → demand surge"
        if temp > 38:                            return "bull", "Heat wave → cooling demand spike"
        if "storm" in desc or "thunder" in desc: return "bull", "Storm → supply disruption risk"
        if "clear" in desc and 10 < temp < 25:   return "bear", "Mild clear weather → low demand"
        return "watch", "Normal energy conditions"

    if ctype == "grain":
        if rain > 10:                            return "bear", "Heavy rain → flood risk"
        if rain == 0 and temp > 35:              return "bull", "Drought stress → supply risk"
        if "frost" in desc or temp < 0:          return "bull", "Frost risk → crop damage"
        if wind > 20 or "storm" in desc:         return "bull", "Storm → harvest disruption"
        if 15 < temp < 28 and rain < 5:          return "watch", "Favorable growing conditions"
        return "watch", "Monitor crop conditions"

    if ctype == "soft":
        if rain > 15:                            return "bear", "Excess rain → disease / mold risk"
        if rain == 0 and temp > 38:              return "bull", "Drought stress → yield reduction"
        if "storm" in desc:                      return "bull", "Storm → crop / harvest damage"
        if wind > 18:                            return "watch", "High winds → monitor closely"
        return "watch", "Normal conditions"

    if ctype == "metal":
        if "storm" in desc or wind > 20:         return "bull", "Storm → mining ops disruption"
        if temp < -10:                           return "bull", "Extreme cold → equipment shutdown"
        return "watch", "Normal mining conditions"

    return "watch", "Monitor"


def weather_emoji(desc):
    d = desc.lower()
    if "thunder" in d or "storm" in d: return "⛈️"
    if "snow" in d or "blizzard" in d: return "❄️"
    if "rain" in d or "drizzle" in d:  return "🌧️"
    if "fog" in d or "mist" in d:      return "🌫️"
    if "cloud" in d:                   return "☁️"
    if "clear" in d:                   return "☀️"
    return "🌤️"


# ── MAP ────────────────────────────────────────────────────────────────────────
def build_map(regions, weather_cache, commodities):
    groups = {"bull": [], "bear": [], "watch": []}

    for r in regions:
        key   = f"{r['lat']}_{r['lon']}"
        w     = parse_weather(weather_cache.get(key, {}))
        sig, reason = weather_signal(w, r["type"])
        com   = commodities.get(r["commodity"], {})
        price = com.get("price") or 0
        chg   = com.get("changesPercentage") or 0
        wdesc = w.get("description", "—") if w else "—"
        wemo  = weather_emoji(wdesc)
        chg_col = "#4ade80" if chg >= 0 else "#f87171"
        chg_arrow = "▲" if chg >= 0 else "▼"

        hover = (
            f"<b style='font-size:13px'>{r['emoji']} {r['name']}</b>"
            f"<br><span style='color:#6a8aaa'>{r['region']}</span><br><br>"
            f"<span style='color:#b89a52'>── Futures ──────────</span><br>"
            f"Price  <b style='color:#eef2f7'>{fmt_price(price) if price else '—'}</b>"
            + (f"  <span style='color:{chg_col}'>{chg_arrow}{abs(chg):.2f}%</span>" if chg else "")
            + f"<br>Symbol <span style='color:#4a6080'>{r['commodity']}</span><br><br>"
            f"<span style='color:#b89a52'>── Weather ──────────</span><br>"
            f"{wemo} {wdesc} · {w.get('temp','—')}°C<br>"
            f"💨 {w.get('wind_speed','—')} m/s  · 💧 {w.get('humidity','—')}%<br><br>"
            f"<b>Signal</b> "
            f"<span style='color:{'#4ade80' if sig=='bull' else '#f87171' if sig=='bear' else '#fbbf24'}'>"
            f"{sig.upper()} — {reason}</span>"
        )

        if price and price > 0:
            label = f"  {r['emoji']} {fmt_price(price)} {chg_arrow}{abs(chg):.1f}%"
        else:
            label = f"  {r['emoji']} {r['name']}"

        groups[sig].append({
            "lat": r["lat"], "lon": r["lon"],
            "hover": hover, "label": label,
            "type": r["type"], "price": price, "chg": chg, "sig": sig,
        })

    fig = go.Figure()

    # Outer glow halos for active signals
    for sig, halo_color in [("bull", "#4ade80"), ("bear", "#f87171")]:
        pts = groups[sig]
        if not pts:
            continue
        for sz, op in [(30, 0.08), (20, 0.16)]:
            fig.add_trace(go.Scattergeo(
                lat=[p["lat"] for p in pts], lon=[p["lon"] for p in pts],
                mode="markers",
                marker=dict(size=sz, color=halo_color, opacity=op, line=dict(width=0)),
                hoverinfo="skip", showlegend=False,
            ))

    # Main pins
    sig_ring  = {"bull": "#4ade80", "bear": "#f87171", "watch": "#fbbf24"}
    sig_size  = {"bull": 14,        "bear": 14,         "watch": 10}
    sig_name  = {"bull": "🟢 Bullish — supply risk", "bear": "🔴 Bearish — surplus", "watch": "🟡 Watch"}

    for sig, pts in groups.items():
        if not pts:
            continue
        fig.add_trace(go.Scattergeo(
            lat=[p["lat"] for p in pts],
            lon=[p["lon"] for p in pts],
            mode="markers+text",
            marker=dict(
                size=sig_size[sig],
                color=[TYPE_COLORS.get(p["type"], "#94a3b8") for p in pts],
                opacity=0.93,
                line=dict(width=2, color=sig_ring[sig]),
                symbol="circle",
            ),
            text=[p["label"] for p in pts],
            textfont=dict(
                size=9,
                color=[("#4ade80" if p["chg"] >= 0 else "#f87171") for p in pts],
                family="Space Mono, monospace",
            ),
            textposition="middle right",
            hovertext=[p["hover"] for p in pts],
            hoverinfo="text",
            hoverlabel=dict(
                bgcolor="#0b0f16", bordercolor="#2a3a4e",
                font=dict(color="#eef2f7", size=12, family="Inter, sans-serif"),
                align="left",
            ),
            name=sig_name[sig],
            showlegend=True,
        ))

    # Beautiful geo styling — continents pop with bright coastlines
    fig.update_geos(
        projection_type="natural earth",
        showland=True,        landcolor="#141e2b",        # lifted dark blue-grey
        showocean=True,       oceancolor="#07090f",        # near-black ocean
        showcoastlines=True,  coastlinecolor="#4a7090",   # bright teal-blue coastlines
        coastlinewidth=1.4,
        showcountries=True,   countrycolor="#1e2e42",     countrywidth=0.5,
        showlakes=True,       lakecolor="#07090f",
        showrivers=False,
        showframe=False,
        bgcolor="#090b0e",
        lataxis=dict(showgrid=True, gridcolor="rgba(42,58,78,0.25)", gridwidth=0.4),
        lonaxis=dict(showgrid=True, gridcolor="rgba(42,58,78,0.25)", gridwidth=0.4),
    )

    fig.update_layout(
        paper_bgcolor="#090b0e",
        plot_bgcolor="#090b0e",
        margin=dict(l=0, r=0, t=0, b=0),
        height=490,
        legend=dict(
            orientation="h", x=0.01, y=0.02,
            bgcolor="rgba(7,9,15,0.90)", bordercolor="#1e2a38", borderwidth=1,
            font=dict(size=11, color="#8a9bb0", family="Space Mono, monospace"),
        ),
        font=dict(family="Inter, sans-serif", color="#4a6080"),
    )
    return fig


# ── Eagle Insight ──────────────────────────────────────────────────────────────
def gen_insight(regions, weather_cache, commodities):
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    sigs   = []
    for r in regions:
        key  = f"{r['lat']}_{r['lon']}"
        w    = parse_weather(weather_cache.get(key, {}))
        sig, reason = weather_signal(w, r["type"])
        com  = commodities.get(r["commodity"], {})
        price = com.get("price") or 0
        chg   = com.get("changesPercentage") or 0
        sigs.append({
            "name": r["name"], "region": r["region"],
            "commodity": r["commodity"], "type": r["type"],
            "signal": sig, "reason": reason,
            "weather": f"{w.get('temp','—')}°C, {w.get('description','—')}, wind {w.get('wind_speed','—')} m/s",
            "price": price, "chg_pct": chg,
        })
    bull = [s for s in sigs if s["signal"] == "bull" and s["price"]]
    bear = [s for s in sigs if s["signal"] == "bear" and s["price"]]

    def lines(lst):
        return "\n".join(
            f"- {s['name']} ({s['region']}): {s['reason']} | "
            f"{s['weather']} | {fmt_price(s['price'])} ({s['chg_pct']:+.2f}%)"
            for s in lst
        ) or "None identified"

    try:
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": (
                "You are Eagle, commodity futures analyst at Blackwater Trading.\n"
                "Based on current weather across key commodity-producing regions and live futures prices, "
                "identify the top 3 developing opportunities in futures markets.\n\n"
                "For each: name the commodity + region, explain the weather→supply chain link in one sentence, "
                "state bull/bear signal, and reference current price + % move.\n"
                "Be crisp and specific. Signals only, no trade recommendations.\n\n"
                f"BULLISH ({len(bull)}):\n{lines(bull)}\n\nBEARISH ({len(bear)}):\n{lines(bear)}"
            )}],
            temperature=0.3, max_tokens=520,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate insight: {e}"


# ── MAIN ───────────────────────────────────────────────────────────────────────
def render_weather_commodities():
    st.markdown(WC_CSS, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="wc-header">
      <span style="font-size:1.1rem">🌍</span>
      <span class="wc-logo">Blackwater One · Weather Intelligence</span>
      <div class="wc-sep"></div>
      <span class="wc-sub">Commodity Futures · Weather Map</span>
      <div style="flex:1"></div>
      <span style="font-family:'Space Mono',monospace;font-size:.65rem;color:#4a6080">
        {datetime.now().strftime("%b %d %Y · %H:%M")}
      </span>
    </div>
    <div style="height:14px"></div>
    """, unsafe_allow_html=True)

    # Refresh + Back nav at top
    rc1, rc2, _ = st.columns([1, 1, 5])
    with rc1:
        if st.button("← Back to Blackwater One", key="wc_back_top", use_container_width=True):
            st.session_state.page = "eagle"
            st.rerun()
    with rc2:
        if st.button("⟳ Refresh", use_container_width=True, key="wc_refresh"):
            fetch_weather.clear()
            fetch_all_commodities.clear()
            st.session_state.wc_loaded      = False
            st.session_state.wc_weather     = {}
            st.session_state.wc_commodities = {}
            st.session_state.wc_insight     = ""
            st.rerun()

    # Load data
    if not st.session_state.get("wc_loaded"):
        prog = st.progress(0, text="Fetching live commodity prices…")
        commodities = fetch_all_commodities()
        st.session_state.wc_commodities = commodities
        prog.progress(20, text="Loading global weather data…")
        weather_cache = {}
        seen = set()
        for i, r in enumerate(COMMODITY_REGIONS):
            key = f"{r['lat']}_{r['lon']}"
            if key not in seen:
                seen.add(key)
                weather_cache[key] = fetch_weather(r["lat"], r["lon"])
            prog.progress(20 + int(78 * (i + 1) / len(COMMODITY_REGIONS)),
                          text=f"Weather: {r['name']} ({r['region']})…")
        st.session_state.wc_weather = weather_cache
        st.session_state.wc_loaded  = True
        prog.progress(100, text="Done.")
        prog.empty()
        st.rerun()

    commodities   = st.session_state.wc_commodities
    weather_cache = st.session_state.wc_weather

    # Feed health
    loaded = sum(1 for c, _, _, _, _ in FMP_COMMODITIES if commodities.get(c, {}).get("price"))
    if loaded == 0:
        st.markdown(
            '<div class="debug-warn">⚠ No commodity prices loaded. '
            'Verify FMP API key supports /stable/batch-commodity-quotes. Click Refresh.</div>',
            unsafe_allow_html=True,
        )
    with st.expander(f"🔍 Price feed status  ({loaded}/{len(FMP_COMMODITIES)} loaded)", expanded=False):
        for canon, name, _, _, _ in FMP_COMMODITIES:
            d = commodities.get(canon, {})
            p = d.get("price") or 0
            chgp = d.get("changesPercentage") or 0
            src  = d.get("_source", "—")
            if p:
                st.caption(f"✅  {canon}  {name}  →  {fmt_price(p)}  ({chgp:+.2f}%)  via {src}")
            else:
                st.caption(f"❌  {canon}  {name}  →  not loaded")

    # KPIs
    bull_n  = sum(1 for r in COMMODITY_REGIONS
                  if weather_signal(parse_weather(weather_cache.get(f"{r['lat']}_{r['lon']}", {})), r["type"])[0] == "bull")
    bear_n  = sum(1 for r in COMMODITY_REGIONS
                  if weather_signal(parse_weather(weather_cache.get(f"{r['lat']}_{r['lon']}", {})), r["type"])[0] == "bear")
    watch_n = len(COMMODITY_REGIONS) - bull_n - bear_n
    live    = [(s, d) for s, d in commodities.items() if d.get("price")]
    gainers = sorted(live, key=lambda x: x[1].get("changesPercentage", 0), reverse=True)
    losers  = sorted(live, key=lambda x: x[1].get("changesPercentage", 0))
    top_g   = f"{gainers[0][0].replace('USD','')}  +{gainers[0][1]['changesPercentage']:.2f}%" if gainers else "—"
    top_l   = f"{losers[0][0].replace('USD','')}  {losers[0][1]['changesPercentage']:.2f}%"    if losers  else "—"

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, cls, label, val, sub in [
        (k1, "bull",    "Bullish Signals", str(bull_n),  "Weather → supply risk"),
        (k2, "bear",    "Bearish Signals", str(bear_n),  "Favorable supply conditions"),
        (k3, "watch",   "Watch Zones",     str(watch_n), "Monitor developing"),
        (k4, "neutral", "Top Gainer",      top_g,        "Futures today"),
        (k5, "neutral", "Top Loser",       top_l,        "Futures today"),
    ]:
        with col:
            st.markdown(
                f'<div class="wc-kpi {cls}"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-val">{val}</div><div class="kpi-sub">{sub}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # Ticker
    ticker_items = ""
    for canon, name, _, _, _ in FMP_COMMODITIES:
        d     = commodities.get(canon, {})
        price = d.get("price") or 0
        chg   = d.get("changesPercentage") or 0
        if not price:
            continue
        arrow = "▲" if chg >= 0 else "▼"
        cls   = "tick-pos" if chg >= 0 else "tick-neg"
        sym_s = canon.replace("USD", "")
        ticker_items += (
            f'<div class="tick-item">'
            f'<span class="tick-sym">{sym_s}</span>'
            f'<span class="tick-name">{name}</span>'
            f'<span class="tick-price">{fmt_price(price)}</span>'
            f'<span class="{cls}">{arrow}{abs(chg):.2f}%</span>'
            f'</div><div class="tick-sep"></div>'
        )
    fallback = (
        '<span style="font-family:\'Space Mono\',monospace;font-size:.7rem;color:#4a6080">'
        'Prices loading… click Refresh if this persists.</span>'
    )
    st.markdown(
        f'<div class="ticker-wrap"><div class="ticker-inner">'
        f'{ticker_items or fallback}</div></div>',
        unsafe_allow_html=True,
    )

    # Main layout
    map_col, right_col = st.columns([2.2, 1.0], gap="medium")

    with map_col:
        st.markdown('<div class="sec-hdr">Global Commodity Weather Map · Live Prices</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        <div class="map-legend">
          <div class="leg-item">
            <div class="leg-ring" style="border-color:#4ade80;box-shadow:0 0 5px #4ade80"></div>
            <span style="color:#4ade80">Bullish — supply risk</span>
          </div>
          <div class="leg-item">
            <div class="leg-ring" style="border-color:#f87171;box-shadow:0 0 5px #f87171"></div>
            <span style="color:#f87171">Bearish — surplus</span>
          </div>
          <div class="leg-item">
            <div class="leg-ring" style="border-color:#fbbf24"></div>
            <span style="color:#fbbf24">Watch</span>
          </div>
          <span style="width:1px;height:14px;background:#1e2a38;display:inline-block"></span>
          <div class="leg-item"><div class="leg-dot" style="background:#fb923c"></div><span style="color:#8a9bb0">Energy</span></div>
          <div class="leg-item"><div class="leg-dot" style="background:#fbbf24"></div><span style="color:#8a9bb0">Grain</span></div>
          <div class="leg-item"><div class="leg-dot" style="background:#4ade80"></div><span style="color:#8a9bb0">Soft</span></div>
          <div class="leg-item"><div class="leg-dot" style="background:#60a5fa"></div><span style="color:#8a9bb0">Metal</span></div>
          <span style="color:#2a3a4e;margin-left:auto;font-size:.58rem">Pin fill = type · Ring = signal · Hover for detail</span>
        </div>
        """, unsafe_allow_html=True)

        st.plotly_chart(build_map(COMMODITY_REGIONS, weather_cache, commodities),
                        use_container_width=True, config={"displayModeBar": False})

        # Region tabs
        st.markdown('<div class="sec-hdr" style="margin-top:4px">Region Detail</div>',
                    unsafe_allow_html=True)
        t_all, t_en, t_gr, t_so, t_me = st.tabs(
            ["All", "⚡ Energy", "🌾 Grains", "☕ Softs", "🔶 Metals"]
        )
        for tab, tfilter in [(t_all, None), (t_en, "energy"), (t_gr, "grain"), (t_so, "soft"), (t_me, "metal")]:
            with tab:
                filtered = sorted(
                    [r for r in COMMODITY_REGIONS if tfilter is None or r["type"] == tfilter],
                    key=lambda r: {"bull": 0, "bear": 1, "watch": 2}.get(
                        weather_signal(parse_weather(weather_cache.get(f"{r['lat']}_{r['lon']}", {})), r["type"])[0], 3
                    ),
                )
                for r in filtered:
                    key   = f"{r['lat']}_{r['lon']}"
                    w     = parse_weather(weather_cache.get(key, {}))
                    sig, reason = weather_signal(w, r["type"])
                    com   = commodities.get(r["commodity"], {})
                    price = com.get("price") or 0
                    chg   = com.get("changesPercentage") or 0
                    hi    = com.get("dayHigh") or 0
                    lo    = com.get("dayLow") or 0
                    wemo  = weather_emoji(w.get("description", ""))
                    arrow = "▲" if chg >= 0 else "▼"
                    cc    = "#4ade80" if chg >= 0 else "#f87171"
                    hl    = f"H {fmt_price(hi)} · L {fmt_price(lo)}" if hi and lo else ""

                    today_str = f"{arrow} {abs(chg):.2f}%" if chg else "—"
                    price_str = fmt_price(price) if price else "—"
                    temp_str  = f"{w.get('temp', '—')}°C"
                    cond_str  = f"{wemo} {w.get('description', '—')}"
                    wind_str  = f"{w.get('wind_speed', '—')} m/s"
                    humi_str  = f"{w.get('humidity', '—')}%"

                    # Header row
                    sig_colors = {"bull": "#4ade80", "bear": "#f87171", "watch": "#fbbf24"}
                    border_col = sig_colors.get(sig, "#2a3a4e")
                    st.markdown(
                        f'''<div style="background:#0e1218;border:1px solid #1e2a38;
                            border-left:3px solid {border_col};border-radius:8px;
                            padding:12px 14px 8px 14px;margin-bottom:2px">
                          <div style="display:flex;justify-content:space-between;align-items:flex-start">
                            <div>
                              <div style="font-size:.83rem;font-weight:600;color:#eef2f7">
                                {r["emoji"]} {r["name"]}
                              </div>
                              <div style="font-family:'Space Mono',monospace;font-size:.59rem;color:#4a6080;margin-top:2px">
                                {r["region"]} · {r["commodity"]}
                              </div>
                            </div>
                            <div style="text-align:right">
                              <span class="sig-pill sig-{sig}">{sig}</span>
                              <div style="font-size:.63rem;color:#4a6080;margin-top:5px;
                                          max-width:150px;text-align:right;line-height:1.4">
                                {reason}
                              </div>
                            </div>
                          </div>
                        </div>''',
                        unsafe_allow_html=True,
                    )
                    # Stats row using native Streamlit columns (no nested HTML)
                    stats = [
                        ("Futures Price", price_str, "#e8c97e"),
                        ("Today",         today_str, cc),
                        ("Temp",          temp_str,  "#eef2f7"),
                        ("Conditions",    cond_str,  "#eef2f7"),
                        ("Wind",          wind_str,  "#eef2f7"),
                        ("Humidity",      humi_str,  "#eef2f7"),
                    ]
                    if hl:
                        stats.insert(2, ("Hi / Lo", hl, "#eef2f7"))
                    cols = st.columns(len(stats))
                    for col, (lbl, val, col_hex) in zip(cols, stats):
                        with col:
                            st.markdown(
                                f'''<div style="background:#0a0d13;border:1px solid #1e2a38;
                                    border-radius:6px;padding:7px 10px;margin-bottom:8px">
                                  <div style="font-family:'Space Mono',monospace;font-size:.54rem;
                                              color:#4a6080;text-transform:uppercase;letter-spacing:.1em">
                                    {lbl}
                                  </div>
                                  <div style="font-size:.78rem;font-weight:600;color:{col_hex};margin-top:3px">
                                    {val}
                                  </div>
                                </div>''',
                                unsafe_allow_html=True,
                            )
                    st.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="sec-hdr">Live Commodity Futures</div>', unsafe_allow_html=True)

        for ctype, clabel in [("energy","⚡ Energy"),("metal","🔶 Metals"),("grain","🌾 Grains"),("soft","☕ Softs")]:
            st.markdown(f'<div class="com-group-hdr">{clabel}</div>', unsafe_allow_html=True)
            for canon, name, t, _, _ in FMP_COMMODITIES:
                if t != ctype:
                    continue
                d     = commodities.get(canon, {})
                price = d.get("price") or 0
                chg   = d.get("changesPercentage") or 0
                hi    = d.get("dayHigh") or 0
                lo    = d.get("dayLow") or 0
                arrow = "▲" if chg >= 0 else "▼"
                cc    = "#4ade80" if chg >= 0 else "#f87171"
                row_c = "bull-row" if chg > 0.05 else "bear-row" if chg < -0.05 else "flat-row"

                # weather dot
                rel  = next((r for r in COMMODITY_REGIONS if r["commodity"] == canon), None)
                wsig = "watch"
                if rel:
                    ww = parse_weather(weather_cache.get(f"{rel['lat']}_{rel['lon']}", {}))
                    wsig, _ = weather_signal(ww, rel["type"])
                wdot = {"bull":"#4ade80","bear":"#f87171","watch":"#fbbf24"}.get(wsig,"#94a3b8")
                hl   = f"H {fmt_price(hi)} · L {fmt_price(lo)}" if hi and lo else ""

                if not price:
                    st.markdown(f"""
                    <div class="com-row flat-row">
                      <div><div class="com-name">{name}</div><div class="com-sym">{canon}</div></div>
                      <span class="com-na">Loading…</span>
                    </div>""", unsafe_allow_html=True)
                    continue

                st.markdown(f"""
                <div class="com-row {row_c}">
                  <div style="flex:1">
                    <div class="com-name">{name}
                      <span style="font-size:.57rem;color:{wdot};margin-left:5px">● {wsig}</span>
                    </div>
                    <div class="com-sym">{canon}{f'  ·  {hl}' if hl else ''}</div>
                  </div>
                  <div style="text-align:right">
                    <div class="com-price">{fmt_price(price)}</div>
                    <div style="color:{cc};font-family:'Space Mono',monospace;font-size:.7rem">{arrow} {abs(chg):.2f}%</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # Alerts
        alert_list = [
            (r, a)
            for r in COMMODITY_REGIONS
            for a in parse_weather(weather_cache.get(f"{r['lat']}_{r['lon']}", {})).get("alerts", [])
        ]
        if alert_list:
            st.markdown('<div class="sec-hdr" style="margin-top:12px">⚠ Weather Alerts</div>',
                        unsafe_allow_html=True)
            for r, alert in alert_list:
                st.markdown(f"""
                <div class="alert-box"><b>{r['name']} · {r['region']}</b><br>
                {alert.get('event','Alert')}: {alert.get('description','')[:100]}…</div>""",
                            unsafe_allow_html=True)

        # Insight
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-hdr">Eagle Commodity Insight</div>', unsafe_allow_html=True)
        if st.button("⚡ Identify Opportunities", use_container_width=True, key="wc_insight_btn"):
            with st.spinner("Eagle scanning weather & price signals…"):
                st.session_state.wc_insight = gen_insight(COMMODITY_REGIONS, weather_cache, commodities)
        if st.session_state.get("wc_insight"):
            st.markdown(
                f'<div class="insight-box">{st.session_state.wc_insight}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
