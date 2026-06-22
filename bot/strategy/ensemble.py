"""Higher-selectivity reversion setups for binary (the WR lever = stacking gates).

StochAtLevel  — Stochastic(5,3,3) %K/%D cross out of an extreme zone, AT an S/R level
                (RockStarrFX flagship + KB7 S2). Stoch cross is a cleaner turn trigger
                than RSI on some pairs.
TripleGate    — the tightest reversion: RSI extreme + AT S/R level + REJECTION candle
                (close back toward mean) + minimum bar-range (skip dead/flat candles that
                cause ties). Fewest, highest-quality trades -> highest WR.

No look-ahead: bar i uses only data <= i; backtester enters at i+1 open.
"""
from __future__ import annotations
import numpy as np
from .base import Strategy, Signal
from ..indicators import rsi as rsi_ind, stochastic, atr as atr_ind, sma, rolling_std


class WilliamsAtLevel(Strategy):
    """Williams %R snap-back from extreme, AT an S/R level (KB7 S9, range-only)."""
    name = "williams_at_level"

    def __init__(self, expiry_sec=120, wr_n=10, ob=-20.0, os=-80.0, sr_lookback=20,
                 tol_atr=0.7, atr_n=14, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.wr_n = wr_n; self.ob = ob; self.os = os
        self.sr_lb = sr_lookback; self.tol = tol_atr; self.atr_n = atr_n

    def warmup(self):
        return max(self.wr_n + 2, self.sr_lb + 2, self.atr_n + 2)

    def precompute(self, o, h, l, c):
        self.h, self.l, self.c = h, l, c
        n = len(c); wr = np.full(n, np.nan)
        for i in range(self.wr_n - 1, n):
            hh = h[i - self.wr_n + 1:i + 1].max(); ll = l[i - self.wr_n + 1:i + 1].min()
            rng = hh - ll
            wr[i] = -100.0 * (hh - c[i]) / rng if rng > 0 else -50.0
        self.wr = wr
        self.atr = atr_ind(h, l, c, self.atr_n)

    def signal_at(self, i):
        if i < self.warmup():
            return None
        w0, w1, a = self.wr[i], self.wr[i-1], self.atr[i]
        if np.isnan(w0) or np.isnan(w1) or np.isnan(a) or a <= 0:
            return None
        res = np.max(self.h[i - self.sr_lb:i]); sup = np.min(self.l[i - self.sr_lb:i])
        tol = self.tol * a
        # %R near 0 (overbought) snapping down at resistance -> PUT
        if w1 >= self.ob and w0 < w1 and abs(self.h[i] - res) <= tol:
            return Signal(i, "PUT", self.expiry_sec, "A+", "%R OB@res")
        # %R near -100 (oversold) snapping up at support -> CALL
        if w1 <= self.os and w0 > w1 and abs(self.l[i] - sup) <= tol:
            return Signal(i, "CALL", self.expiry_sec, "A+", "%R OS@sup")
        return None


class BandRevAtLevel(Strategy):
    """S1 Bollinger reversion + S/R confluence: close beyond band, reject back inside, at level."""
    name = "band_at_level"

    def __init__(self, expiry_sec=180, n=20, mult=2.0, sr_lookback=20, tol_atr=0.8,
                 atr_n=14, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.n = n; self.mult = mult; self.sr_lb = sr_lookback
        self.tol = tol_atr; self.atr_n = atr_n

    def warmup(self):
        return max(self.n + 2, self.sr_lb + 2, self.atr_n + 2)

    def precompute(self, o, h, l, c):
        self.h, self.l, self.c = h, l, c
        m = sma(c, self.n); s = rolling_std(c, self.n)
        self.up = m + self.mult * s; self.lo = m - self.mult * s
        self.atr = atr_ind(h, l, c, self.atr_n)

    def signal_at(self, i):
        if i < self.warmup():
            return None
        a = self.atr[i]
        if np.isnan(self.up[i-1]) or np.isnan(a) or a <= 0:
            return None
        res = np.max(self.h[i - self.sr_lb:i]); sup = np.min(self.l[i - self.sr_lb:i])
        tol = self.tol * a
        # prior bar pierced upper band, this bar closes back inside, at resistance -> PUT
        if self.h[i-1] >= self.up[i-1] and self.c[i] < self.up[i] and abs(self.h[i] - res) <= tol:
            return Signal(i, "PUT", self.expiry_sec, "A+", "band rej upper@res")
        if self.l[i-1] <= self.lo[i-1] and self.c[i] > self.lo[i] and abs(self.l[i] - sup) <= tol:
            return Signal(i, "CALL", self.expiry_sec, "A+", "band rej lower@sup")
        return None


class StochAtLevel(Strategy):
    name = "stoch_at_level"

    def __init__(self, expiry_sec=120, k=5, d=3, smooth=3, ob=80.0, os=20.0,
                 sr_lookback=20, tol_atr=0.6, atr_n=14, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.k = k; self.d = d; self.smooth = smooth; self.ob = ob; self.os = os
        self.sr_lb = sr_lookback; self.tol = tol_atr; self.atr_n = atr_n

    def warmup(self):
        return max(self.k + self.d + self.smooth + 2, self.sr_lb + 2, self.atr_n + 2)

    def precompute(self, o, h, l, c):
        self.h, self.l, self.c = h, l, c
        self.K, self.D = stochastic(h, l, c, self.k, self.d, self.smooth)
        self.atr = atr_ind(h, l, c, self.atr_n)

    def signal_at(self, i):
        if i < self.warmup():
            return None
        k0, k1, d0, d1 = self.K[i], self.K[i-1], self.D[i], self.D[i-1]
        a = self.atr[i]
        if any(np.isnan(x) for x in (k0, k1, d0, d1, a)) or a <= 0:
            return None
        res = np.max(self.h[i - self.sr_lb:i]); sup = np.min(self.l[i - self.sr_lb:i])
        tol = self.tol * a
        cross_dn = k1 >= d1 and k0 < d0      # %K crosses below %D
        cross_up = k1 <= d1 and k0 > d0
        if k1 >= self.ob and cross_dn and abs(self.h[i] - res) <= tol:
            return Signal(i, "PUT", self.expiry_sec, "A+", "stoch OB cross@res")
        if k1 <= self.os and cross_up and abs(self.l[i] - sup) <= tol:
            return Signal(i, "CALL", self.expiry_sec, "A+", "stoch OS cross@sup")
        return None


class TripleGate(Strategy):
    name = "triple_gate"

    def __init__(self, expiry_sec=120, rsi_n=14, ob=70.0, os=30.0, sr_lookback=20,
                 tol_atr=0.6, atr_n=14, min_range_atr=0.4, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.rsi_n = rsi_n; self.ob = ob; self.os = os
        self.sr_lb = sr_lookback; self.tol = tol_atr; self.atr_n = atr_n
        self.min_range = min_range_atr

    def warmup(self):
        return max(self.rsi_n + 2, self.sr_lb + 2, self.atr_n + 2)

    def precompute(self, o, h, l, c):
        self.o, self.h, self.l, self.c = o, h, l, c
        self.rsi = rsi_ind(c, self.rsi_n)
        self.atr = atr_ind(h, l, c, self.atr_n)

    def signal_at(self, i):
        if i < self.warmup():
            return None
        r0, r1 = self.rsi[i], self.rsi[i-1]
        a = self.atr[i]
        if np.isnan(r0) or np.isnan(r1) or np.isnan(a) or a <= 0:
            return None
        rng = self.h[i] - self.l[i]
        if rng < self.min_range * a:          # skip flat/dead candles (tie risk)
            return None
        res = np.max(self.h[i - self.sr_lb:i]); sup = np.min(self.l[i - self.sr_lb:i])
        tol = self.tol * a
        # PUT: overbought + at resistance + rejection (close in lower half of bar) + RSI turning down
        if (r1 >= self.ob and r0 < r1 and abs(self.h[i] - res) <= tol
                and self.c[i] <= self.l[i] + 0.5 * rng):
            return Signal(i, "PUT", self.expiry_sec, "A+", f"3gate OB@res r={r1:.0f}")
        # CALL: oversold + at support + rejection (close in upper half) + RSI turning up
        if (r1 <= self.os and r0 > r1 and abs(self.l[i] - sup) <= tol
                and self.c[i] >= self.h[i] - 0.5 * rng):
            return Signal(i, "CALL", self.expiry_sec, "A+", f"3gate OS@sup r={r1:.0f}")
        return None
