"""Mean-reversion FADE setups (for range/oscillating assets like RB100, baskets).

Two variants, both KB7-aligned (mean-revert snap-back at extremes, high hit-rate):
- FadeStreak: after `streak` consecutive same-direction candles, fade the next bar
  (exhaustion snap-back). Optional regime gate (ADX low).
- FadeExtreme: fade when close is `k` * rolling-std away from a short SMA (z-score
  reversion), optional require a rejection wick.
"""
from __future__ import annotations
import numpy as np
from .base import Strategy, Signal
from ..indicators import sma, rolling_std, adx as adx_ind


class FadeStreak(Strategy):
    name = "fade_streak"

    def __init__(self, expiry_sec=120, streak=3, use_adx=True, adx_n=14, adx_max=25.0, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.streak = streak
        self.use_adx = use_adx
        self.adx_n = adx_n
        self.adx_max = adx_max

    def warmup(self):
        return max(self.streak + 2, 2 * self.adx_n + 2)

    def precompute(self, o, h, l, c):
        self.o, self.c = o, c
        self.dirs = np.sign(np.diff(c, prepend=c[0]))  # per-bar direction
        self.adx = adx_ind(h, l, c, self.adx_n) if self.use_adx else None

    def signal_at(self, i):
        if i < self.warmup():
            return None
        if self.use_adx:
            a = self.adx[i]
            if np.isnan(a) or a >= self.adx_max:
                return None
        # last `streak` bars all same non-zero direction?
        seg = self.dirs[i - self.streak + 1:i + 1]
        if np.any(seg == 0) or not (np.all(seg > 0) or np.all(seg < 0)):
            return None
        up = seg[0] > 0
        # all up -> exhaustion -> PUT ; all down -> CALL
        return Signal(i, "PUT" if up else "CALL", self.expiry_sec, "A",
                      f"fade {self.streak}-streak {'up' if up else 'down'}")


class FadeExtreme(Strategy):
    name = "fade_extreme"

    def __init__(self, expiry_sec=120, n=20, k=2.0, use_adx=True, adx_n=14,
                 adx_max=25.0, require_reject=True, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.n = n; self.k = k; self.use_adx = use_adx
        self.adx_n = adx_n; self.adx_max = adx_max; self.require_reject = require_reject

    def warmup(self):
        return max(self.n + 2, 2 * self.adx_n + 2)

    def precompute(self, o, h, l, c):
        self.o, self.c = o, c
        self.mid = sma(c, self.n)
        self.sd = rolling_std(c, self.n)
        self.adx = adx_ind(h, l, c, self.adx_n) if self.use_adx else None

    def signal_at(self, i):
        if i < self.warmup():
            return None
        mid, sd = self.mid[i], self.sd[i]
        if np.isnan(mid) or np.isnan(sd) or sd <= 0:
            return None
        if self.use_adx:
            a = self.adx[i]
            if np.isnan(a) or a >= self.adx_max:
                return None
        z_prev = (self.c[i - 1] - self.mid[i - 1]) / self.sd[i - 1] if self.sd[i - 1] > 0 else 0
        z_now = (self.c[i] - mid) / sd
        # prior bar beyond +k, now pulling back inside -> PUT
        if z_prev >= self.k and (not self.require_reject or z_now < z_prev):
            return Signal(i, "PUT", self.expiry_sec, "A", f"z_prev={z_prev:.2f} reject")
        if z_prev <= -self.k and (not self.require_reject or z_now > z_prev):
            return Signal(i, "CALL", self.expiry_sec, "A", f"z_prev={z_prev:.2f} reject")
        return None
