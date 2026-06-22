"""Indicators — pure numpy, all CAUSAL (value at bar i uses only bars <= i).

Hand-rolled (Py3.14 has no TA-Lib wheel) and verified against standard definitions.
Every function returns an array aligned to the input close array; leading warm-up
positions are NaN. The backtester must never act on a NaN bar.
"""
from __future__ import annotations
import numpy as np


def sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    if len(x) < n:
        return out
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def rolling_std(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    if len(x) < n:
        return out
    c1 = np.cumsum(np.insert(x, 0, 0.0))
    c2 = np.cumsum(np.insert(x * x, 0, 0.0))
    s = c1[n:] - c1[:-n]
    ss = c2[n:] - c2[:-n]
    var = (ss - s * s / n) / n          # population std (matches Bollinger convention)
    var = np.clip(var, 0, None)
    out[n - 1:] = np.sqrt(var)
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    if len(x) < n:
        return out
    k = 2.0 / (n + 1.0)
    seed = np.mean(x[:n])               # SMA seed
    out[n - 1] = seed
    for i in range(n, len(x)):
        out[i] = x[i] * k + out[i - 1] * (1 - k)
    return out


def bollinger(close: np.ndarray, n: int = 20, mult: float = 2.0):
    """Returns (mid, upper, lower, width_pct). width_pct = (upper-lower)/mid."""
    mid = sma(close, n)
    sd = rolling_std(close, n)
    upper = mid + mult * sd
    lower = mid - mult * sd
    width = (upper - lower) / np.where(mid == 0, np.nan, mid)
    return mid, upper, lower, width


def rsi(close: np.ndarray, n: int = 14) -> np.ndarray:
    """Wilder's RSI."""
    out = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < n + 1:
        return out
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_g = gain[:n].mean()
    avg_l = loss[:n].mean()
    for i in range(n, len(close)):
        g = gain[i - 1]
        l = loss[i - 1]
        avg_g = (avg_g * (n - 1) + g) / n
        avg_l = (avg_l * (n - 1) + l) / n
        rs = avg_g / avg_l if avg_l > 0 else np.inf
        out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def stochastic(high, low, close, k_period=5, d_period=3, smooth=3):
    """Returns (%K, %D). Fast %K smoothed by `smooth`, %D = SMA(%K, d_period)."""
    n = len(close)
    raw_k = np.full(n, np.nan)
    for i in range(k_period - 1, n):
        hh = high[i - k_period + 1:i + 1].max()
        ll = low[i - k_period + 1:i + 1].min()
        rng = hh - ll
        raw_k[i] = 100.0 * (close[i] - ll) / rng if rng > 0 else 50.0
    k = sma(raw_k, smooth)
    d = sma(k, d_period)
    return k, d


def true_range(high, low, close) -> np.ndarray:
    n = len(close)
    tr = np.full(n, np.nan)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return tr


def atr(high, low, close, n: int = 14) -> np.ndarray:
    tr = true_range(high, low, close)
    out = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < n + 1:
        return out
    out[n] = np.nanmean(tr[1:n + 1])
    for i in range(n + 1, len(close)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def adx(high, low, close, n: int = 14) -> np.ndarray:
    """Wilder ADX — trend-strength. <20 = range (mean-reversion regime), >25 = trend."""
    sz = len(close)
    out = np.full(sz, np.nan)
    if sz < 2 * n + 1:
        return out
    up = high[1:] - high[:-1]
    dn = low[:-1] - low[1:]
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = true_range(high, low, close)[1:]
    atr_s = np.zeros(sz - 1)
    pdm_s = np.zeros(sz - 1)
    mdm_s = np.zeros(sz - 1)
    atr_s[n - 1] = tr[:n].sum()
    pdm_s[n - 1] = plus_dm[:n].sum()
    mdm_s[n - 1] = minus_dm[:n].sum()
    for i in range(n, sz - 1):
        atr_s[i] = atr_s[i - 1] - atr_s[i - 1] / n + tr[i]
        pdm_s[i] = pdm_s[i - 1] - pdm_s[i - 1] / n + plus_dm[i]
        mdm_s[i] = mdm_s[i - 1] - mdm_s[i - 1] / n + minus_dm[i]
    dx = np.full(sz - 1, np.nan)
    for i in range(n - 1, sz - 1):
        if atr_s[i] > 0:
            pdi = 100 * pdm_s[i] / atr_s[i]
            mdi = 100 * mdm_s[i] / atr_s[i]
            s = pdi + mdi
            dx[i] = 100 * abs(pdi - mdi) / s if s > 0 else 0.0
    # ADX = Wilder-smoothed DX
    first = 2 * n - 2
    if first >= sz - 1:
        return out
    adx_arr = np.full(sz - 1, np.nan)
    adx_arr[first] = np.nanmean(dx[n - 1:first + 1])
    for i in range(first + 1, sz - 1):
        if not np.isnan(dx[i]):
            adx_arr[i] = (adx_arr[i - 1] * (n - 1) + dx[i]) / n
    out[1:] = adx_arr
    return out


def rolling_median(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    for i in range(n - 1, len(x)):
        out[i] = np.median(x[i - n + 1:i + 1])
    return out
