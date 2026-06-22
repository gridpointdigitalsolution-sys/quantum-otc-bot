"""S3 — Liquidity-Sweep / Stop-Hunt Reversal + S/R-gated RSI (KB7 highest-cross-validation).

KB7 says S3 is the ONE pattern where book-quant + price-action + SMC + KB8 all agree, and the
missing ingredient in the generic battery was S/R-level confluence. Two strategies here:

S3 SweepReversal  — price sweeps a recent swing extreme then RECLAIMS it (the false break /
  liquidity grab), then closes back inside -> fade the trap. High hit-rate by design.
S2+ RsiAtLevel    — RSI extreme that occurs RIGHT AT a recent support/resistance level (not
  mid-range) + a turn candle. The S/R gate is the selectivity lever (KB7: "at a band edge or
  S/R level"). Far more selective than plain RSI -> higher WR.

No look-ahead: bar i uses only data <= i; backtester enters at i+1 open.
"""
from __future__ import annotations
import numpy as np
from .base import Strategy, Signal
from ..indicators import rsi as rsi_ind, atr as atr_ind, adx as adx_ind


class SweepReversal(Strategy):
    name = "sweep_reversal"

    def __init__(self, expiry_sec=180, lookback=8, reclaim_frac=0.0,
                 require_close_half=True, use_adx=False, adx_n=14, adx_max=30.0, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.lb = lookback
        self.reclaim_frac = reclaim_frac          # reclaim margin as frac of bar range
        self.require_close_half = require_close_half
        self.use_adx = use_adx; self.adx_n = adx_n; self.adx_max = adx_max

    def warmup(self):
        return max(self.lb + 2, 2 * self.adx_n + 2)

    def precompute(self, o, h, l, c):
        self.o, self.h, self.l, self.c = o, h, l, c
        self.adx = adx_ind(h, l, c, self.adx_n) if self.use_adx else None

    def signal_at(self, i):
        if i < self.warmup():
            return None
        if self.use_adx:
            a = self.adx[i]
            if np.isnan(a) or a >= self.adx_max:
                return None
        lo, hi, cl, op = self.l[i], self.h[i], self.c[i], self.o[i]
        rng = hi - lo
        if rng <= 0:
            return None
        prior_low = np.min(self.l[i - self.lb:i])
        prior_high = np.max(self.h[i - self.lb:i])
        margin = self.reclaim_frac * rng

        # swept the lows then reclaimed -> bullish trap -> CALL
        if lo < prior_low and cl > prior_low + margin:
            if not self.require_close_half or cl >= lo + 0.5 * rng:
                return Signal(i, "CALL", self.expiry_sec, "A+", "sweep low + reclaim")
        # swept the highs then reclaimed -> bearish trap -> PUT
        if hi > prior_high and cl < prior_high - margin:
            if not self.require_close_half or cl <= hi - 0.5 * rng:
                return Signal(i, "PUT", self.expiry_sec, "A+", "sweep high + reclaim")
        return None


class RsiAtLevel(Strategy):
    """RSI extreme + turn, gated to fire ONLY near a recent S/R level (within tol*ATR)."""
    name = "rsi_at_level"

    def __init__(self, expiry_sec=180, rsi_n=14, ob=70.0, os=30.0, sr_lookback=20,
                 tol_atr=0.5, atr_n=14, use_adx=False, adx_n=14, adx_max=40.0,
                 min_range_atr=0.0, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.rsi_n = rsi_n; self.ob = ob; self.os = os
        self.sr_lb = sr_lookback; self.tol = tol_atr; self.atr_n = atr_n
        self.use_adx = use_adx; self.adx_n = adx_n; self.adx_max = adx_max
        self.min_range = min_range_atr        # dead-candle filter (skip flat/doji)

    def warmup(self):
        return max(self.rsi_n + 2, self.sr_lb + 2, 2 * self.adx_n + 2)

    def precompute(self, o, h, l, c):
        self.h, self.l, self.c = h, l, c
        self.rsi = rsi_ind(c, self.rsi_n)
        self.atr = atr_ind(h, l, c, self.atr_n)
        self.adx = adx_ind(h, l, c, self.adx_n) if self.use_adx else None

    def signal_at(self, i):
        if i < self.warmup():
            return None
        r_prev, r_now = self.rsi[i - 1], self.rsi[i]
        a = self.atr[i]
        if np.isnan(r_prev) or np.isnan(r_now) or np.isnan(a) or a <= 0:
            return None
        # AVOID STRONG TRENDS: skip when ADX too high (fades get run over)
        if self.use_adx:
            ad = self.adx[i]
            if np.isnan(ad) or ad >= self.adx_max:
                return None
        # AVOID DEAD/FLAT CANDLES: skip when bar range is tiny (tie risk)
        if self.min_range > 0 and (self.h[i] - self.l[i]) < self.min_range * a:
            return None
        res = np.max(self.h[i - self.sr_lb:i])   # recent resistance
        sup = np.min(self.l[i - self.sr_lb:i])   # recent support
        tol = self.tol * a
        # overbought turning down AT resistance -> PUT
        if r_prev >= self.ob and r_now < r_prev and abs(self.h[i] - res) <= tol:
            return Signal(i, "PUT", self.expiry_sec, "A+", f"RSI{r_prev:.0f}@res")
        # oversold turning up AT support -> CALL
        if r_prev <= self.os and r_now > r_prev and abs(self.l[i] - sup) <= tol:
            return Signal(i, "CALL", self.expiry_sec, "A+", f"RSI{r_prev:.0f}@sup")
        return None
