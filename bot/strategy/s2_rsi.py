"""S2 — RSI / Stochastic extreme fade + optional Bollinger confluence. KB7 HIGH.

Range regime. RSI in extreme zone at a band edge -> fade on the turn.
Confluence (S1 band + RSI) is the selectivity lever that lifts WR (the whole game).
"""
from __future__ import annotations
import numpy as np
from .base import Strategy, Signal
from ..indicators import rsi as rsi_ind, bollinger, adx as adx_ind


class S2RSI(Strategy):
    name = "s2_rsi"

    def __init__(self, expiry_sec=120, rsi_n=14, ob=70.0, os=30.0, use_bb=True,
                 bb_n=20, bb_mult=2.0, use_adx=True, adx_n=14, adx_max=25.0, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.rsi_n = rsi_n; self.ob = ob; self.os = os
        self.use_bb = use_bb; self.bb_n = bb_n; self.bb_mult = bb_mult
        self.use_adx = use_adx; self.adx_n = adx_n; self.adx_max = adx_max

    def warmup(self):
        return max(self.rsi_n + 2, self.bb_n + 2, 2 * self.adx_n + 2)

    def precompute(self, o, h, l, c):
        self.c = c
        self.rsi = rsi_ind(c, self.rsi_n)
        if self.use_bb:
            self.mid, self.up, self.lo, _ = bollinger(c, self.bb_n, self.bb_mult)
        self.adx = adx_ind(h, l, c, self.adx_n) if self.use_adx else None

    def signal_at(self, i):
        if i < self.warmup():
            return None
        r_prev, r_now = self.rsi[i - 1], self.rsi[i]
        if np.isnan(r_prev) or np.isnan(r_now):
            return None
        if self.use_adx:
            a = self.adx[i]
            if np.isnan(a) or a >= self.adx_max:
                return None
        # overbought turning down -> PUT
        if r_prev >= self.ob and r_now < r_prev:
            if not self.use_bb or self.c[i - 1] >= self.up[i - 1]:
                return Signal(i, "PUT", self.expiry_sec, "A", f"RSI {r_prev:.0f} turn")
        # oversold turning up -> CALL
        if r_prev <= self.os and r_now > r_prev:
            if not self.use_bb or self.c[i - 1] <= self.lo[i - 1]:
                return Signal(i, "CALL", self.expiry_sec, "A", f"RSI {r_prev:.0f} turn")
        return None
