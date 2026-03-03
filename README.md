# 🦅 Eagle by Blackwater
## Market Monitoring & Signal Interpretation System

---

### Architecture
```
Raw Data → Clean Features → Rules + LLM → Logs + Dashboard
   ↓              ↓               ↓              ↓
data/          signals/        reasoning/     output/
loader.py      engine.py       llm.py         logger.py
```

### Quick Start

**1. Install dependencies**
```bash
cd eagle
pip install -r requirements.txt
```

**2. Verify your .env file**
The `.env` file should already contain your API keys:
```
FMP_API_KEY=your_fmp_key
OPENAI_API_KEY=your_openai_key
```

**3. Run Eagle**
```bash
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`

---

### Features

| Layer | What it does |
|-------|-------------|
| **Data** | Fetches daily OHLCV from Financial Modeling Prep for SPY, QQQ, GLD, TLT, BTCUSD |
| **Signals** | Computes momentum, realized vol, drawdown, correlation, z-scores, regime tags |
| **Reasoning** | Rule engine flags risks; GPT-4o-mini generates plain-English summaries |
| **Output** | Logs to `eagle_log.csv`; Streamlit dashboard + chat agent |

### Dashboard Layout (Cursor-style)

```
┌─────────────┬──────────────────────────┬──────────────────┐
│  Asset List │   Charts + Signals        │  Eagle Chat      │
│  Quick      │   Price / Vol / Momentum  │  Agent           │
│  Metrics    │   Drawdown / Correlation  │                  │
│  Flags      │   Daily LLM Summary       │  Quick prompts   │
└─────────────┴──────────────────────────┴──────────────────┘
```

### Signals Computed

- **Momentum** — 20-day price momentum + rolling z-score
- **Realized Volatility** — 20-day annualized, tagged as: low / normal / elevated / extreme
- **Drawdown** — 60-day rolling max drawdown
- **Correlation** — 60-day rolling cross-asset correlation matrix
- **Regime** — Combined momentum + vol regime tag

### Configuring Thresholds

Edit `config.py`:
```python
VOL_LOW = 0.10          # < 10% ann vol = "low"
VOL_NORMAL = 0.18       # 10–18% = "normal"
VOL_ELEVATED = 0.28     # 18–28% = "elevated", above = "extreme"
MOMENTUM_UP_THRESHOLD = 1.0   # Z-score threshold for uptrend
DRAWDOWN_WARN = -0.05   # 5% drawdown warning
DRAWDOWN_ALERT = -0.10  # 10% drawdown alert
```

### Adding Assets

In `config.py`:
```python
FMP_ASSETS = ["SPY", "QQQ", "GLD", "TLT", "AAPL", "XLE"]
CRYPTO_ASSETS = ["BTCUSD", "ETHUSD"]
```

### Output Files

- `eagle_log.csv` — Daily signal log (date, symbol, regimes, flags, LLM summary)

---

*Eagle does not recommend trades or predict prices. All LLM output is advisory.*
