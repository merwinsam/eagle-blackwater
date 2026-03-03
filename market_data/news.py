"""
News Layer: Fetch financial and macro news from FMP and structure it for LLM consumption.
"""

import requests
import streamlit as st
from datetime import datetime, timedelta
import config


def fetch_market_news(limit: int = 20) -> list[dict]:
    """Fetch general financial news from FMP."""
    url = (
        f"https://financialmodelingprep.com/stable/news/general-latest"
        f"?limit={limit}&apikey={config.FMP_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        # Fallback to older endpoint
        try:
            url2 = f"https://financialmodelingprep.com/api/v3/stock_news?limit={limit}&apikey={config.FMP_API_KEY}"
            resp2 = requests.get(url2, timeout=10)
            resp2.raise_for_status()
            data2 = resp2.json()
            return data2 if isinstance(data2, list) else []
        except:
            return []


def fetch_asset_news(symbol: str, limit: int = 8) -> list[dict]:
    """Fetch news for a specific ticker."""
    url = (
        f"https://financialmodelingprep.com/stable/news/stock"
        f"?symbols={symbol}&limit={limit}&apikey={config.FMP_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        # fallback
        url2 = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit={limit}&apikey={config.FMP_API_KEY}"
        resp2 = requests.get(url2, timeout=10)
        data2 = resp2.json()
        return data2 if isinstance(data2, list) else []
    except Exception as e:
        return []


def fetch_economic_calendar(days_ahead: int = 7) -> list[dict]:
    """Fetch upcoming economic events."""
    today = datetime.today()
    end   = today + timedelta(days=days_ahead)
    url = (
        f"https://financialmodelingprep.com/stable/economic-calendar"
        f"?from={today.strftime('%Y-%m-%d')}&to={end.strftime('%Y-%m-%d')}"
        f"&apikey={config.FMP_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except:
        return []


def format_news_for_llm(news_items: list[dict], max_items: int = 10) -> str:
    """Compress news into a structured string for LLM context."""
    if not news_items:
        return "No recent news available."
    lines = []
    for item in news_items[:max_items]:
        title = item.get("title", item.get("headline", ""))
        date  = str(item.get("publishedDate", item.get("date", "")))[:10]
        site  = item.get("site", item.get("source", ""))
        if title:
            lines.append(f"[{date}] ({site}) {title}")
    return "\n".join(lines)


def format_econ_calendar_for_llm(events: list[dict], max_items: int = 8) -> str:
    """Compress economic calendar into string for LLM context."""
    if not events:
        return "No upcoming economic events found."
    lines = []
    for ev in events[:max_items]:
        name   = ev.get("event", ev.get("name", ""))
        date   = str(ev.get("date", ""))[:10]
        impact = ev.get("impact", ev.get("importance", ""))
        actual = ev.get("actual", "")
        est    = ev.get("estimate", ev.get("consensus", ""))
        line   = f"[{date}] {name}"
        if impact: line += f" | impact:{impact}"
        if est:    line += f" | est:{est}"
        if actual: line += f" | actual:{actual}"
        lines.append(line)
    return "\n".join(lines)
