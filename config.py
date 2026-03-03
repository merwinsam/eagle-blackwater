import os
from dotenv import load_dotenv
load_dotenv()

def _get(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.getenv(key, "")

FMP_API_KEY    = _get("FMP_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")

FMP_ASSETS    = ["SPY", "QQQ", "GLD", "TLT"]
CRYPTO_ASSETS = ["BTCUSD"]

INDIA_ASSETS = [
    "^NSEI",    # NIFTY 50
    "^BSESN",   # SENSEX
    "^NSEBANK", # NIFTY Bank
    "^CNXIT",   # NIFTY IT
    "^NSMIDCP", # NIFTY Midcap 50
]

INDIA_LABELS = {
    "^NSEI":    "NIFTY 50",
    "^BSESN":   "SENSEX",
    "^NSEBANK": "NIFTY Bank",
    "^CNXIT":   "NIFTY IT",
    "^NSMIDCP": "NIFTY Midcap",
}

ASSET_GROUPS = {
    "🇺🇸 US Markets":    FMP_ASSETS + CRYPTO_ASSETS,
    "🇮🇳 Indian Markets": INDIA_ASSETS,
}

MOMENTUM_LOOKBACK = 20
VOL_LOOKBACK      = 20
CORR_LOOKBACK     = 60
ZSCORE_LOOKBACK   = 60
VOL_LOW      = 0.10
VOL_NORMAL   = 0.18
VOL_ELEVATED = 0.28
MOMENTUM_UP_THRESHOLD   =  1.0
MOMENTUM_DOWN_THRESHOLD = -1.0
CORR_HIGH = 0.70
CORR_LOW  = 0.30
DRAWDOWN_WARN  = -0.05
DRAWDOWN_ALERT = -0.10
OPENAI_MODEL = "gpt-4o-mini"
AUTO_REFRESH_SECONDS = 300
