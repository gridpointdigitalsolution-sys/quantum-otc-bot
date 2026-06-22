"""CONFLUENCE FADE — AND-gated mean-reversion for Range Break assets (RB100/RB200).

The sweep proved fading Range Break works (~60-65% raw). Selectivity is the lever to
push WR higher: require MULTIPLE independent reversion signals to AGREE before firing.
Fewer trades, higher hit-rate (KB7: confluence = the whole game for binaries).

Three independent fade votes, all on CLOSED bars only (no look-ahead):
  vote A  STREAK     : `streak` consecutive same-direction bars (exhaustion)
  vote B  Z-EXTREME  : |close - SMA(n)| / std(n) >= k  (statistical stretch)
  vote C  RSI-EXTREME: RSI(rsi_n) in overbought/oversold zone

All votes must point the SAME way (up-exhaustion -> PUT, down -> CALL). `min_votes`
controls strictness: 2 = looser/more trades, 3 = strict/highest WR. Optional ADX gate
keeps us out of strong trends (fades die in trends). Optional rejection: current bar must
be turning back toward the mean (confirms the snap-back started).
"""
from __future__ import annotations
import numpy as np
from .base import Strategy, Signal
from ..indicators import sma, rolling_std, rsi as rsi_ind, adx as adx_ind


class ConfluenceFade(Strategy):
    name = "confluence_fade"

    def __init__(self, expiry_sec=300, streak=4, n=20, k=2.0, rsi_n=14,
                 ob=70.0, os=30.0, min_votes=3, use_adx=True, adx_n=14,
                 adx_max=25.0, require_reject=True, quality="A", **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.streak = streak; self.n = n; self.k = k
        self.rsi_n = rsi_n; self.ob = ob; self.os = os
        self.min_votes = min_votes
        self.use_adx = use_adx; self.adx_n = adx_n; self.adx_max = adx_max
        self.require_reject = require_reject
        self._quality = quality

    def warmup(self):
        return max(self.streak + 2, self.n + 2, self.rsi_n + 2, 2 * self.adx_n + 2)

    def precompute(self, o, h, l, c):
        self.c = c
        self.dirs = np.sign(np.diff(c, prepend=c[0]))
        self.mid = sma(c, self.n)
        self.sd = rolling_std(c, self.n)
        self.rsi = rsi_ind(c, self.rsi_n)
        self.adx = adx_ind(h, l, c, self.adx_n) if self.use_adx else None

    def signal_at(self, i):
        if i < self.warmup():
            return None
        if self.use_adx:
            a = self.adx[i]
            if np.isnan(a) or a >= self.adx_max:
                return None
        mid, sd = self.mid[i], self.sd[i]
        if np.isnan(mid) or np.isnan(sd) or sd <= 0:
            return None
        r_now = self.rsi[i]
        if np.isnan(r_now):
            return None

        z = (self.c[i] - mid) / sd

        # --- collect UP-exhaustion votes (-> PUT) and DOWN-exhaustion votes (-> CALL) ---
        up_votes = 0; dn_votes = 0
        # vote A: streak
        seg = self.dirs[i - self.streak + 1:i + 1]
        if not np.any(seg == 0):
            if np.all(seg > 0): up_votes += 1
            elif np.all(seg < 0): dn_votes += 1
        # vote B: z-extreme
        if z >= self.k: up_votes += 1
        elif z <= -self.k: dn_votes += 1
        # vote C: rsi-extreme
        if r_now >= self.ob: up_votes += 1
        elif r_now <= self.os: dn_votes += 1

        # require min_votes on ONE side and zero on the other (clean agreement)
        if up_votes >= self.min_votes and dn_votes == 0:
            if self.require_reject and not (self.c[i] < self.c[i - 1]):
                return None
            return Signal(i, "PUT", self.expiry_sec, self._quality,
                          f"conf up votes={up_votes} z={z:.2f} rsi={r_now:.0f}")
        if dn_votes >= self.min_votes and up_votes == 0:
            if self.require_reject and not (self.c[i] > self.c[i - 1]):
                return None
            return Signal(i, "CALL", self.expiry_sec, self._quality,
                          f"conf dn votes={dn_votes} z={z:.2f} rsi={r_now:.0f}")
        return None
