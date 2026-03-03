import os
from dotenv import load_dotenv

load_dotenv()

def _get(key):
    """Read from Streamlit secrets (cloud) or .env (local)."""
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        return os.getenv(key, "")

# API Keys
FMP_API_KEY    = _get("FMP_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")

# ── Asset Universe ─────────────────────────────────────────────────────────────
# US Markets
FMP_ASSETS   = ["SPY", "QQQ", "GLD", "TLT"]
CRYPTO_ASSETS = ["BTCUSD"]

# Indian Markets — NSE indices & large caps via FMP
# FMP uses BSE/NSE suffix: e.g. RELIANCE.NS, ^NSEI, ^BSESN
INDIA_ASSETS = ["^NSEI", "^BSESN", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]

# Display labels for Indian assets
INDIA_LABELS = {
    "^NSEI":       "NIFTY 50",
    "^BSESN":      "SENSEX",
    "RELIANCE.NS": "Reliance",
    "TCS.NS":      "TCS",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS":     "Infosys",
}

# All assets grouped
ASSET_GROUPS = {
    "🇺🇸 US Markets":    FMP_ASSETS + CRYPTO_ASSETS,
    "🇮🇳 Indian Markets": INDIA_ASSETS,
}

# ── Lookback Windows ───────────────────────────────────────────────────────────
MOMENTUM_LOOKBACK = 20
VOL_LOOKBACK      = 20
CORR_LOOKBACK     = 60
ZSCORE_LOOKBACK   = 60

# ── Volatility Thresholds (annualized) ────────────────────────────────────────
VOL_LOW      = 0.10
VOL_NORMAL   = 0.18
VOL_ELEVATED = 0.28

# ── Momentum Z-Score Thresholds ───────────────────────────────────────────────
MOMENTUM_UP_THRESHOLD   =  1.0
MOMENTUM_DOWN_THRESHOLD = -1.0

# ── Correlation Thresholds ────────────────────────────────────────────────────
CORR_HIGH = 0.70
CORR_LOW  = 0.30

# ── Drawdown Thresholds ───────────────────────────────────────────────────────
DRAWDOWN_WARN  = -0.05
DRAWDOWN_ALERT = -0.10

# ── LLM ───────────────────────────────────────────────────────────────────────
OPENAI_MODEL = "gpt-4o-mini"
