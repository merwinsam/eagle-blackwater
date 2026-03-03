"""
Output Layer: Log daily signals to CSV, load history for charts.
"""

import os
import pandas as pd
from datetime import datetime

LOG_PATH = "eagle_log.csv"


def log_signals(signals_dict: dict, summary_text: str = ""):
    """Append today's signals as a row in the log CSV."""
    rows = []
    for sym, sig in signals_dict.items():
        if not sig:
            continue
        row = {
            "timestamp": datetime.now().isoformat(),
            "date": sig.get("date"),
            "symbol": sym,
            "price": sig.get("price"),
            "momentum_20d": sig.get("momentum_20d"),
            "momentum_regime": sig.get("momentum_regime"),
            "vol_20d_ann": sig.get("vol_20d_ann"),
            "vol_state": sig.get("vol_state"),
            "max_drawdown_60d": sig.get("max_drawdown_60d"),
            "market_regime": sig.get("market_regime"),
            "risk_flags": " | ".join(sig.get("risk_flags", [])),
            "summary": summary_text[:500] if sym == list(signals_dict.keys())[0] else "",
        }
        rows.append(row)

    if not rows:
        return

    df_new = pd.DataFrame(rows)
    if os.path.exists(LOG_PATH):
        df_existing = pd.read_csv(LOG_PATH)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(LOG_PATH, index=False)


def load_log() -> pd.DataFrame:
    """Load historical signal log."""
    if os.path.exists(LOG_PATH):
        df = pd.read_csv(LOG_PATH)
        df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame()
