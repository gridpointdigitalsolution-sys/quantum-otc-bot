"""S10 MACD-Triple-Gate + S11 SuperTrend+EMA150 (KB7 Alice setups — only ones with a real
self-reported backtest). Trend-continuation family. No look-ahead: bar i uses data <= i.
"""
from __future__ import annotations
import numpy as np
from .base import Strategy, Signal
from ..indicators import ema, atr as atr_ind


def _macd(c, fast=12, slow=26, sig=9):
    line = ema(c, fast) - ema(c, slow)
    signal = ema(line, sig)
    return line, signal


def _supertrend(h, l, c, period=12, mult=3.0):
    a = atr_ind(h, l, c, period)
    hl2 = (h + l) / 2.0
    upper = hl2 + mult * a
    lower = hl2 - mult * a
    n = len(c)
    st = np.full(n, np.nan)
    dir_up = np.zeros(n, dtype=bool)  # True = uptrend (green)
    for i in range(1, n):
        if np.isnan(a[i]):
            continue
        fu = upper[i]; fl = lower[i]
        prev = st[i - 1]
        if np.isnan(prev):
            st[i] = fl; dir_up[i] = True; continue
        if dir_up[i - 1]:
            fl = max(fl, prev)
            if c[i] < fl:
                dir_up[i] = False; st[i] = fu
            else:
                dir_up[i] = True; st[i] = fl
        else:
            fu = min(fu, prev)
            if c[i] > fu:
                dir_up[i] = True; st[i] = fl
            else:
                dir_up[i] = False; st[i] = fu
    return st, dir_up


class MacdTripleGate(Strategy):
    name = "macd_triple"

    def __init__(self, expiry_sec=180, ema_n=100, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.ema_n = ema_n

    def warmup(self):
        return self.ema_n + 30

    def precompute(self, o, h, l, c):
        self.c = c
        self.line, self.sig = _macd(c)
        self.ema = ema(c, self.ema_n)

    def signal_at(self, i):
        if i < self.warmup():
            return None
        ln, lp = self.line[i], self.line[i - 1]
        sn, sp = self.sig[i], self.sig[i - 1]
        e = self.ema[i]
        if any(np.isnan(x) for x in (ln, lp, sn, sp, e)):
            return None
        crossed_up = lp <= sp and ln > sn
        crossed_dn = lp >= sp and ln < sn
        # CALL: MACD crosses up while below zero + price above EMA
        if crossed_up and ln < 0 and self.c[i] > e:
            return Signal(i, "CALL", self.expiry_sec, "A+", "macd up<0 +ema")
        if crossed_dn and ln > 0 and self.c[i] < e:
            return Signal(i, "PUT", self.expiry_sec, "A+", "macd dn>0 +ema")
        return None


class SuperTrendEma(Strategy):
    name = "supertrend_ema"

    def __init__(self, expiry_sec=120, ema_n=150, st_period=12, st_mult=3.0, **kw):
        super().__init__(expiry_sec=expiry_sec, **kw)
        self.ema_n = ema_n; self.stp = st_period; self.stm = st_mult

    def warmup(self):
        return self.ema_n + 30

    def precompute(self, o, h, l, c):
        self.c = c
        self.st, self.dir_up = _supertrend(h, l, c, self.stp, self.stm)
        self.ema = ema(c, self.ema_n)

    def signal_at(self, i):
        if i < self.warmup():
            return None
        e = self.ema[i]
        if np.isnan(e) or np.isnan(self.st[i]):
            return None
        flip_up = self.dir_up[i] and not self.dir_up[i - 1]
        flip_dn = (not self.dir_up[i]) and self.dir_up[i - 1]
        mom = abs(self.c[i] - self.c[i - 1])
        mom_prev = abs(self.c[i - 1] - self.c[i - 2])
        growing = mom >= mom_prev
        if flip_up and self.c[i] > e and growing:
            return Signal(i, "CALL", self.expiry_sec, "A+", "ST flip up +ema150")
        if flip_dn and self.c[i] < e and growing:
            return Signal(i, "PUT", self.expiry_sec, "A+", "ST flip dn +ema150")
        return None
