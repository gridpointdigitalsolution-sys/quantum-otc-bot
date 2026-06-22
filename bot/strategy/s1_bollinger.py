"""S1 — Bollinger-Band Reversion (KB7 flagship mean-reversion). CONFIDENCE: HIGH.

3 gates (KB7):
  WHERE: prior bar tagged/closed beyond the band (z-score >= mult sigma).
  WHAT : rejection back inside — the signal bar closes back INSIDE the band.
  WHEN : act on that close-confirmation -> enter NEXT bar open (backtester does this).
Direction: tagged UPPER + reject -> PUT;  tagged LOWER + reject -> CALL.
Regime filter FIRST (range only): trade only if ADX < adx_max OR BB-width below its
rolling median (bands NOT widening). Widening bands => breakout => skip (that's S7's job).

Quality: A+ if BOTH the extreme is strong (close beyond band by >= aplus_sigma*sd) AND
regime is clearly ranging (adx < adx_aplus); else A. Drives risk sizing + off-peak gate.
"""
from __future__ import annotations
import numpy as np

from .base import Strategy, Signal
from ..indicators import bollinger, adx as adx_ind, rolling_median


class S1Bollinger(Strategy):
    name = "S1_bollinger"

    def __init__(self, expiry_sec: int = 60, bb_n: int = 20, bb_mult: float = 2.0,
                 adx_n: int = 14, adx_max: float = 25.0, adx_aplus: float = 18.0,
                 width_med_n: int = 50, aplus_sigma: float = 2.5, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.bb_n = bb_n
        self.bb_mult = bb_mult
        self.adx_n = adx_n
        self.adx_max = adx_max
        self.adx_aplus = adx_aplus
        self.width_med_n = width_med_n
        self.aplus_sigma = aplus_sigma

    def warmup(self) -> int:
        return max(self.bb_n + self.width_med_n, 2 * self.adx_n + 2) + 2

    def precompute(self, o, h, l, c) -> None:
        self.c = c
        self.mid, self.upper, self.lower, self.width = bollinger(c, self.bb_n, self.bb_mult)
        self.sd = (self.upper - self.mid) / self.bb_mult
        self.adx = adx_ind(h, l, c, self.adx_n)
        self.width_med = rolling_median(self.width, self.width_med_n)

    def _regime_ok(self, i: int) -> bool:
        """Range regime: ADX low OR bands not wider than their median."""
        a = self.adx[i]
        w, wm = self.width[i], self.width_med[i]
        if np.isnan(w) or np.isnan(wm):
            return False
        not_widening = w <= wm
        low_adx = (not np.isnan(a)) and a < self.adx_max
        return low_adx or not_widening

    def signal_at(self, i: int):
        # need a prior bar (i-1) that tagged the band, and bar i that rejected back inside
        if i < self.warmup():
            return None
        mid, up, lo, sd = self.mid[i], self.upper[i], self.lower[i], self.sd[i]
        if any(np.isnan(v) for v in (mid, up, lo, sd)) or sd <= 0:
            return None
        if not self._regime_ok(i):
            return None

        c_prev, c_now = self.c[i - 1], self.c[i]
        up_prev, lo_prev = self.upper[i - 1], self.lower[i - 1]

        # UPPER tag + reject back inside -> PUT
        if c_prev >= up_prev and c_now < up:
            strong = (c_prev - mid) >= self.aplus_sigma * sd
            ranging = (not np.isnan(self.adx[i])) and self.adx[i] < self.adx_aplus
            q = "A+" if (strong and ranging) else "A"
            return Signal(i, "PUT", self.expiry_sec, q,
                          f"upper-tag+reject z={(c_prev-mid)/sd:.2f} adx={self.adx[i]:.1f}")

        # LOWER tag + reject back inside -> CALL
        if c_prev <= lo_prev and c_now > lo:
            strong = (mid - c_prev) >= self.aplus_sigma * sd
            ranging = (not np.isnan(self.adx[i])) and self.adx[i] < self.adx_aplus
            q = "A+" if (strong and ranging) else "A"
            return Signal(i, "CALL", self.expiry_sec, q,
                          f"lower-tag+reject z={(mid-c_prev)/sd:.2f} adx={self.adx[i]:.1f}")

        return None
