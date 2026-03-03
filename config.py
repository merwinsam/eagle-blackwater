import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Asset universe
DEFAULT_ASSETS = ["SPY", "QQQ", "GLD", "TLT", "BTC/USD"]
FMP_ASSETS = ["SPY", "QQQ", "GLD", "TLT"]   # stocks via FMP
CRYPTO_ASSETS = ["BTCUSD"]                   # crypto via FMP

# Lookback windows
MOMENTUM_LOOKBACK = 20
VOL_LOOKBACK = 20
CORR_LOOKBACK = 60
ZSCORE_LOOKBACK = 60

# Volatility thresholds (annualized)
VOL_LOW = 0.10
VOL_NORMAL = 0.18
VOL_ELEVATED = 0.28
# above ELEVATED → extreme

# Momentum z-score thresholds
MOMENTUM_UP_THRESHOLD = 1.0
MOMENTUM_DOWN_THRESHOLD = -1.0

# Correlation thresholds
CORR_HIGH = 0.70
CORR_LOW = 0.30

# Drawdown thresholds
DRAWDOWN_WARN = -0.05
DRAWDOWN_ALERT = -0.10

# LLM model
OPENAI_MODEL = "gpt-4o-mini"
