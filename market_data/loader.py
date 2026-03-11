"""
Data Layer: Fetch market data from Financial Modeling Prep + yfinance fallback.
Supports US equities, crypto, and Indian markets (NSE/BSE).

FIX: Three-source cascade (FMP v3 → FMP stable → yfinance) so data always loads.
     Silent failures now print to terminal so you can see what's going wrong.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import config


# ── Source 1: FMP v3 (best for US tickers — has adjClose) ────────────────────

def _fmp_v3(symbol: str, days: int) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=days + 60)
    url = (
        f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
        f"?from={start.strftime('%Y-%m-%d')}"
        f"&to={end.strftime('%Y-%m-%d')}"
        f"&apikey={config.FMP_API_KEY}"
    )
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    records = data.get("historical", [])
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    if "adjClose" in df.columns:
        df = df.rename(columns={"adjClose": "adj_close"})
    elif "close" in df.columns:
        df["adj_close"] = df["close"]
    keep = [c for c in ["open", "high", "low", "adj_close", "volume"] if c in df.columns]
    df = df[keep].dropna(subset=["adj_close"])
    return df.tail(days) if len(df) >= 20 else pd.DataFrame()


# ── Source 2: FMP stable endpoint ────────────────────────────────────────────

def _fmp_stable(symbol: str, days: int) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=days + 60)
    url = (
        f"https://financialmodelingprep.com/stable/historical-price-eod/full"
        f"?symbol={symbol}"
        f"&from={start.strftime('%Y-%m-%d')}"
        f"&to={end.strftime('%Y-%m-%d')}"
        f"&apikey={config.FMP_API_KEY}"
    )
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    records = data if isinstance(data, list) else data.get("historical", [])
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    if "close" in df.columns and "adj_close" not in df.columns:
        df["adj_close"] = df["close"]
    keep = [c for c in ["open", "high", "low", "adj_close", "volume"] if c in df.columns]
    df = df[keep].dropna(subset=["adj_close"])
    return df.tail(days) if len(df) >= 20 else pd.DataFrame()


# ── Source 3: yfinance (reliable for all symbols including Indian indexes) ────

def _yfinance(symbol: str, days: int) -> pd.DataFrame:
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="2y", auto_adjust=True)
    if df.empty:
        return pd.DataFrame()
    df.index = df.index.tz_localize(None)
    df = df.rename(columns={
        "Close": "adj_close", "Open": "open",
        "High": "high",       "Low": "low", "Volume": "volume"
    })
    keep = [c for c in ["open", "high", "low", "adj_close", "volume"] if c in df.columns]
    df = df[keep].dropna(subset=["adj_close"])
    return df.tail(days) if len(df) >= 20 else pd.DataFrame()


# ── Main fetch: cascade through all sources ───────────────────────────────────

def fetch_daily_ohlcv(symbol: str, days: int = 252) -> pd.DataFrame:
    """
    Try FMP v3 → FMP stable → yfinance.
    Logs failures to terminal but never raises — returns empty DataFrame on total failure.
    """
    errors = []

    try:
        df = _fmp_v3(symbol, days)
        if not df.empty:
            return df
        errors.append("fmp_v3: empty")
    except Exception as e:
        errors.append(f"fmp_v3: {type(e).__name__}: {e}")

    try:
        df = _fmp_stable(symbol, days)
        if not df.empty:
            return df
        errors.append("fmp_stable: empty")
    except Exception as e:
        errors.append(f"fmp_stable: {type(e).__name__}: {e}")

    try:
        df = _yfinance(symbol, days)
        if not df.empty:
            return df
        errors.append("yfinance: empty")
    except Exception as e:
        errors.append(f"yfinance: {type(e).__name__}: {e}")

    print(f"[loader] ✗ {symbol}: all sources failed — {' | '.join(errors)}")
    return pd.DataFrame()


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_returns(df: pd.DataFrame, price_col: str = "adj_close") -> pd.Series:
    return np.log(df[price_col] / df[price_col].shift(1)).dropna()


def compute_drawdown(prices: pd.Series) -> pd.Series:
    rolling_max = prices.cummax()
    return (prices - rolling_max) / rolling_max


# ── Cached bulk loader ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_assets(days: int = 252) -> dict:
    """
    Load all assets from config. Returns {symbol: DataFrame}.
    Failed symbols are skipped; successful ones always populate.
    """
    all_syms = list(dict.fromkeys(
        config.FMP_ASSETS + config.CRYPTO_ASSETS + config.INDIA_ASSETS
    ))
    assets = {}
    for sym in all_syms:
        df = fetch_daily_ohlcv(sym, days)
        if not df.empty:
            df = df.copy()
            df["returns"]  = compute_returns(df)
            df["drawdown"] = compute_drawdown(df["adj_close"])
            assets[sym] = df
    print(f"[loader] Loaded {len(assets)}/{len(all_syms)} assets: {list(assets.keys())}")
    return assets


def get_latest_price_summary(assets: dict) -> dict:
    summary = {}
    for sym, df in assets.items():
        if df.empty or len(df) < 2:
            continue
        latest = df.iloc[-1]
        prev   = df.iloc[-2]
        chg    = (latest["adj_close"] - prev["adj_close"]) / prev["adj_close"]
        summary[sym] = {
            "price":      latest["adj_close"],
            "change_pct": chg,
            "volume":     latest.get("volume", 0),
            "high":       latest.get("high",  latest["adj_close"]),
            "low":        latest.get("low",   latest["adj_close"]),
            "drawdown":   latest["drawdown"],
        }
    return summary
