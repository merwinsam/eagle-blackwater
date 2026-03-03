import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import config


def fetch_daily_ohlcv(symbol: str, days: int = 252) -> pd.DataFrame:
    """yfinance first (best for Indian indexes), FMP as fallback."""
    # Strategy 1: yfinance
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(period="2y", auto_adjust=True)
        if not df.empty and len(df) >= 20:
            df.index = df.index.tz_localize(None)
            df = df.rename(columns={
                "Close": "adj_close", "Open": "open",
                "High": "high", "Low": "low", "Volume": "volume"
            })
            keep = [c for c in ["open","high","low","adj_close","volume"] if c in df.columns]
            return df[keep].dropna(subset=["adj_close"]).tail(days)
    except Exception:
        pass

    # Strategy 2: FMP stable endpoint
    end   = datetime.today()
    start = end - timedelta(days=days + 60)
    url = (
        f"https://financialmodelingprep.com/stable/historical-price-eod/full"
        f"?symbol={symbol}"
        f"&from={start.strftime('%Y-%m-%d')}"
        f"&to={end.strftime('%Y-%m-%d')}"
        f"&apikey={config.FMP_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        records = data if isinstance(data, list) else data.get("historical", [])
        if records:
            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
            df = df.rename(columns={"close": "adj_close"})
            keep = [c for c in ["open","high","low","adj_close","volume"] if c in df.columns]
            df = df[keep].dropna(subset=["adj_close"])
            if len(df) >= 20:
                return df.tail(days)
    except Exception:
        pass

    return pd.DataFrame()


def compute_returns(df: pd.DataFrame, price_col: str = "adj_close") -> pd.Series:
    return np.log(df[price_col] / df[price_col].shift(1)).dropna()


def compute_drawdown(prices: pd.Series) -> pd.Series:
    rolling_max = prices.cummax()
    return (prices - rolling_max) / rolling_max


@st.cache_data(ttl=config.AUTO_REFRESH_SECONDS)
def load_all_assets(days: int = 252) -> dict:
    """Load all assets. Cache auto-expires every AUTO_REFRESH_SECONDS (5 min)."""
    all_syms = config.FMP_ASSETS + config.CRYPTO_ASSETS + config.INDIA_ASSETS
    assets = {}
    for sym in all_syms:
        df = fetch_daily_ohlcv(sym, days)
        if not df.empty:
            df["returns"]  = compute_returns(df)
            df["drawdown"] = compute_drawdown(df["adj_close"])
            assets[sym] = df
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
            "high":       latest.get("high", latest["adj_close"]),
            "low":        latest.get("low",  latest["adj_close"]),
            "drawdown":   latest["drawdown"],
        }
    return summary
