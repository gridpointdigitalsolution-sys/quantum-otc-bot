"""Momentum / drift FOLLOW setups (for trending or drifting 24/7 assets:
Jump indices, Step, R_50, and the Boom/Crash drift). KB7 S4/S11 family (trend-continuation).

- MomentumFollow: trade in the direction of an EMA-slope / fast-vs-slow EMA stack, entering
  on a continuation candle. High hit-rate when the asset has a persistent drift.
- DriftBias: pure directional bias when an asset has a structural one-way drift (e.g. the
  Daily-Reset / Boom-Crash inter-spike drift). Trades the dominant direction only, gated by
  a short trend confirmation. (Boom/Crash flagged risky by user -> reported separately.)
"""
from __future__ import annotations
import numpy as np
from .base import Strategy, Signal
from ..indicators import ema, adx as adx_ind


class MomentumFollow(Strategy):
    name = "momentum_follow"

    def __init__(self, expiry_sec=120, ema_fast=10, ema_slow=20, use_adx=True,
                 adx_n=14, adx_min=22.0, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.ef = ema_fast; self.es = ema_slow
        self.use_adx = use_adx; self.adx_n = adx_n; self.adx_min = adx_min

    def warmup(self):
        return max(self.es + 2, 2 * self.adx_n + 2)

    def precompute(self, o, h, l, c):
        self.c = c
        self.fast = ema(c, self.ef)
        self.slow = ema(c, self.es)
        self.adx = adx_ind(h, l, c, self.adx_n) if self.use_adx else None

    def signal_at(self, i):
        if i < self.warmup():
            return None
        f, s = self.fast[i], self.slow[i]
        if np.isnan(f) or np.isnan(s):
            return None
        if self.use_adx:
            a = self.adx[i]
            if np.isnan(a) or a < self.adx_min:
                return None
        # continuation candle in the stack direction
        up_bar = self.c[i] > self.c[i - 1]
        if f > s and up_bar:
            return Signal(i, "CALL", self.expiry_sec, "A", "ema-stack up + cont")
        if f < s and not up_bar:
            return Signal(i, "PUT", self.expiry_sec, "A", "ema-stack down + cont")
        return None


class DriftBias(Strategy):
    """One-way structural drift: bet the dominant direction, gated by EMA side.
    `bias` = 'up' or 'down' (the asset's known drift). For Boom (drifts down) -> 'down'."""
    name = "drift_bias"

    def __init__(self, expiry_sec=60, bias="down", ema_n=50, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.bias = bias; self.ema_n = ema_n

    def warmup(self):
        return self.ema_n + 2

    def precompute(self, o, h, l, c):
        self.c = c
        self.e = ema(c, self.ema_n)

    def signal_at(self, i):
        if i < self.warmup():
            return None
        e = self.e[i]
        if np.isnan(e):
            return None
        if self.bias == "down" and self.c[i] < e:
            return Signal(i, "PUT", self.expiry_sec, "A", "down-drift below ema")
        if self.bias == "up" and self.c[i] > e:
            return Signal(i, "CALL", self.expiry_sec, "A", "up-drift above ema")
        return None
