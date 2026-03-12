"""
Blackwater GEOINT — Geopolitical Intelligence Platform
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import time
import streamlit.components.v1

GEOINT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;600;700&display=swap');
.gi-bar{background:#000;border-bottom:2px solid #0d2a1a;padding:0 18px;height:44px;display:flex;align-items:center;gap:12px;}
.gi-logo{font-family:'Rajdhani',sans-serif;font-weight:700;font-size:1.05rem;color:#00ff88;letter-spacing:.14em;text-transform:uppercase;}
.gi-sep{width:1px;height:18px;background:#0d2a1a;}
.gi-sub{font-family:'Share Tech Mono',monospace;font-size:.56rem;color:#1a6a3a;letter-spacing:.18em;text-transform:uppercase;}
.gi-pill{font-family:'Share Tech Mono',monospace;font-size:.50rem;color:#00ff88;border:1px solid #0d3a1a;padding:2px 8px;border-radius:1px;background:rgba(0,255,136,.06);letter-spacing:.10em;}
.gi-ts{font-family:'Share Tech Mono',monospace;font-size:.58rem;color:#1a5a2a;margin-left:auto;display:flex;align-items:center;gap:6px;}
.gi-dot{width:5px;height:5px;border-radius:50%;background:#00ff88;animation:gi-pulse 2s ease-in-out infinite;}
@keyframes gi-pulse{0%,100%{opacity:1}50%{opacity:.25}}
.gi-hdr{font-family:'Share Tech Mono',monospace;font-size:.56rem;color:#00ff88;text-transform:uppercase;letter-spacing:.18em;padding:8px 0 5px;border-bottom:1px solid #0a2010;margin-bottom:7px;display:flex;align-items:center;gap:6px;}
.gi-hdr::before{content:'';display:inline-block;width:2px;height:9px;background:#00ff88;}
.gi-kpi{background:#020d05;border:1px solid #0a2010;border-top:2px solid #00ff88;padding:9px 12px;text-align:center;}
.gi-kpi.red{border-top-color:#ff4444;}.gi-kpi.amber{border-top-color:#ffaa00;}
.gi-kpi .lbl{font-family:'Share Tech Mono',monospace;font-size:.50rem;color:#1a6a3a;text-transform:uppercase;letter-spacing:.13em;margin-bottom:3px;}
.gi-kpi .val{font-family:'Rajdhani',sans-serif;font-size:1.55rem;font-weight:700;color:#00ff88;line-height:1;}
.gi-kpi.red .val{color:#ff4444;}.gi-kpi.amber .val{color:#ffaa00;}
.gi-kpi .sub{font-size:.56rem;color:#1a5a2a;margin-top:2px;font-family:'Share Tech Mono',monospace;}
.gi-card{background:#020d05;border:1px solid #0a2010;border-left:2px solid #0d3a1a;padding:7px 11px;margin-bottom:3px;font-family:'Share Tech Mono',monospace;font-size:.68rem;color:#4a9a6a;line-height:1.55;transition:border-left-color .12s;}
.gi-card:hover{border-left-color:#00ff88;}.gi-card.conflict{border-left-color:#ff4444;}.gi-card.disaster{border-left-color:#ffaa00;}.gi-card.news{border-left-color:#4488ff;}
.gi-card .meta{font-size:.52rem;color:#1a5a2a;margin-bottom:2px;}.gi-card .body{font-size:.70rem;color:#5aaa7a;}.gi-card .note{font-size:.60rem;color:#1a5a2a;margin-top:2px;}
.gi-tag{display:inline-block;font-family:'Share Tech Mono',monospace;font-size:.46rem;padding:1px 5px;border-radius:1px;text-transform:uppercase;letter-spacing:.07em;margin-left:4px;}
.gi-tag.conflict{background:rgba(255,68,68,.12);color:#ff4444;border:1px solid rgba(255,68,68,.25);}
.gi-tag.disaster{background:rgba(255,170,0,.12);color:#ffaa00;border:1px solid rgba(255,170,0,.25);}
.gi-tag.aircraft{background:rgba(0,255,136,.08);color:#00ff88;border:1px solid rgba(0,255,136,.18);}
.gi-tag.maritime{background:rgba(0,170,255,.10);color:#00aaff;border:1px solid rgba(0,170,255,.22);}
.gi-tag.news{background:rgba(68,136,255,.10);color:#4488ff;border:1px solid rgba(68,136,255,.22);}
.gi-statusbar{background:#000;border-top:1px solid #0a2010;padding:4px 14px;display:flex;gap:16px;font-family:'Share Tech Mono',monospace;font-size:.50rem;color:#0d3a1a;}
.gi-statusbar .ok{color:#00cc66;}.gi-statusbar .err{color:#ff4444;}
/* Globe fills viewport */
#globe-container { width:100%;height:90vh;position:relative; }
#globe-container iframe,
#globe-container > div { width:100% !important;height:100% !important; }
</style>
"""

@st.cache_data(ttl=300, show_spinner=False)
def gi_fetch_acled(days: int = 14) -> pd.DataFrame:
    try:
        key   = st.secrets.get("ACLED_KEY", "")
        email = st.secrets.get("ACLED_EMAIL", "")
        end   = datetime.utcnow()
        start = end - timedelta(days=days)
        if key and email:
            url = (
                f"https://api.acleddata.com/acled/read"
                f"?key={key}&email={email}"
                f"&event_date={start.strftime('%Y-%m-%d')}|{end.strftime('%Y-%m-%d')}"
                "&event_date_where=BETWEEN&limit=300&format=json"
                "&fields=event_date|event_type|country|latitude|longitude|fatalities|notes|actor1"
            )
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                rows = r.json().get("data", [])
                if rows:
                    df = pd.DataFrame(rows)
                    for c in ["latitude","longitude","fatalities"]:
                        df[c] = pd.to_numeric(df.get(c, pd.Series()), errors="coerce")
                    df["fatalities"] = df["fatalities"].fillna(0)
                    return df.dropna(subset=["latitude","longitude"])
        # CSV fallback
        url2 = (
            f"https://api.acleddata.com/acled/read.csv"
            f"?event_date={start.strftime('%Y-%m-%d')}|{end.strftime('%Y-%m-%d')}"
            "&event_date_where=BETWEEN&limit=200"
            "&fields=event_date|event_type|country|latitude|longitude|fatalities|notes|actor1"
        )
        r2 = requests.get(url2, timeout=15)
        if r2.status_code == 200 and len(r2.content) > 500:
            from io import StringIO
            df = pd.read_csv(StringIO(r2.text))
            for c in ["latitude","longitude","fatalities"]:
                df[c] = pd.to_numeric(df.get(c, pd.Series()), errors="coerce")
            df["fatalities"] = df["fatalities"].fillna(0)
            return df.dropna(subset=["latitude","longitude"])
    except Exception as e:
        print(f"[geoint] ACLED direct: {e}")

    # GDELT fallback — derive conflict locations from known hotspot keywords
    try:
        q = "armed+conflict+OR+airstrike+OR+shelling+OR+militia+OR+insurgent+OR+bombing"
        r = requests.get(
            f"https://api.gdeltproject.org/api/v2/doc/doc?query={q}"
            "&mode=artlist&maxrecords=80&format=json&timespan=336h&sort=datedesc",
            timeout=12)
        if r.status_code == 200:
            coords = {
                "ukraine":(49.0,32.0),"russia":(55.0,37.0),"gaza":(31.4,34.4),
                "israel":(31.7,35.2),"sudan":(15.6,32.5),"myanmar":(19.7,96.1),
                "somalia":(2.0,45.3),"mali":(17.6,-3.9),"syria":(34.8,38.9),
                "iraq":(33.3,44.4),"yemen":(15.6,48.5),"ethiopia":(9.1,40.5),
                "nigeria":(10.5,7.4),"drc":(-4.0,21.8),"afghanistan":(33.9,67.7),
                "pakistan":(30.4,69.3),"haiti":(18.9,-72.3),"colombia":(4.7,-74.1),
                "mozambique":(-18.7,35.5),"sahel":(14.0,0.0),"lebanon":(33.9,35.5),
                "libya":(26.3,17.2),"chad":(15.5,18.7),"burkina":(12.4,-1.6),
            }
            rows = []
            import hashlib
            for a in (r.json().get("articles") or [])[:80]:
                tl = (a.get("title","") or "").lower()
                lat, lon = None, None
                for kw,(la,lo) in coords.items():
                    if kw in tl:
                        h = int(hashlib.md5((a.get("url","")+"_lat").encode()).hexdigest(),16)
                        lat = la + (h % 100)/400 - 0.125
                        h2 = int(hashlib.md5((a.get("url","")+"_lon").encode()).hexdigest(),16)
                        lon = lo + (h2 % 100)/400 - 0.125
                        break
                if lat is None:
                    continue
                rows.append({
                    "event_date": (a.get("seendate","") or "")[:10],
                    "event_type": "Conflict Signal",
                    "country":    a.get("sourcecountry",""),
                    "latitude":   lat, "longitude": lon,
                    "fatalities": 0,
                    "actor1":     a.get("domain",""),
                    "notes":      (a.get("title","") or "")[:120],
                })
            if rows:
                return pd.DataFrame(rows)
    except Exception as e:
        print(f"[geoint] ACLED/GDELT fallback: {e}")
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def gi_fetch_aircraft() -> pd.DataFrame:
    """FR24 API — live aircraft in sensitive airspace (same key as ATI)."""
    regions = [
        ("Middle East",      20,42,25,63),
        ("Eastern Europe",   44,58,22,45),
        ("South China Sea",   5,25,105,125),
        ("Korean Peninsula", 34,42,124,132),
        ("Taiwan Strait",    20,30,118,125),
        ("Red Sea / Horn",    8,30,30,50),
    ]
    try:
        token = st.secrets["FR24_API_KEY"]
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Accept-Version": "v1"}
    except Exception:
        return pd.DataFrame()
    rows = []
    for name, la0, la1, lo0, lo1 in regions:
        try:
            r = requests.get(
                "https://fr24api.flightradar24.com/api/live/flight-positions/light",
                params={"bounds": f"{la1},{la0},{lo0},{lo1}"},
                headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                flights = data.get("data", data) if isinstance(data, dict) else data
                for f in (flights or [])[:30]:
                    lat = f.get("lat") or f.get("latitude")
                    lon = f.get("lon") or f.get("longitude")
                    if not lat or not lon:
                        continue
                    rows.append({
                        "icao":     f.get("icao24","") or f.get("hex",""),
                        "callsign": (f.get("callsign","") or f.get("flight","") or "").strip(),
                        "country":  f.get("orig_iata","") or f.get("country",""),
                        "longitude":float(lon), "latitude": float(lat),
                        "altitude": float(f.get("alt",0) or f.get("altitude",0) or 0),
                        "velocity": float(f.get("gspeed",0) or f.get("speed",0) or 0),
                        "heading":  float(f.get("track",0) or f.get("heading",0) or 0),
                        "region":   name,
                    })
            time.sleep(0.3)
        except Exception as e:
            print(f"[geoint] FR24 {name}: {e}")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def gi_fetch_gdacs() -> pd.DataFrame:
    try:
        r = requests.get("https://www.gdacs.org/xml/rss.xml", timeout=12)
        if r.status_code != 200:
            return pd.DataFrame()
        root = ET.fromstring(r.content)
        rows = []
        GD="http://www.gdacs.org"; GEO="http://www.w3.org/2003/01/geo/wgs84_pos#"
        for item in root.findall(".//item"):
            def g(tag,ns=""):
                el=item.find(f"{{{ns}}}{tag}" if ns else tag)
                return (el.text or "").strip() if el is not None else ""
            title=g("title"); pub=g("pubDate")[:16]
            etype=g("eventtype",GD); alert=g("alertlevel",GD).upper()
            lat_s=g("lat",GEO); lon_s=g("long",GEO)
            if not lat_s:
                bb=item.find(f"{{{GD}}}bbox")
                if bb is not None and bb.text:
                    p=bb.text.split()
                    if len(p)>=4:
                        lat_s=str((float(p[1])+float(p[3]))/2)
                        lon_s=str((float(p[0])+float(p[2]))/2)
            try:
                rows.append({"title":title,"date":pub,"type":etype,"alert":alert,
                             "latitude":float(lat_s),"longitude":float(lon_s)})
            except:
                pass
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        print(f"[geoint] GDACS: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=180, show_spinner=False)
def gi_fetch_gdelt(n:int=50) -> pd.DataFrame:
    """FMP general news — geopolitical/market headlines."""
    try:
        import config
        url = f"https://financialmodelingprep.com/stable/news/general-latest?apikey={config.FMP_API_KEY}&limit=80"
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            rows = []
            keywords = {"war","conflict","sanction","military","missile","nuclear","attack",
                        "invasion","ceasefire","troops","nato","geopolit","coup","unrest",
                        "tariff","embargo","blockade","crisis","tension"}
            for a in r.json()[:120]:
                title = (a.get("title","") or "").lower()
                if not any(kw in title for kw in keywords):
                    continue
                rows.append({
                    "title":  a.get("title",""),
                    "url":    a.get("url","#"),
                    "source": a.get("site","") or a.get("symbol",""),
                    "date":   (a.get("publishedDate","") or "")[:10],
                    "country":"",
                    "tone":   0.0,
                })
                if len(rows) >= n:
                    break
            if rows:
                return pd.DataFrame(rows)
    except Exception as e:
        print(f"[geoint] FMP news: {e}")
    # GDELT fallback
    try:
        url2 = ("https://api.gdeltproject.org/api/v2/doc/doc"
                "?query=conflict+war+sanctions+military+naval"
                "&mode=artlist&maxrecords=50&format=json&timespan=24h&sort=datedesc")
        r2 = requests.get(url2, timeout=10)
        if r2.status_code == 200:
            rows = []
            for a in (r2.json().get("articles") or [])[:n]:
                rows.append({"title":a.get("title",""),"url":a.get("url","#"),
                             "source":a.get("domain",""),"date":(a.get("seendate","") or "")[:10],
                             "country":a.get("sourcecountry",""),"tone":float(a.get("tone",0))})
            return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        print(f"[geoint] GDELT fallback: {e}")
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def gi_fetch_worldbank() -> pd.DataFrame:
    inds={"NY.GDP.MKTP.KD.ZG":"GDP Growth %","FP.CPI.TOTL.ZG":"Inflation %","MS.MIL.XPND.GD.ZS":"Military % GDP"}
    ctry=["US","CN","RU","IN","DE","JP","GB","SA","BR","TR"]
    rows=[]
    for code,label in inds.items():
        try:
            url=f"https://api.worldbank.org/v2/country/{';'.join(ctry)}/indicator/{code}?format=json&mrv=1&per_page=20"
            r=requests.get(url,timeout=10)
            if r.status_code==200:
                for e in (r.json()[1] or []):
                    if e.get("value") is not None:
                        rows.append({"country":e["country"]["value"],"indicator":label,"value":round(float(e["value"]),2)})
        except Exception as e:
            print(f"[geoint] WB {code}: {e}")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=180, show_spinner=False)
def gi_fetch_maritime() -> pd.DataFrame:
    coords={"red sea":(15.0,42.5),"bab el-mandeb":(12.5,43.3),"strait of hormuz":(26.5,56.5),
            "persian gulf":(26.0,52.0),"south china sea":(12.0,114.0),"taiwan strait":(24.5,120.5),
            "black sea":(43.0,33.0),"baltic":(58.0,20.0),"gulf of guinea":(3.0,3.5),
            "somali":(5.0,46.0),"mediterranean":(36.0,18.0),"strait of malacca":(2.5,102.0)}
    try:
        q="ship OR vessel OR tanker OR maritime OR piracy OR strait OR navy"
        url=(f"https://api.gdeltproject.org/api/v2/doc/doc?query={requests.utils.quote(q)}"
             "&mode=artlist&maxrecords=40&format=json&timespan=72h&sort=datedesc")
        r=requests.get(url,timeout=12)
        if r.status_code!=200: return pd.DataFrame()
        rows=[]
        for a in (r.json().get("articles") or []):
            tl=(a.get("title","") or "").lower()
            lat,lon=None,None
            for kw,(la,lo) in coords.items():
                if kw in tl: lat,lon=la,lo; break
            if lat is None: continue
            rows.append({"title":a.get("title",""),"url":a.get("url","#"),
                         "source":a.get("domain",""),"date":(a.get("seendate","") or "")[:10],
                         "latitude":lat,"longitude":lon})
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        print(f"[geoint] Maritime: {e}")
        return pd.DataFrame()


def build_globe(layers, acled, aircraft, gdacs, maritime):
    fig = go.Figure()

    if layers.get("conflict") and not acled.empty:
        fatal=(acled.get("fatalities",pd.Series([0]*len(acled))).fillna(0))
        sizes=(fatal.clip(0,300)/300*20+7).tolist()
        hover=[f"<b>⚔ {r.get('event_type','Conflict')}</b><br>{r.get('country','—')} · {r.get('event_date','')}<br>Actor: {str(r.get('actor1','—'))[:50]}<br>Fatalities: {int(r.get('fatalities',0))}<br><i>{str(r.get('notes',''))[:100]}</i>" for _,r in acled.iterrows()]
        fig.add_trace(go.Scattergeo(lat=acled.latitude,lon=acled.longitude,mode="markers",
            marker=dict(size=[s+18 for s in sizes],color="rgba(255,40,40,0.04)",line=dict(width=0)),
            hoverinfo="skip",showlegend=False))
        fig.add_trace(go.Scattergeo(lat=acled.latitude,lon=acled.longitude,mode="markers",
            marker=dict(size=[s+7 for s in sizes],color="rgba(255,70,70,0.13)",line=dict(width=0)),
            hoverinfo="skip",showlegend=False))
        fig.add_trace(go.Scattergeo(lat=acled.latitude,lon=acled.longitude,mode="markers",
            marker=dict(size=sizes,color="#ff3333",opacity=0.88,line=dict(width=0.5,color="rgba(255,100,100,0.4)")),
            text=hover,hoverinfo="text",
            hoverlabel=dict(bgcolor="#050505",bordercolor="#330808",font=dict(color="#ff8888",size=10,family="Share Tech Mono")),
            name="⚔ Conflict (ACLED)"))

    if layers.get("disasters") and not gdacs.empty:
        ac=gdacs.get("alert",pd.Series(["ORANGE"]*len(gdacs)))
        cols=[{"RED":"#ff2200","ORANGE":"#ff8800","GREEN":"#00cc44"}.get(a,"#ffaa00") for a in ac]
        hover=[f"<b>⚠ {r.get('type','Disaster')}</b> [{r.get('alert','')}]<br>{r.get('title','')}<br>{r.get('date','')}" for _,r in gdacs.iterrows()]
        fig.add_trace(go.Scattergeo(lat=gdacs.latitude,lon=gdacs.longitude,mode="markers",
            marker=dict(size=15,color=cols,opacity=0.9,symbol="diamond",line=dict(width=1.5,color="rgba(255,170,0,0.5)")),
            text=hover,hoverinfo="text",
            hoverlabel=dict(bgcolor="#050505",bordercolor="#332200",font=dict(color="#ffaa00",size=10,family="Share Tech Mono")),
            name="⚠ Disasters (GDACS)"))

    if layers.get("aircraft") and not aircraft.empty:
        hover=[f"<b>✈ {r.get('callsign','—') or '—'}</b><br>ICAO: {r.get('icao','—')} · {r.get('country','—')}<br>Zone: {r.get('region','—')}<br>Alt: {r.get('altitude',0):.0f}m" for _,r in aircraft.iterrows()]
        fig.add_trace(go.Scattergeo(lat=aircraft.latitude,lon=aircraft.longitude,mode="markers",
            marker=dict(size=7,color="#00ffaa",opacity=0.75,symbol="triangle-up",line=dict(width=1,color="rgba(0,255,150,0.4)")),
            text=hover,hoverinfo="text",
            hoverlabel=dict(bgcolor="#050505",bordercolor="#003322",font=dict(color="#00ffaa",size=10,family="Share Tech Mono")),
            name="✈ Aircraft (FR24)"))

    if layers.get("maritime") and not maritime.empty:
        hover=[f"<b>⚓ Maritime Signal</b><br>{r.get('title','')[:70]}…<br>{r.get('source','—')} · {r.get('date','')}" for _,r in maritime.iterrows()]
        fig.add_trace(go.Scattergeo(lat=maritime.latitude,lon=maritime.longitude,mode="markers",
            marker=dict(size=13,color="#00aaff",opacity=0.85,symbol="square",line=dict(width=1.5,color="rgba(0,150,255,0.4)")),
            text=hover,hoverinfo="text",
            hoverlabel=dict(bgcolor="#050505",bordercolor="#001833",font=dict(color="#00aaff",size=10,family="Share Tech Mono")),
            name="⚓ Maritime (GDELT)"))

    if layers.get("hotspots"):
        hotspots=[
            (26.5,56.5,"Strait of Hormuz","Energy chokepoint · High naval activity"),
            (12.8,43.3,"Bab el-Mandeb","Houthi threat zone · Red Sea disruption"),
            (24.0,121.0,"Taiwan Strait","PLA exercises · ADIZ violations"),
            (49.5,35.0,"Ukraine Front","Active conflict · NATO monitoring"),
            (36.5,37.5,"Syria / N.Iraq","Multi-actor conflict zone"),
            (34.0,129.5,"Korean Peninsula","DPRK missile activity"),
            (2.0,32.0,"DRC / East Africa","ACLED high-activity region"),
            (12.0,14.5,"Lake Chad Basin","Sahel instability corridor"),
            (2.5,102.0,"Strait of Malacca","Maritime chokepoint · Piracy risk"),
        ]
        for lat,lon,name,desc in hotspots:
            for sz,op in [(60,.025),(40,.06),(22,.14),(9,.40)]:
                fig.add_trace(go.Scattergeo(lat=[lat],lon=[lon],mode="markers",
                    marker=dict(size=sz,color="rgba(0,0,0,0)",line=dict(width=1,color=f"rgba(255,200,0,{op})")),
                    hoverinfo="skip",showlegend=False))
            fig.add_trace(go.Scattergeo(lat=[lat],lon=[lon],mode="markers+text",
                marker=dict(size=5,color="#ffcc00",opacity=1.0,line=dict(width=2,color="#ff8800")),
                text=[f"  {name}"],textfont=dict(size=8,color="#ffdd44",family="Share Tech Mono"),
                textposition="middle right",
                hovertext=[f"<b>🔴 {name}</b><br><span style='color:#aaa'>{desc}</span>"],
                hoverinfo="text",
                hoverlabel=dict(bgcolor="#050505",bordercolor="#332200",font=dict(color="#ffcc00",size=10,family="Share Tech Mono")),
                showlegend=False))

    fig.update_geos(
        projection_type="orthographic",
        showland=True,      landcolor="#0b1e0d",
        showocean=True,     oceancolor="#040c10",
        showcoastlines=True,coastlinecolor="#1e5525",coastlinewidth=0.9,
        showcountries=True, countrycolor="#122a16",  countrywidth=0.4,
        showlakes=True,     lakecolor="#040c10",
        showframe=False,    bgcolor="#000000",
        showrivers=False,
        lataxis=dict(showgrid=True,gridcolor="rgba(0,90,30,0.20)",gridwidth=0.4),
        lonaxis=dict(showgrid=True,gridcolor="rgba(0,90,30,0.20)",gridwidth=0.4),
        center=dict(lat=30,lon=30),
        projection_rotation=dict(lon=30,lat=20,roll=0),
    )
    fig.update_layout(
        paper_bgcolor="#000000",plot_bgcolor="#000000",
        margin=dict(l=0,r=0,t=0,b=0),height=820,
        legend=dict(orientation="h",x=0.01,y=0.02,
            bgcolor="rgba(0,0,0,0.90)",bordercolor="#0d2a10",borderwidth=1,
            font=dict(size=9,color="#2a8a4a",family="Share Tech Mono")),
        font=dict(family="Share Tech Mono",color="#1a5a2a"),
    )
    return fig


def build_econ_chart(wb, indicator):
    df=wb[wb["indicator"]==indicator].sort_values("value")
    if df.empty: return go.Figure()
    colors=["#ff4444" if v<0 else "#ffaa00" if v<2 else "#00ff88" for v in df["value"]]
    fig=go.Figure(go.Bar(x=df["value"],y=df["country"],orientation="h",
        marker=dict(color=colors,opacity=0.80),
        text=[f"{v:+.1f}%" for v in df["value"]],textposition="outside",
        textfont=dict(size=8,color="#1a7a3a",family="Share Tech Mono")))
    fig.update_layout(paper_bgcolor="#010402",plot_bgcolor="#010402",
        font=dict(family="Share Tech Mono",color="#1a5a2a",size=8),
        xaxis=dict(gridcolor="#0a1a08",zerolinecolor="#0d2a10",tickfont=dict(size=7)),
        yaxis=dict(gridcolor="#0a1a08"),
        margin=dict(l=0,r=55,t=22,b=5),height=200,
        title=dict(text=indicator,font=dict(size=9,color="#00cc66"),x=0))
    return fig


def render_geoint():
    st.markdown(GEOINT_CSS, unsafe_allow_html=True)
    ts=datetime.utcnow().strftime("%Y-%m-%d  %H:%M UTC")
    st.markdown(f"""
    <div class="gi-bar">
      <span class="gi-logo">Blackwater One</span><div class="gi-sep"></div>
      <span class="gi-sub">Geopolitical Intelligence</span><div class="gi-sep"></div>
      <span class="gi-pill">OSINT · LIVE</span>
      <span class="gi-ts"><span class="gi-dot"></span>{ts}</span>
    </div>
    <div style="height:10px"></div>""", unsafe_allow_html=True)

    # Compact nav — back and refresh right next to each other
    n1,n2,n3,_ = st.columns([0.45,0.35,3.5,6])
    with n1:
        if st.button("← Back", key="gi_back", use_container_width=True):
            st.session_state.page="eagle"; st.rerun()
    with n2:
        if st.button("⟳", key="gi_ref", use_container_width=True, help="Refresh all feeds"):
            for fn in [gi_fetch_acled,gi_fetch_aircraft,gi_fetch_gdacs,gi_fetch_gdelt,gi_fetch_worldbank,gi_fetch_maritime]:
                fn.clear()
            st.session_state.gi_loaded=False; st.rerun()
    with n3:
        st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.58rem;color:#1a5a2a;padding:6px 0;letter-spacing:.1em">🛰 BLACKWATER GEOINT — GLOBAL INTELLIGENCE FEED</div>',unsafe_allow_html=True)

    st.markdown('<div class="gi-hdr">Intelligence Layers</div>', unsafe_allow_html=True)
    lc=st.columns(6)
    layer_defs=[("conflict","⚔ Conflict"),("disasters","⚠ Disasters"),("aircraft","✈ Aircraft"),
                ("maritime","⚓ Maritime"),("hotspots","🔴 Hotspots"),("econ","📊 Economics")]
    layers={}
    for col,(key,label) in zip(lc,layer_defs):
        with col:
            layers[key]=st.toggle(label,value=st.session_state.get(f"gi_l_{key}",key in ("conflict","disasters","hotspots")),key=f"gi_l_{key}")

    if not st.session_state.get("gi_loaded"):
        prog=st.progress(0)
        prog.progress(5,"Fetching conflict events (ACLED)…"); acled=gi_fetch_acled(14)
        prog.progress(22,"Tracking aircraft (FR24)…");    aircraft=gi_fetch_aircraft()
        prog.progress(40,"Loading disaster alerts (GDACS)…"); gdacs=gi_fetch_gdacs()
        prog.progress(55,"Scanning news (GDELT)…");          gdelt=gi_fetch_gdelt()
        prog.progress(70,"Maritime incident signals…");       maritime=gi_fetch_maritime()
        prog.progress(85,"Economic indicators (World Bank)…");wb=gi_fetch_worldbank()
        prog.progress(100,"Intelligence feeds online."); prog.empty()
        st.session_state.update({"gi_acled":acled,"gi_aircraft":aircraft,"gi_gdacs":gdacs,
            "gi_gdelt":gdelt,"gi_maritime":maritime,"gi_wb":wb,"gi_loaded":True,"gi_ts":time.time()})

    acled    = st.session_state.get("gi_acled",    pd.DataFrame())
    aircraft  = st.session_state.get("gi_aircraft",  pd.DataFrame())
    gdacs    = st.session_state.get("gi_gdacs",    pd.DataFrame())
    gdelt    = st.session_state.get("gi_gdelt",    pd.DataFrame())
    maritime = st.session_state.get("gi_maritime", pd.DataFrame())
    wb       = st.session_state.get("gi_wb",       pd.DataFrame())

    kk=st.columns(6)
    n_fatal=int(acled["fatalities"].sum()) if not acled.empty and "fatalities" in acled else 0
    n_red=int((gdacs["alert"]=="RED").sum()) if not gdacs.empty and "alert" in gdacs else 0
    for col,cls,lbl,val,sub in [
        (kk[0],"red","Conflict Events",str(len(acled)),"Last 14 days · ACLED"),
        (kk[1],"red","Fatalities",f"{n_fatal:,}","Reported deaths"),
        (kk[2],"amber","Disaster Alerts",str(len(gdacs)),f"{n_red} RED · GDACS"),
        (kk[3],"","Aircraft Tracked",str(len(aircraft)),"Sensitive airspace"),
        (kk[4],"","Maritime Signals",str(len(maritime)),"72h · GDELT"),
        (kk[5],"","GDELT Events",str(len(gdelt)),"24h news feed"),
    ]:
        with col:
            st.markdown(f'<div class="gi-kpi {cls}"><div class="lbl">{lbl}</div><div class="val">{val}</div><div class="sub">{sub}</div></div>',unsafe_allow_html=True)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    globe_col,feed_col = st.columns([2.6,1.0],gap="medium")

    with globe_col:
        gh1, gh2 = st.columns([8,1])
        with gh1:
            st.markdown('<div class="gi-hdr">Global Intelligence Globe — Drag to rotate · Scroll to zoom</div>',unsafe_allow_html=True)
        with gh2:
            if st.button("⤢ Expand", key="globe_expand", use_container_width=True, help="Full screen globe"):
                st.session_state.page = "globe_fullscreen"
                st.rerun()
        fig=build_globe(layers,acled,aircraft,gdacs,maritime)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":True,"modeBarButtonsToRemove":["toImage","select2d","lasso2d"],"displaylogo":False,"scrollZoom":True})


        if layers.get("econ") and not wb.empty:
            st.markdown('<div class="gi-hdr" style="margin-top:6px">Global Economic Indicators · World Bank</div>',unsafe_allow_html=True)
            ec1,ec2,ec3=st.columns(3)
            for col,ind in zip([ec1,ec2,ec3],["GDP Growth %","Inflation %","Military % GDP"]):
                with col:
                    ch=build_econ_chart(wb,ind)
                    if ch.data: st.plotly_chart(ch,use_container_width=True,config={"displayModeBar":False})

        st.markdown('<div class="gi-hdr" style="margin-top:6px">GDELT Global News Feed · 24h</div>',unsafe_allow_html=True)
        if not gdelt.empty:
            for _,row in gdelt.head(15).iterrows():
                tone=row.get("tone",0)
                tc="#ff4444" if tone<-5 else "#ffaa00" if tone<0 else "#00cc66"
                st.markdown(f"""
                <div class="gi-card news">
                  <div class="meta">{row.get('date','')} · {row.get('source','')} <span style="color:{tc};margin-left:8px">tone {tone:+.1f}</span></div>
                  <div class="body"><a href="{row.get('url','#')}" target="_blank" style="color:#4488ff;text-decoration:none">{row.get('title','')}</a></div>
                </div>""",unsafe_allow_html=True)
        else:
            st.caption("GDELT unavailable.")

    with feed_col:
        st.markdown('<div class="gi-hdr">Conflict Events · ACLED</div>',unsafe_allow_html=True)
        if not acled.empty:
            for _,row in acled.head(14).iterrows():
                fat=int(row.get("fatalities",0))
                fs=f"<span style='color:#ff4444'> · {fat} killed</span>" if fat else ""
                note=str(row.get("notes",""))
                st.markdown(f"""
                <div class="gi-card conflict">
                  <div class="meta">{row.get('event_date','')} · {row.get('country','')} <span class="gi-tag conflict">{row.get('event_type','')}</span></div>
                  <div class="body">{str(row.get('actor1',''))[:45]}{fs}</div>
                  <div class="note">{note[:85]}{'…' if len(note)>85 else ''}</div>
                </div>""",unsafe_allow_html=True)
        else:
            st.markdown('<div class="gi-card">Loading conflict data…</div>',unsafe_allow_html=True)

        st.markdown('<div class="gi-hdr" style="margin-top:10px">Disaster Alerts · GDACS</div>',unsafe_allow_html=True)
        if not gdacs.empty:
            for _,row in gdacs.head(8).iterrows():
                alert=row.get("alert","")
                ac={"RED":"#ff2200","ORANGE":"#ff8800","GREEN":"#00cc44"}.get(alert,"#ffaa00")
                st.markdown(f"""
                <div class="gi-card disaster">
                  <div class="meta">{row.get('type','')} <span style="color:{ac};margin-left:6px">● {alert}</span></div>
                  <div class="body">{row.get('title','')[:80]}</div>
                  <div class="note">{row.get('date','')}</div>
                </div>""",unsafe_allow_html=True)
        else:
            st.markdown('<div class="gi-card">GDACS unavailable.</div>',unsafe_allow_html=True)

        st.markdown('<div class="gi-hdr" style="margin-top:10px">Aircraft · Sensitive Zones</div>',unsafe_allow_html=True)
        if not aircraft.empty:
            by_region=aircraft.groupby("region").size().reset_index(name="n")
            for _,row in by_region.iterrows():
                st.markdown(f'<div class="gi-card"><span class="gi-tag aircraft">AIRCRAFT</span><b style="color:#00ffaa;margin-left:5px">{row["region"]}</b><span style="color:#1a5a2a;font-size:.62rem;margin-left:6px">{row["n"]} tracked</span></div>',unsafe_allow_html=True)
            for _,row in aircraft.head(10).iterrows():
                cs=(row.get("callsign","") or "—")
                st.markdown(f'<div style="padding:2px 10px;font-family:\'Share Tech Mono\',monospace;font-size:.58rem;color:#1a5a2a;border-bottom:1px solid #080f08">✈ {cs:<8} {row.get("region",""):18} {row.get("altitude",0):.0f}m</div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="gi-card">FR24 unavailable.</div>',unsafe_allow_html=True)

        if not maritime.empty:
            st.markdown('<div class="gi-hdr" style="margin-top:10px">Maritime Signals</div>',unsafe_allow_html=True)
            for _,row in maritime.head(6).iterrows():
                st.markdown(f'<div class="gi-card"><span class="gi-tag maritime">MARITIME</span><div class="body" style="margin-top:4px">{row.get("title","")[:75]}…</div><div class="note">{row.get("source","")} · {row.get("date","")}</div></div>',unsafe_allow_html=True)

    age=int(time.time()-st.session_state.get("gi_ts",time.time()))
    age_s=f"{age//60}m {age%60}s ago" if age>60 else f"{age}s ago"
    sources=[("ACLED",not acled.empty),("FR24",not aircraft.empty),("GDACS",not gdacs.empty),
             ("GDELT",not gdelt.empty),("Maritime",not maritime.empty),("World Bank",not wb.empty)]
    sb=" · ".join(f'<span class="{"ok" if ok else "err"}">{n} {"●" if ok else "✗"}</span>' for n,ok in sources)
    st.markdown(f'<div class="gi-statusbar">{sb}<span style="margin-left:auto">Last fetch: {age_s}</span></div>',unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FULLSCREEN GLOBE
# ─────────────────────────────────────────────────────────────────────────────

def render_globe_fullscreen():
    """Full-bleed globe — no columns, no sidebar, edge to edge."""
    st.markdown("""
    <style>
    /* Hide all Streamlit chrome */
    #MainMenu, header, footer, [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }
    /* Kill all padding */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
    }
    section[data-testid="stMain"] > div { padding: 0 !important; }
    /* Globe bar */
    .gb-bar {
        position: fixed; top: 0; left: 0; right: 0; z-index: 999;
        background: rgba(0,0,0,0.82);
        border-bottom: 1px solid #0d2a1a;
        padding: 0 16px; height: 38px;
        display: flex; align-items: center; gap: 10px;
        font-family: 'Share Tech Mono', monospace;
    }
    .gb-title { font-size: .58rem; color: #00ff88; letter-spacing: .18em; text-transform: uppercase; }
    .gb-dot   { width:5px;height:5px;border-radius:50%;background:#00ff88;
                animation:gi-pulse 2s ease-in-out infinite; }
    @keyframes gi-pulse{0%,100%{opacity:1}50%{opacity:.25}}
    /* Chart fills everything below bar */
    [data-testid="stPlotlyChart"] {
        position: fixed !important;
        top: 38px !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
        width: 100vw !important;
        height: calc(100vh - 38px) !important;
    }
    [data-testid="stPlotlyChart"] > div,
    [data-testid="stPlotlyChart"] .js-plotly-plot,
    [data-testid="stPlotlyChart"] .plot-container.plotly {
        width:  100% !important;
        height: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    ts = datetime.utcnow().strftime("%H:%M UTC")
    st.markdown(f"""
    <div class="gb-bar">
      <span class="gb-dot"></span>
      <span class="gb-title">Blackwater GEOINT — Global Intelligence Globe</span>
      <span style="margin-left:auto;font-size:.54rem;color:#1a5a2a">{ts}</span>
    </div>""", unsafe_allow_html=True)

    # Back button — floated top-right via CSS
    st.markdown("""
    <style>
    div[data-testid="stButton"]:first-of-type button {
        position: fixed !important; top: 6px !important; right: 16px !important;
        z-index: 1000 !important;
        background: rgba(0,0,0,0.7) !important;
        border: 1px solid #0d2a1a !important;
        color: #00ff88 !important;
        font-family: 'Share Tech Mono',monospace !important;
        font-size: .58rem !important;
        padding: 3px 10px !important;
    }
    </style>""", unsafe_allow_html=True)

    if st.button("✕ Close", key="globe_close"):
        st.session_state.page = "geoint"
        st.rerun()

    # Reuse cached data — no new fetches
    acled    = st.session_state.get("gi_acled",    pd.DataFrame())
    aircraft = st.session_state.get("gi_aircraft", pd.DataFrame())
    gdacs    = st.session_state.get("gi_gdacs",    pd.DataFrame())
    maritime = st.session_state.get("gi_maritime", pd.DataFrame())

    # Active layers from session
    layers = {k: st.session_state.get(f"gi_l_{k}", k in ("conflict","disasters","hotspots"))
              for k in ("conflict","disasters","aircraft","maritime","hotspots","econ")}

    fig = build_globe(layers, acled, aircraft, gdacs, maritime)

    # Override to fill screen
    fig.update_layout(
        height=None,
        autosize=True,
        margin=dict(l=0, r=0, t=0, b=0),
    )

    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["toImage","select2d","lasso2d"],
        "displaylogo": False,
        "scrollZoom": True,
    })
