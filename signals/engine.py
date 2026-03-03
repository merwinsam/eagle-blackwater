"""
Signal Layer: Compute momentum, volatility, correlation, regimes, and z-scores.
"""

import pandas as pd
import numpy as np
import config


# ── Momentum ──────────────────────────────────────────────────────────────────

def momentum(prices: pd.Series, lookback: int = None) -> pd.Series:
    lb = lookback or config.MOMENTUM_LOOKBACK
    return prices / prices.shift(lb) - 1.0


def momentum_zscore(prices: pd.Series, lookback: int = None, z_window: int = None) -> pd.Series:
    lb = lookback or config.MOMENTUM_LOOKBACK
    zw = z_window or config.ZSCORE_LOOKBACK
    mom = momentum(prices, lb)
    mu = mom.rolling(zw).mean()
    sigma = mom.rolling(zw).std()
    return (mom - mu) / sigma.replace(0, np.nan)


def momentum_regime(z_mom: float) -> str:
    up = config.MOMENTUM_UP_THRESHOLD
    down = config.MOMENTUM_DOWN_THRESHOLD
    if pd.isna(z_mom):
        return "unknown"
    if z_mom > up:
        return "uptrend"
    elif z_mom < down:
        return "downtrend"
    return "sideways"


# ── Volatility ────────────────────────────────────────────────────────────────

def realized_vol(returns: pd.Series, lookback: int = None, annualize: bool = True) -> pd.Series:
    lb = lookback or config.VOL_LOOKBACK
    rv = returns.rolling(lb).std()
    if annualize:
        rv = rv * np.sqrt(252)
    return rv


def vol_state(rv: float) -> str:
    if pd.isna(rv):
        return "unknown"
    if rv < config.VOL_LOW:
        return "low"
    elif rv < config.VOL_NORMAL:
        return "normal"
    elif rv < config.VOL_ELEVATED:
        return "elevated"
    return "extreme"


# ── Correlation ───────────────────────────────────────────────────────────────

def rolling_corr(returns_a: pd.Series, returns_b: pd.Series, lookback: int = None) -> pd.Series:
    lb = lookback or config.CORR_LOOKBACK
    return returns_a.rolling(lb).corr(returns_b)


def corr_state(corr: float) -> str:
    if pd.isna(corr):
        return "unknown"
    if corr > config.CORR_HIGH:
        return "concentrated"
    elif corr < config.CORR_LOW:
        return "diversified"
    return "moderate"


# ── Drawdown ──────────────────────────────────────────────────────────────────

def max_drawdown(prices: pd.Series, window: int = 60) -> pd.Series:
    rolling_max = prices.rolling(window).max()
    return (prices - rolling_max) / rolling_max


# ── Deviation from MA ─────────────────────────────────────────────────────────

def ma_deviation(prices: pd.Series, window: int = 20) -> pd.Series:
    ma = prices.rolling(window).mean()
    return (prices - ma) / ma


# ── Market Regime ─────────────────────────────────────────────────────────────

def market_regime(trend: str, v_state: str) -> str:
    if trend == "uptrend" and v_state in ("low", "normal"):
        return "calm uptrend"
    elif trend == "uptrend" and v_state in ("elevated", "extreme"):
        return "volatile uptrend"
    elif trend == "downtrend" and v_state in ("elevated", "extreme"):
        return "stress selloff"
    elif trend == "downtrend" and v_state in ("low", "normal"):
        return "quiet decline"
    elif trend == "sideways" and v_state in ("elevated", "extreme"):
        return "volatile chop"
    return "mixed / sideways"


# ── Risk Flags ────────────────────────────────────────────────────────────────

def compute_risk_flags(momentum_r: str, v_state: str, c_state: str, drawdown: float) -> list[str]:
    flags = []
    if momentum_r == "uptrend" and v_state in ("elevated", "extreme"):
        flags.append("⚠️ Trend up but volatility spiking — possible distribution phase")
    if momentum_r == "downtrend" and v_state in ("elevated", "extreme"):
        flags.append("🔴 Trend down with high volatility — stress selloff in progress")
    if c_state == "concentrated":
        flags.append("⚠️ High cross-asset correlation — diversification benefit reduced")
    if drawdown < config.DRAWDOWN_ALERT:
        flags.append(f"🔴 Significant drawdown: {drawdown:.1%} — approaching historical risk levels")
    elif drawdown < config.DRAWDOWN_WARN:
        flags.append(f"⚠️ Moderate drawdown: {drawdown:.1%} — monitor for continuation")
    if not flags:
        flags.append("✅ No major risk flags detected")
    return flags


# ── Full Signal Snapshot for one asset ───────────────────────────────────────

def compute_signals(sym: str, df: pd.DataFrame, peer_returns: pd.Series = None) -> dict:
    """Return a dict of latest signal values for one asset."""
    prices = df["adj_close"].dropna()
    rets = df["returns"].dropna()

    if len(prices) < config.ZSCORE_LOOKBACK + 10:
        return {}

    mom_series = momentum(prices)
    z_series = momentum_zscore(prices)
    rv_series = realized_vol(rets)
    dd_series = max_drawdown(prices)
    ma_dev_series = ma_deviation(prices)

    latest_mom = mom_series.iloc[-1]
    latest_z = z_series.iloc[-1]
    latest_rv = rv_series.iloc[-1]
    latest_dd = dd_series.iloc[-1]
    latest_ma_dev = ma_dev_series.iloc[-1]

    t_regime = momentum_regime(latest_z)
    v_state = vol_state(latest_rv)
    m_regime = market_regime(t_regime, v_state)

    # Correlation to peer (if provided)
    corr_val = np.nan
    c_state = "unknown"
    if peer_returns is not None:
        aligned_peer = peer_returns.reindex(rets.index).dropna()
        aligned_self = rets.reindex(aligned_peer.index).dropna()
        if len(aligned_self) >= config.CORR_LOOKBACK:
            corr_series = rolling_corr(aligned_self, aligned_peer)
            corr_val = corr_series.iloc[-1] if not corr_series.empty else np.nan
            c_state = corr_state(corr_val)

    flags = compute_risk_flags(t_regime, v_state, c_state, latest_dd)

    return {
        "symbol": sym,
        "date": str(df.index[-1].date()),
        "price": prices.iloc[-1],
        "momentum_20d": round(latest_mom, 4),
        "momentum_zscore": round(latest_z, 3) if not pd.isna(latest_z) else None,
        "momentum_regime": t_regime,
        "vol_20d_ann": round(latest_rv, 4),
        "vol_state": v_state,
        "corr_to_peer": round(corr_val, 3) if not pd.isna(corr_val) else None,
        "corr_state": c_state,
        "max_drawdown_60d": round(latest_dd, 4),
        "ma_deviation": round(latest_ma_dev, 4),
        "market_regime": m_regime,
        "risk_flags": flags,
        # series for charts
        "_mom_series": mom_series,
        "_rv_series": rv_series,
        "_dd_series": dd_series,
        "_z_series": z_series,
        "_prices": prices,
        "_rets": rets,
    }
