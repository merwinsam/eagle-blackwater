"""
Blackwater One — Aviation Activity Index (ATI)
Global Airport Traffic Index = weighted sum of tracked airport flights today,
normalised to a base of 100 (last 7-day avg = 100).
Sector sub-indices + route-aware map.
"""

import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import time

# ── Credentials — loaded lazily to avoid module-level secret access ───────────
_BASE = "https://fr24api.flightradar24.com/api"

def _get_headers() -> dict:
    token = st.secrets["FR24_API_KEY"]
    return {
        "Authorization":  f"Bearer {token}",
        "Accept":         "application/json",
        "Accept-Version": "v1",
    }

# ══════════════════════════════════════════════════════════════════════════════
# AIRPORT REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
AIRPORTS = [
    # Energy
    {"iata":"MAF","city":"Midland TX",    "sector":"Energy",        "label":"Permian Basin",       "lat":31.94, "lon":-102.20,"baseline":85},
    {"iata":"HOU","city":"Houston",       "sector":"Energy",        "label":"Energy Capital",       "lat":29.65, "lon":-95.28, "baseline":410},
    {"iata":"IAH","city":"Houston Intl",  "sector":"Energy",        "label":"Gulf Energy Hub",      "lat":29.99, "lon":-95.34, "baseline":660},
    {"iata":"DOH","city":"Doha",          "sector":"Energy",        "label":"LNG Export",           "lat":25.27, "lon":51.61,  "baseline":330},
    {"iata":"DXB","city":"Dubai",         "sector":"Energy",        "label":"Gulf Nexus",           "lat":25.25, "lon":55.36,  "baseline":1080},
    # Technology
    {"iata":"SJC","city":"San Jose",      "sector":"Technology",    "label":"Silicon Valley",       "lat":37.36, "lon":-121.93,"baseline":270},
    {"iata":"SFO","city":"San Francisco", "sector":"Technology",    "label":"Bay Area Tech",        "lat":37.62, "lon":-122.38,"baseline":870},
    {"iata":"SEA","city":"Seattle",       "sector":"Technology",    "label":"Pacific NW Tech",      "lat":47.45, "lon":-122.31,"baseline":540},
    {"iata":"TPE","city":"Taipei",        "sector":"Technology",    "label":"Semiconductor Hub",    "lat":25.08, "lon":121.23, "baseline":410},
    {"iata":"ICN","city":"Seoul",         "sector":"Technology",    "label":"Korea Semi",           "lat":37.46, "lon":126.44, "baseline":630},
    # Finance
    {"iata":"JFK","city":"New York",      "sector":"Finance",       "label":"US Finance Core",      "lat":40.64, "lon":-73.78, "baseline":1100},
    {"iata":"LHR","city":"London",        "sector":"Finance",       "label":"Global Finance Hub",   "lat":51.47, "lon":-0.46,  "baseline":1280},
    {"iata":"ZRH","city":"Zurich",        "sector":"Finance",       "label":"Private Banking",      "lat":47.46, "lon":8.55,   "baseline":370},
    {"iata":"HKG","city":"Hong Kong",     "sector":"Finance",       "label":"Asia Finance",         "lat":22.31, "lon":113.91, "baseline":760},
    {"iata":"SIN","city":"Singapore",     "sector":"Finance",       "label":"SEA Finance",          "lat":1.36,  "lon":103.99, "baseline":700},
    # Tourism
    {"iata":"LAS","city":"Las Vegas",     "sector":"Tourism",       "label":"Leisure Bellwether",   "lat":36.08, "lon":-115.15,"baseline":1030},
    {"iata":"MCO","city":"Orlando",       "sector":"Tourism",       "label":"Theme Parks",          "lat":28.43, "lon":-81.31, "baseline":960},
    {"iata":"MIA","city":"Miami",         "sector":"Tourism",       "label":"Latin America Gateway","lat":25.80, "lon":-80.29, "baseline":850},
    {"iata":"HNL","city":"Honolulu",      "sector":"Tourism",       "label":"Pacific Tourism",      "lat":21.32, "lon":-157.92,"baseline":330},
    {"iata":"CUN","city":"Cancún",        "sector":"Tourism",       "label":"Resort Demand",        "lat":21.04, "lon":-86.87, "baseline":460},
    # Manufacturing
    {"iata":"PVG","city":"Shanghai",      "sector":"Manufacturing", "label":"China Export Hub",     "lat":31.14, "lon":121.81, "baseline":1030},
    {"iata":"SZX","city":"Shenzhen",      "sector":"Manufacturing", "label":"Electronics MFG",      "lat":22.64, "lon":113.81, "baseline":510},
    {"iata":"KUL","city":"Kuala Lumpur",  "sector":"Manufacturing", "label":"SEA Supply Chain",     "lat":2.74,  "lon":101.71, "baseline":580},
    {"iata":"BKK","city":"Bangkok",       "sector":"Manufacturing", "label":"SEA Industrial",       "lat":13.69, "lon":100.75, "baseline":620},
    # Resources
    {"iata":"PER","city":"Perth",         "sector":"Resources",     "label":"Iron Ore / LNG",       "lat":-31.94,"lon":115.97, "baseline":290},
    {"iata":"JNB","city":"Johannesburg",  "sector":"Resources",     "label":"Africa Mining",        "lat":-26.14,"lon":28.24,  "baseline":470},
    {"iata":"YYC","city":"Calgary",       "sector":"Resources",     "label":"Oil Sands",            "lat":51.13, "lon":-114.01,"baseline":340},
]
AP_BY_IATA   = {ap["iata"]: ap for ap in AIRPORTS}
SECTOR_CFG   = {
    "Energy":        {"color":"#f59e0b", "icon":"⚡"},
    "Technology":    {"color":"#60a5fa", "icon":"💻"},
    "Finance":       {"color":"#f472b6", "icon":"📈"},
    "Tourism":       {"color":"#34d399", "icon":"🌴"},
    "Manufacturing": {"color":"#fb923c", "icon":"🏭"},
    "Resources":     {"color":"#fbbf24", "icon":"⛏️"},
}
SECTOR_ORDER = ["Energy","Technology","Finance","Tourism","Manufacturing","Resources"]

KEY_ROUTES = [
    ("JFK","LHR","Transatlantic Finance","Finance"),
    ("JFK","ZRH","NY–Zurich Capital","Finance"),
    ("DXB","HOU","Gulf–US Energy","Energy"),
    ("DOH","LHR","Gulf–Europe","Energy"),
    ("TPE","SJC","Chip Supply Lane","Technology"),
    ("ICN","SFO","Korea–Silicon Valley","Technology"),
    ("PVG","SFO","China–US West","Manufacturing"),
    ("SIN","HKG","SEA–Asia Finance","Finance"),
    ("PER","SIN","Aus Resources–Asia","Resources"),
    ("PVG","ICN","China–Korea MFG","Manufacturing"),
    ("MIA","CUN","Caribbean Tourism","Tourism"),
    ("LAS","JFK","US Domestic Leisure","Tourism"),
    ("HOU","MAF","Texas Energy Shuttle","Energy"),
    ("YYC","HOU","Canada–US Energy","Energy"),
    ("LHR","ZRH","London–Zurich","Finance"),
    ("LHR","SIN","Europe–Asia Finance","Finance"),
    ("SFO","SEA","West Coast Tech","Technology"),
    ("TPE","HKG","Asia Semi–Finance","Technology"),
    ("KUL","SIN","SEA Manufacturing","Manufacturing"),
    ("BKK","PVG","SEA–China Supply","Manufacturing"),
]

_ICAO = {
    "KMAF":"MAF","KHOU":"HOU","KIAH":"IAH","OTHH":"DOH","OMDB":"DXB",
    "KSJC":"SJC","KSFO":"SFO","KSEA":"SEA","RCTP":"TPE","RKSI":"ICN",
    "KJFK":"JFK","EGLL":"LHR","LSZH":"ZRH","VHHH":"HKG","WSSS":"SIN",
    "KLAS":"LAS","KMCO":"MCO","KMIA":"MIA","PHNL":"HNL","MMUN":"CUN",
    "ZSPD":"PVG","ZGSZ":"SZX","WMKK":"KUL","VTBS":"BKK",
    "YPPH":"PER","FAOR":"JNB","CYYC":"YYC",
}

def _to_iata(code: str) -> str:
    c = (code or "").upper().strip()
    if c in _ICAO: return _ICAO[c]
    if len(c) == 4 and c[0] == "K": return c[1:]
    return c[:3] if len(c) == 4 else c


# ══════════════════════════════════════════════════════════════════════════════
# CSS — Refined dark terminal aesthetic
# Sharper hierarchy, better spacing, cleaner data presentation
# ══════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&family=Bebas+Neue&display=swap');

:root {
  --bg:      #080d14;
  --bg1:     #0c1420;
  --bg2:     #10192a;
  --bg3:     #162030;
  --bg4:     #1c2a3e;
  --b0:      #1e2e42;
  --b1:      #253848;
  --b2:      #2e4a62;
  --tx0:     #e8f0f8;
  --tx1:     #9ab4cc;
  --tx2:     #5a7a96;
  --tx3:     #344e66;
  --amber:   #e8a020;
  --amber2:  #fbbf24;
  --green:   #1db954;
  --green2:  #22c55e;
  --red:     #e05555;
  --red2:    #f87171;
  --blue:    #4a9ede;
  --indigo:  #6e7ff0;
  --teal:    #2dd4bf;
  --shadow:  0 4px 24px rgba(0,0,0,0.5);
}

* { box-sizing:border-box; margin:0; padding:0; }

[data-testid="stAppViewContainer"] { background:var(--bg) !important; }
[data-testid="stHeader"]           { background:transparent !important; }
.block-container                   { padding-top:0 !important; max-width:100% !important; }
[data-testid="column"]             { padding:0 6px !important; }

/* ── Top bar ─────────────────────────────────────────────────────────── */
.ati-topbar {
  background: linear-gradient(90deg, #0c1420 0%, #0e1828 100%);
  border-bottom: 1px solid var(--b0);
  height: 54px;
  display: flex; align-items: center;
  padding: 0 28px; gap: 20px;
  position: sticky; top: 0; z-index: 100;
  box-shadow: 0 1px 0 var(--b0), 0 4px 20px rgba(0,0,0,0.4);
}
.ati-wordmark {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.45rem; letter-spacing: .08em;
  background: linear-gradient(135deg, #e8a020 0%, #fbbf24 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.ati-divider { width:1px; height:26px; background:var(--b1); flex-shrink:0; }
.ati-subtitle {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .6rem; color: var(--tx2);
  letter-spacing: .22em; text-transform: uppercase;
}
.ati-badge {
  background: rgba(74,158,222,.08);
  border: 1px solid rgba(74,158,222,.2);
  border-radius: 3px; padding: 3px 11px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: .55rem; color: var(--blue);
  letter-spacing: .12em; text-transform: uppercase;
}
.ati-clock {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .6rem; color: var(--tx3);
  margin-left: auto; letter-spacing: .05em;
}
.live-dot {
  display:inline-block; width:6px; height:6px; border-radius:50%;
  background:var(--green); margin-right:7px;
  animation: livepulse 2.5s ease-in-out infinite;
}
@keyframes livepulse { 0%,100%{opacity:1;box-shadow:0 0 4px var(--green)} 50%{opacity:.3;box-shadow:none} }

/* ── Section header ──────────────────────────────────────────────────── */
.sec-hdr {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .57rem; font-weight: 600;
  color: var(--tx3); text-transform: uppercase;
  letter-spacing: .26em;
  padding: 0 0 10px; margin-bottom: 18px;
  border-bottom: 1px solid var(--b0);
  display: flex; align-items: center; gap: 10px;
}
.sec-hdr em {
  font-style: normal; color: var(--tx2);
  letter-spacing: .1em;
}
.sec-hdr-accent {
  display: inline-block; width: 18px; height: 2px;
  background: var(--amber); border-radius: 1px;
}

/* ── Hero panel ──────────────────────────────────────────────────────── */
.hero-wrap {
  background: linear-gradient(135deg, #0c1824 0%, #080f1a 100%);
  border: 1px solid var(--b0);
  border-radius: 12px;
  padding: 32px 40px;
  display: flex; align-items: center; gap: 48px;
  position: relative; overflow: hidden;
  box-shadow: var(--shadow);
  margin-bottom: 28px;
}
.hero-wrap::before {
  content: '';
  position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 40% 80% at 5% 50%, rgba(232,160,32,.09), transparent);
}
.hero-wrap::after {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(232,160,32,.3), transparent);
}
.hero-ati-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .57rem; color: var(--tx3);
  text-transform: uppercase; letter-spacing: .28em; margin-bottom: 8px;
}
.hero-ati-number {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 8.5rem; line-height: .85; color: var(--amber);
  text-shadow: 0 0 60px rgba(232,160,32,.25);
}
.hero-ati-sub {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .62rem; color: var(--tx2);
  letter-spacing: .15em; text-transform: uppercase; margin-top: 8px;
}
.hero-sep { width: 1px; height: 110px; background: var(--b1); flex-shrink: 0; }
.hero-delta-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .57rem; color: var(--tx3);
  text-transform: uppercase; letter-spacing: .28em; margin-bottom: 8px;
}
.hero-delta-val {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 4rem; line-height: 1;
}
.hero-status {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .7rem; letter-spacing: .14em;
  text-transform: uppercase; margin-top: 6px;
}
.hero-meta {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .7rem; color: var(--tx2); line-height: 2.1; margin-top: 14px;
}
.hero-meta b { color: var(--tx0); font-weight: 500; }
.hero-key { flex: 1; }
.hero-key-title {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .57rem; color: var(--tx3);
  text-transform: uppercase; letter-spacing: .22em; margin-bottom: 14px;
}
.key-row {
  display: flex; align-items: center; gap: 10px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: .68rem; color: var(--tx2); margin-bottom: 9px;
}
.key-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }

/* ── Mover cards ─────────────────────────────────────────────────────── */
.mover-card {
  background: var(--bg2);
  border: 1px solid var(--b0);
  border-radius: 10px; padding: 22px 24px;
  position: relative; overflow: hidden;
  height: 100%;
  transition: border-color .2s, transform .15s;
}
.mover-card:hover { border-color: var(--b2); transform: translateY(-1px); }
.mover-top-bar {
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  border-radius: 10px 10px 0 0;
}
.mover-rank {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .54rem; color: var(--tx3);
  text-transform: uppercase; letter-spacing: .22em; margin-bottom: 12px;
}
.mover-iata {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 3.2rem; line-height: 1; margin-bottom: 4px;
}
.mover-city {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: .82rem; font-weight: 500; color: var(--tx0);
}
.mover-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .6rem; color: var(--tx3); margin-top: 2px;
}
.mover-divider { height: 1px; background: var(--b0); margin: 14px 0; }
.mover-pct {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.4rem; line-height: 1;
}
.mover-signal {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .65rem; color: var(--tx2); line-height: 1.7; margin-top: 8px;
}
.mover-flights {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .6rem; color: var(--tx3); margin-top: 6px;
}

/* ── Sector sub-index cards ──────────────────────────────────────────── */
.subidx-card {
  background: var(--bg2);
  border: 1px solid var(--b0);
  border-radius: 8px; padding: 16px 18px;
  position: relative; overflow: hidden;
  transition: border-color .2s;
}
.subidx-card:hover { border-color: var(--b2); }
.subidx-glow {
  position: absolute; bottom: 0; right: 0;
  width: 70px; height: 70px; border-radius: 50%;
  filter: blur(30px); opacity: .15;
}
.subidx-icon {
  font-size: 1.1rem; margin-bottom: 8px; display: block;
}
.subidx-name {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .55rem; color: var(--tx3);
  text-transform: uppercase; letter-spacing: .2em; margin-bottom: 8px;
}
.subidx-val {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2.6rem; line-height: 1;
}
.subidx-chg {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .65rem; margin-top: 5px; letter-spacing: .04em;
}
.subidx-bar-bg {
  height: 2px; background: var(--b0);
  border-radius: 1px; margin-top: 10px;
}
.subidx-bar-fg { height: 2px; border-radius: 1px; }

/* ── Map callout ─────────────────────────────────────────────────────── */
.map-callout {
  background: var(--bg3);
  border: 1px solid var(--b1);
  border-left: 3px solid var(--amber);
  border-radius: 0 8px 8px 0;
  padding: 12px 20px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: .72rem; color: var(--tx1); line-height: 1.6;
  margin-bottom: 14px;
}
.map-callout strong { color: var(--tx0); }

/* ── Change badge ────────────────────────────────────────────────────── */
.chg {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .72rem; font-weight: 500;
  padding: 4px 10px; border-radius: 4px;
  text-align: center; white-space: nowrap;
  display: inline-block; min-width: 64px;
  letter-spacing: .02em;
}
.up   { background: rgba(29,185,84,.1);  color: #22c55e; border:1px solid rgba(29,185,84,.2); }
.dn   { background: rgba(224,85,85,.1);  color: #f87171; border:1px solid rgba(224,85,85,.2); }
.flat { background: rgba(58,96,128,.1);  color: #4a7090; border:1px solid rgba(58,96,128,.2); }

/* ── Airport table ───────────────────────────────────────────────────── */
.apt-table {
  background: var(--bg1);
  border: 1px solid var(--b0);
  border-radius: 10px; overflow: hidden;
  box-shadow: var(--shadow);
}
.apt-head {
  display: grid;
  grid-template-columns: 60px 1fr 80px 80px 86px 120px;
  gap: 8px; padding: 10px 20px;
  background: var(--bg3);
  font-family: 'IBM Plex Mono', monospace;
  font-size: .54rem; color: var(--tx3);
  text-transform: uppercase; letter-spacing: .18em;
  border-bottom: 1px solid var(--b0);
}
.apt-row {
  display: grid;
  grid-template-columns: 60px 1fr 80px 80px 86px 120px;
  gap: 8px; padding: 13px 20px;
  border-bottom: 1px solid var(--b0);
  align-items: center;
  transition: background .12s;
}
.apt-row:last-child { border-bottom: none; }
.apt-row:hover { background: var(--bg3); }
.apt-iata {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1rem; letter-spacing: .04em;
}
.apt-city {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: .78rem; font-weight: 500; color: var(--tx0);
}
.apt-lbl {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .6rem; color: var(--tx3); margin-top: 2px;
}
.apt-num {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .8rem; color: var(--tx0);
  text-align: right; font-weight: 500;
}
.apt-avg {
  font-family: 'IBM Plex Mono', monospace;
  font-size: .76rem; color: var(--tx2); text-align: right;
}
.spark-bg { height: 3px; background: var(--b0); border-radius: 2px; overflow: hidden; }
.spark-fg { height: 3px; border-radius: 2px; transition: width .4s ease; }
.show-more {
  padding: 12px 20px; text-align: center;
  font-family: 'IBM Plex Mono', monospace;
  font-size: .6rem; color: var(--tx3); letter-spacing: .1em;
  border-top: 1px solid var(--b0);
  text-transform: uppercase;
}

/* ── Intelligence narrative ──────────────────────────────────────────── */
.insight-box {
  background: var(--bg2);
  border: 1px solid var(--b0);
  border-left: 3px solid var(--amber);
  border-radius: 0 10px 10px 0;
  padding: 22px 28px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: .72rem; line-height: 2.0; color: var(--tx1);
  white-space: pre-wrap;
  box-shadow: var(--shadow);
}

/* ── Scrollbar ───────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--b2); border-radius: 2px; }

/* ── Streamlit overrides ─────────────────────────────────────────────── */
.stButton > button {
  background: var(--bg2) !important;
  border: 1px solid var(--b0) !important;
  color: var(--tx2) !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: .68rem !important; letter-spacing: .05em !important;
  border-radius: 6px !important;
  transition: all .15s !important;
}
.stButton > button:hover {
  border-color: var(--amber) !important;
  color: var(--amber) !important;
  background: rgba(232,160,32,.06) !important;
}
.stSelectbox > div > div {
  background: var(--bg2) !important;
  border: 1px solid var(--b0) !important;
  border-radius: 6px !important;
  color: var(--tx1) !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: .72rem !important;
}
.stProgress > div > div > div { background: var(--amber) !important; }
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
# DATA LAYER
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_window(iata_list: list, dt_from: datetime, dt_to: datetime) -> dict:
    """Fetch flight counts for a time window, with retry on 429."""
    counts = defaultdict(int)

    for i in range(0, len(iata_list), 15):
        batch  = ",".join(iata_list[i:i+15])
        params = {
            "flight_datetime_from": dt_from.strftime("%Y-%m-%dT%H:%M:%S"),
            "flight_datetime_to":   dt_to.strftime("%Y-%m-%dT%H:%M:%S"),
            "airports": batch,
            "limit": 1000,
        }
        for attempt in range(3):
            try:
                r = requests.get(
                    f"{_BASE}/flight-summary/light",
                    headers=_get_headers(),
                    params=params,
                    timeout=25,
                )
                if r.status_code == 429:
                    time.sleep(12 * (attempt + 1))
                    continue
                if not r.ok:
                    break
                for f in r.json().get("data", []):
                    for field in ("origin_icao","orig_icao","destination_icao","dest_icao"):
                        raw = (f.get(field) or "").upper()
                        if raw:
                            iata = _to_iata(raw)
                            if iata in iata_list:
                                counts[iata] += 1
                            break
                break
            except Exception:
                break

        time.sleep(2.0)

    return dict(counts)


@st.cache_data(ttl=3600)   # cache for 1 hour — baseline doesn't change intraday
def _fetch_baseline_day(iata_list_key: str, date_str: str) -> dict:
    """
    Cached wrapper for a single past-day baseline fetch.
    iata_list_key is a comma-joined string (hashable for cache).
    date_str is YYYY-MM-DD.
    """
    iata_list = iata_list_key.split(",")
    d_start   = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    d_end     = d_start + timedelta(days=1)
    return _fetch_window(iata_list, d_start, d_end)


def load_traffic(iata_list: list, prog=None) -> dict:
    now     = datetime.now(timezone.utc)
    t0      = now.replace(hour=0, minute=0, second=0, microsecond=0)
    iata_key = ",".join(iata_list)

    if prog: prog(5, "Fetching today's traffic…")
    today_c = _fetch_window(iata_list, t0, now)

    daily = defaultdict(list)
    for day in range(1, 8):
        if prog: prog(5 + int(day / 7 * 88), f"Loading baseline day −{day}…")
        date_str = (t0 - timedelta(days=day)).strftime("%Y-%m-%d")
        dc = _fetch_baseline_day(iata_key, date_str)
        for iata in iata_list:
            daily[iata].append(dc.get(iata, 0))
        # No extra sleep needed — _fetch_window already sleeps 2s per batch

    if prog: prog(100, "Done.")
    result = {}
    for iata in iata_list:
        days = daily[iata]
        result[iata] = {
            "today": today_c.get(iata, 0),
            "avg7":  sum(days) / len(days) if days else 0,
            "days":  days,
        }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# INDEX MATH
# ══════════════════════════════════════════════════════════════════════════════
def calc_ati(traffic: dict, airports: list) -> dict:
    sum_today = sum(traffic.get(ap["iata"], {}).get("today", 0) for ap in airports)
    sum_avg   = sum(traffic.get(ap["iata"], {}).get("avg7",  0) for ap in airports)
    index = round(sum_today / sum_avg * 100, 1) if sum_avg > 0 else 100.0
    pct   = round(index - 100, 1)
    return {"index": index, "pct": pct, "sum_today": sum_today, "sum_avg": sum_avg}

def calc_sector_ati(traffic, airports, sector):
    return calc_ati(traffic, [ap for ap in airports if ap["sector"] == sector])

def pct_chg(today, avg) -> float:
    return round((today - avg) / avg * 100, 1) if avg > 0 else 0.0

def state(pct: float):
    if pct >= 20:  return "SPIKE",    "#e05555"
    if pct >= 8:   return "ELEVATED", "#e8a020"
    if pct >= -8:  return "NORMAL",   "#1db954"
    if pct >= -20: return "SUBDUED",  "#6e7ff0"
    return "LOW",  "#e05555"

def chg_cls(pct: float) -> str:
    return "up" if pct > 3 else "dn" if pct < -3 else "flat"


# ══════════════════════════════════════════════════════════════════════════════
# MAP
# ══════════════════════════════════════════════════════════════════════════════
def build_map(traffic: dict) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        geo=dict(
            showland=True,       landcolor="#09111c",
            showocean=True,      oceancolor="#050c14",
            showcoastlines=True, coastlinecolor="#1a3050", coastlinewidth=0.8,
            showcountries=True,  countrycolor="#0e1e2e",   countrywidth=0.4,
            showlakes=False,     showrivers=False,
            showframe=False,
            projection_type="natural earth",
            bgcolor="#050c14",
            lataxis_range=[-58, 78],
        ),
        paper_bgcolor="#050c14",
        margin=dict(l=0, r=0, t=0, b=0),
        height=460,
        showlegend=True,
    )

    # Routes
    for orig_iata, dest_iata, label, sector in KEY_ROUTES:
        o = AP_BY_IATA.get(orig_iata)
        d = AP_BY_IATA.get(dest_iata)
        if not o or not d: continue
        color   = SECTOR_CFG[sector]["color"]
        td      = traffic.get(dest_iata, {})
        avg     = td.get("avg7", 1)
        today   = td.get("today", 0)
        pct     = pct_chg(today, avg)
        opacity = 0.12 + min(0.30, abs(pct) / 100)
        lats = [o["lat"] + (d["lat"]-o["lat"])*t for t in [0,.17,.33,.5,.67,.83,1]]
        lons = [o["lon"] + (d["lon"]-o["lon"])*t for t in [0,.17,.33,.5,.67,.83,1]]
        fig.add_trace(go.Scattergeo(
            lat=lats, lon=lons, mode="lines",
            line=dict(width=0.9, color=color), opacity=opacity,
            hovertemplate=f"<b>{label}</b><br>{orig_iata} → {dest_iata}<extra></extra>",
            showlegend=False,
        ))

    # Airport halos + dots
    for ap in AIRPORTS:
        td    = traffic.get(ap["iata"], {})
        today = td.get("today", 0)
        avg   = td.get("avg7",  ap["baseline"])
        pct   = pct_chg(today, avg)
        lbl, color = state(pct)
        sm    = SECTOR_CFG[ap["sector"]]
        sign  = "+" if pct >= 0 else ""

        # Halo glow
        halo = max(14, min(52, avg / 28 + 10))
        fig.add_trace(go.Scattergeo(
            lat=[ap["lat"]], lon=[ap["lon"]], mode="markers",
            marker=dict(size=halo, color=sm["color"], opacity=0.05),
            hoverinfo="skip", showlegend=False,
        ))
        # Pin
        fig.add_trace(go.Scattergeo(
            lat=[ap["lat"]], lon=[ap["lon"]],
            mode="markers+text",
            marker=dict(
                size=9, color=color, opacity=0.92,
                line=dict(width=1.5, color="#050c14"),
            ),
            text=[ap["iata"]],
            textposition="top center",
            textfont=dict(size=7, color="#1e3048", family="IBM Plex Mono"),
            hovertemplate=(
                f"<b>{ap['iata']} · {ap['city']}</b><br>"
                f"{ap['sector']} — {ap['label']}<br>"
                f"Today: <b>{today}</b> · 7D avg: {avg:.0f}<br>"
                f"Change: {sign}{pct:.0f}% · <b>{lbl}</b>"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Legend
    for lbl, clr in [
        ("SPIKE  >+20%","#e05555"),
        ("ELEVATED +8–20%","#e8a020"),
        ("NORMAL  ±8%","#1db954"),
        ("SUBDUED  <-8%","#6e7ff0"),
    ]:
        fig.add_trace(go.Scattergeo(
            lat=[None], lon=[None], mode="markers",
            marker=dict(size=8, color=clr), name=lbl, showlegend=True,
        ))

    fig.update_layout(legend=dict(
        x=0.01, y=0.06,
        bgcolor="rgba(5,12,20,0.88)",
        bordercolor="#1e2e42", borderwidth=1,
        font=dict(family="IBM Plex Mono", size=9, color="#3a5878"),
    ))
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════════════════
def render_airline_traffic():
    st.markdown(CSS, unsafe_allow_html=True)

    ts = datetime.now(timezone.utc).strftime("%d %b %Y  %H:%M") + " UTC"
    st.markdown(f"""
    <div class="ati-topbar">
      <span class="ati-wordmark">Blackwater One</span>
      <div class="ati-divider"></div>
      <span class="ati-subtitle">Aviation Activity Index</span>
      <div class="ati-divider"></div>
      <span class="ati-badge">ATI · Global Macro Signal</span>
      <span class="ati-clock"><span class="live-dot"></span>{ts}</span>
    </div>
    <div style="height:18px"></div>
    """, unsafe_allow_html=True)

    # ── Nav ───────────────────────────────────────────────────────────────────
    n1, n2, _ = st.columns([1.1, 1.1, 7])
    with n1:
        if st.button("← Back", key="ati_back", use_container_width=True):
            st.session_state.page = "eagle"
            st.rerun()
    with n2:
        if st.button("⟳ Refresh", key="ati_refresh", use_container_width=True):
            for k in ["ati_loaded","ati_loaded_at","ati_traffic","ati_insight","ati_show_all","ati_debug"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ── ATI Explainer ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#0b0e12;border:1px solid #1a2330;border-left:3px solid #e8c97e;
                border-radius:0 6px 6px 0;padding:16px 20px;margin-bottom:16px">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#e8c97e;
                  text-transform:uppercase;letter-spacing:0.14em;margin-bottom:8px">
        What This Page Tells You
      </div>
      <div style="font-size:0.88rem;color:#aabccc;line-height:1.85;font-family:'Inter',sans-serif">
        The <b style="color:#f0f4f8">Aviation Activity Index (ATI)</b> tracks real-time flight volumes
        across 27 strategically chosen airports — grouped into six economic sectors:
        <b style="color:#f0f4f8">Energy, Technology, Finance, Tourism, Manufacturing</b> and <b style="color:#f0f4f8">Resources</b>.
        Spikes in aviation activity at sector-specific hubs often precede or confirm
        macroeconomic moves — an energy sector surge in Houston or Doha may signal supply chain
        tightening, while a tech corridor uptick across San Jose and Taipei can reflect
        accelerating demand cycles. Use ATI as a <b style="color:#f0f4f8">leading non-financial indicator</b>
        to cross-reference your market signals.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data — only refetch if not loaded or older than 1 hour ──────────
    iata_list  = [ap["iata"] for ap in AIRPORTS]
    cache_age  = time.time() - st.session_state.get("ati_loaded_at", 0)
    needs_load = not st.session_state.get("ati_loaded") or cache_age > 3600

    if needs_load:
        pb = st.progress(0, "Initialising Aviation Activity Index…")
        traffic = load_traffic(iata_list, prog=lambda p, t: pb.progress(p, text=t))
        pb.empty()
        st.session_state.ati_traffic  = traffic
        st.session_state.ati_loaded   = True
        st.session_state.ati_loaded_at = time.time()
    traffic = st.session_state.get("ati_traffic", {})

    global_ati  = calc_ati(traffic, AIRPORTS)
    sector_atis = {s: calc_sector_ati(traffic, AIRPORTS, s) for s in SECTOR_ORDER}

    g_idx   = global_ati["index"]
    g_pct   = global_ati["pct"]
    g_lbl, g_color = state(g_pct)
    g_sign  = "+" if g_pct >= 0 else ""
    g_arrow = "▲" if g_pct >= 0 else "▼"
    now_date = datetime.now().strftime("%d %b %Y")

    # Row data
    all_rows = []
    for ap in AIRPORTS:
        td    = traffic.get(ap["iata"], {})
        today = td.get("today", 0)
        avg   = td.get("avg7", ap["baseline"])
        pct   = pct_chg(today, avg)
        all_rows.append({"ap": ap, "today": today, "avg": avg, "pct": pct})
    all_rows_sorted = sorted(all_rows, key=lambda x: -x["pct"])
    top3    = all_rows_sorted[:3]
    hottest = all_rows_sorted[0]
    coldest = sorted(all_rows, key=lambda x: x["pct"])[0]

    # Callout text
    if hottest["pct"] >= 10:
        callout_txt = (f'<strong>{hottest["ap"]["city"]} ({hottest["ap"]["iata"]})</strong> '
                       f'traffic +{hottest["pct"]:.0f}% above baseline — '
                       f'{hottest["ap"]["label"]} showing elevated activity.')
    elif coldest["pct"] <= -10:
        callout_txt = (f'<strong>{coldest["ap"]["city"]} ({coldest["ap"]["iata"]})</strong> '
                       f'traffic {coldest["pct"]:.0f}% below baseline — '
                       f'{coldest["ap"]["label"]} demand cooling.')
    else:
        callout_txt = (f'Global aviation running at ATI <strong>{g_idx:.1f}</strong> — '
                       f'within normal range across all tracked sectors.')

    # ══════════════════════════════════════════════════════════════════════════
    # HERO
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div class="hero-wrap">
      <div>
        <div class="hero-ati-label">Global Aviation Activity Index</div>
        <div class="hero-ati-number">{g_idx:.1f}</div>
        <div class="hero-ati-sub">Airport Traffic Index · ATI</div>
      </div>
      <div class="hero-sep"></div>
      <div>
        <div class="hero-delta-label">vs 7-Day Baseline</div>
        <div class="hero-delta-val" style="color:{g_color}">{g_arrow} {g_sign}{g_pct:.1f}%</div>
        <div class="hero-status" style="color:{g_color}">{g_lbl}</div>
        <div class="hero-meta">
          Flights today  <b>{global_ati["sum_today"]:,}</b><br>
          7-day average  <b>{global_ati["sum_avg"]:.0f}</b><br>
          Airports tracked  <b>{len(AIRPORTS)}</b><br>
          {now_date}
        </div>
      </div>
      <div class="hero-sep"></div>
      <div class="hero-key">
        <div class="hero-key-title">Index Key</div>
        <div class="key-row"><div class="key-dot" style="background:#e05555"></div>&gt; 120 · Major spike</div>
        <div class="key-row"><div class="key-dot" style="background:#e8a020"></div>108–120 · Elevated</div>
        <div class="key-row"><div class="key-dot" style="background:#1db954"></div>92–108 · Normal range</div>
        <div class="key-row"><div class="key-dot" style="background:#6e7ff0"></div>80–92 · Subdued</div>
        <div class="key-row"><div class="key-dot" style="background:#e05555"></div>&lt; 80 · Significant drop</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TOP 3 MOVERS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="sec-hdr">
      <div class="sec-hdr-accent"></div>
      <em>Top 3</em> &nbsp;Biggest Movers Today
    </div>
    """, unsafe_allow_html=True)

    mc1, mc2, mc3 = st.columns(3, gap="medium")
    rank_labels   = ["#1 · Biggest Move", "#2 · Biggest Move", "#3 · Biggest Move"]
    for col, row, rlbl in zip([mc1, mc2, mc3], top3, rank_labels):
        ap    = row["ap"]
        sm    = SECTOR_CFG[ap["sector"]]
        pct   = row["pct"]
        today = row["today"]
        avg   = row["avg"]
        _, color = state(pct)
        sign  = "+" if pct >= 0 else ""
        if pct >= 20:
            signal = f"Significant spike vs baseline. Possible {ap['sector'].lower()} surge."
        elif pct >= 8:
            signal = f"Above-trend activity at {ap['label']}."
        elif pct <= -20:
            signal = f"Sharp drop. {ap['sector']} demand may be cooling."
        elif pct <= -8:
            signal = f"Below-average traffic. Watch for sector softness."
        else:
            signal = f"Within normal range for {ap['label']}."
        with col:
            st.markdown(f"""
            <div class="mover-card">
              <div class="mover-top-bar" style="background:{color}"></div>
              <div class="mover-rank">{rlbl} · {sm["icon"]} {ap["sector"]}</div>
              <div class="mover-iata" style="color:{color}">{ap["iata"]}</div>
              <div class="mover-city">{ap["city"]}</div>
              <div class="mover-label">{ap["label"]}</div>
              <div class="mover-divider"></div>
              <div class="mover-pct" style="color:{color}">{sign}{pct:.0f}%</div>
              <div class="mover-signal">{signal}</div>
              <div class="mover-flights">Today {today:,} · Avg {avg:.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTOR SUB-INDICES
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="sec-hdr">
      <div class="sec-hdr-accent"></div>
      <em>Sector</em> &nbsp;Sub-Indices
    </div>
    """, unsafe_allow_html=True)

    s_cols = st.columns(len(SECTOR_ORDER))
    for col, sector in zip(s_cols, SECTOR_ORDER):
        sm  = SECTOR_CFG[sector]
        ati = sector_atis[sector]
        idx = ati["index"]
        pct = ati["pct"]
        _, color = state(pct)
        sign = "+" if pct >= 0 else ""
        bar_w = min(100, max(4, (idx / 120) * 100))
        with col:
            st.markdown(f"""
            <div class="subidx-card">
              <div class="subidx-glow" style="background:{sm['color']}"></div>
              <span class="subidx-icon">{sm['icon']}</span>
              <div class="subidx-name">{sector}</div>
              <div class="subidx-val" style="color:{color}">{idx:.0f}</div>
              <div class="subidx-chg" style="color:{color}">{sign}{pct:.1f}%</div>
              <div class="subidx-bar-bg">
                <div class="subidx-bar-fg" style="width:{bar_w:.0f}%;background:{color}"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # MAP
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="sec-hdr">
      <div class="sec-hdr-accent"></div>
      <em>Global</em> &nbsp;Traffic Map with Key Routes
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="map-callout">📡 {callout_txt}</div>', unsafe_allow_html=True)
    st.plotly_chart(
        build_map(traffic),
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False},
    )

    # Sector chips
    chips = "".join(
        f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:.57rem;'
        f'color:{SECTOR_CFG[s]["color"]};background:{SECTOR_CFG[s]["color"]}12;'
        f'border:1px solid {SECTOR_CFG[s]["color"]}26;'
        f'border-radius:3px;padding:3px 10px">'
        f'{SECTOR_CFG[s]["icon"]} {s}</span>'
        for s in SECTOR_ORDER
    )
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;margin-bottom:24px">{chips}</div>',
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # AIRPORT TABLE
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="sec-hdr">
      <div class="sec-hdr-accent"></div>
      <em>Airport</em> &nbsp;Activity Table
    </div>
    """, unsafe_allow_html=True)

    sort_by = st.selectbox(
        "", ["% Change ↓", "% Change ↑", "Flights Today ↓", "Sector"],
        key="ati_sort", label_visibility="collapsed",
    )
    key_fn = {
        "% Change ↓":      lambda x: -x["pct"],
        "% Change ↑":      lambda x:  x["pct"],
        "Flights Today ↓": lambda x: -x["today"],
        "Sector":          lambda x: (x["ap"]["sector"], -x["pct"]),
    }[sort_by]
    sorted_rows = sorted(all_rows, key=key_fn)
    show_all    = st.session_state.get("ati_show_all", False)
    rows_shown  = sorted_rows if show_all else sorted_rows[:8]

    st.markdown("""
    <div class="apt-table">
      <div class="apt-head">
        <span>IATA</span>
        <span>Airport</span>
        <span style="text-align:right">TODAY</span>
        <span style="text-align:right">7D AVG</span>
        <span style="text-align:right">CHANGE</span>
        <span>TREND</span>
      </div>
    """, unsafe_allow_html=True)

    rows_html = ""
    for row in rows_shown:
        ap      = row["ap"]
        sm      = SECTOR_CFG[ap["sector"]]
        today_v = row["today"]
        avg_v   = row["avg"]
        pct_v   = row["pct"]
        _, color = state(pct_v)
        sign    = "+" if pct_v >= 0 else ""
        cc      = chg_cls(pct_v)
        bar_w   = min(100, max(2, (today_v / max(avg_v, 1)) * 50))
        rows_html += f"""
        <div class="apt-row">
          <span class="apt-iata" style="color:{sm['color']}">{ap['iata']}</span>
          <div>
            <div class="apt-city">{ap['city']}</div>
            <div class="apt-lbl">{ap['label']}</div>
          </div>
          <span class="apt-num">{today_v:,}</span>
          <span class="apt-avg">{avg_v:.0f}</span>
          <span style="text-align:right"><span class="chg {cc}">{sign}{pct_v:.0f}%</span></span>
          <div>
            <div class="spark-bg">
              <div class="spark-fg" style="width:{bar_w:.0f}%;background:{color}"></div>
            </div>
          </div>
        </div>"""

    remaining = len(sorted_rows) - len(rows_shown)
    if not show_all and remaining > 0:
        rows_html += f'<div class="show-more">+ {remaining} more airports</div>'

    st.markdown(rows_html + "</div>", unsafe_allow_html=True)

    if not show_all and remaining > 0:
        if st.button(f"Show all {len(sorted_rows)} airports", key="ati_show_more"):
            st.session_state.ati_show_all = True
            st.rerun()

    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # INTELLIGENCE NARRATIVE
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="sec-hdr">
      <div class="sec-hdr-accent"></div>
      <em>Eagle</em> &nbsp;Intelligence Narrative
    </div>
    """, unsafe_allow_html=True)

    nc1, nc2, _ = st.columns([1.6, 1.4, 4])
    with nc1:
        gen_btn = st.button("⚡ Generate Narrative", key="ati_gen", use_container_width=True)
    with nc2:
        focus = st.selectbox("", ["Global"] + SECTOR_ORDER, key="ati_focus",
                             label_visibility="collapsed")

    if gen_btn:
        lines = [f" Global ATI: {g_idx:.1f} ({g_sign}{g_pct:.1f}% vs 7D) — {g_lbl}"]
        for sector in SECTOR_ORDER:
            ati = sector_atis[sector]
            aps = [ap for ap in AIRPORTS if ap["sector"] == sector]
            movers = sorted(
                [{"iata": ap["iata"], "city": ap["city"],
                  "pct": pct_chg(traffic.get(ap["iata"],{}).get("today",0),
                                 traffic.get(ap["iata"],{}).get("avg7",1))}
                 for ap in aps],
                key=lambda x: abs(x["pct"]), reverse=True
            )[:3]
            mv = " | ".join(f'{m["iata"]} {("+" if m["pct"]>=0 else "")}{m["pct"]:.0f}%' for m in movers)
            sv = "+" if ati["pct"] >= 0 else ""
            lines.append(f" {sector} ATI {ati['index']:.0f} ({sv}{ati['pct']:.1f}%) — movers: {mv}")
        focus_txt = f" Focus specifically on {focus} sector." if focus != "Global" else ""
        prompt = f"""You are a Blackwater One macro analyst.{focus_txt}
Write a concise investor-grade report (200–240 words) from airport traffic index data.
ATI = total aviation activity vs 7-day baseline. 100 = baseline.
Cite specific index values, airports, and % changes. Explain cross-asset implications.
Do NOT name any flight tracking service. Tone: institutional, precise, high-conviction.
ATI DATA:
{chr(10).join(lines)}"""
        try:
            import config
            from openai import OpenAI
            with st.spinner("Synthesising ATI intelligence…"):
                resp = OpenAI(api_key=config.OPENAI_API_KEY).chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=420, temperature=0.38,
                )
            st.session_state.ati_insight = resp.choices[0].message.content.strip()
        except Exception as e:
            st.session_state.ati_insight = f"[Error: {e}]"

    if st.session_state.get("ati_insight"):
        st.markdown(
            f'<div class="insight-box">{st.session_state.ati_insight}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:36px"></div>', unsafe_allow_html=True)
