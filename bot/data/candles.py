"""Normalized candle format shared by both brokers + no-look-ahead helpers.

ONE canonical OHLC representation regardless of source (Deriv WS / PO ssid).
Stored on disk as CSV with columns: epoch,open,high,low,close  (epoch = unix seconds, UTC).

No-look-ahead rule (enforced by convention + the backtester, not by the struct):
a candle is only usable for a SIGNAL once it has closed. The backtester signals on a
closed bar i and enters at bar i+1's open. This module never peeks forward.
"""
from __future__ import annotations
from dataclasses import dataclass
import csv
import os
import numpy as np


@dataclass(frozen=True)
class Candle:
    epoch: int      # unix seconds, UTC, = candle OPEN time
    open: float
    high: float
    low: float
    close: float


class CandleSeries:
    """Immutable-ish container of candles for one symbol@granularity.
    Holds parallel numpy arrays for fast vectorized indicators."""

    def __init__(self, symbol: str, granularity_sec: int, candles: list[Candle]):
        candles = sorted(candles, key=lambda c: c.epoch)
        # de-dup by epoch (Deriv pagination can overlap)
        seen, uniq = set(), []
        for c in candles:
            if c.epoch in seen:
                continue
            seen.add(c.epoch)
            uniq.append(c)
        self.symbol = symbol
        self.granularity_sec = granularity_sec
        self.epoch = np.array([c.epoch for c in uniq], dtype=np.int64)
        self.open = np.array([c.open for c in uniq], dtype=np.float64)
        self.high = np.array([c.high for c in uniq], dtype=np.float64)
        self.low = np.array([c.low for c in uniq], dtype=np.float64)
        self.close = np.array([c.close for c in uniq], dtype=np.float64)

    def __len__(self) -> int:
        return len(self.epoch)

    def log_returns(self) -> np.ndarray:
        """Close-to-close log returns. Length n-1."""
        c = self.close
        return np.diff(np.log(c))

    def gap_report(self) -> dict:
        """How clean is the series? Counts missing candles (epoch gaps)."""
        if len(self) < 2:
            return {"n": len(self), "gaps": 0, "max_gap_bars": 0}
        d = np.diff(self.epoch)
        step = self.granularity_sec
        gaps = int(np.sum(d != step))
        max_gap = int(d.max() // step) if len(d) else 0
        return {"n": len(self), "gaps": gaps, "max_gap_bars": max_gap,
                "first_epoch": int(self.epoch[0]), "last_epoch": int(self.epoch[-1])}

    # ── persistence ──
    def to_csv(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["epoch", "open", "high", "low", "close"])
            for i in range(len(self)):
                w.writerow([int(self.epoch[i]), self.open[i], self.high[i],
                            self.low[i], self.close[i]])

    @classmethod
    def from_csv(cls, path: str, symbol: str, granularity_sec: int) -> "CandleSeries":
        candles = []
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                candles.append(Candle(int(row["epoch"]), float(row["open"]),
                                      float(row["high"]), float(row["low"]),
                                      float(row["close"])))
        return cls(symbol, granularity_sec, candles)


def resample(base: CandleSeries, factor: int) -> CandleSeries:
    """Aggregate a 1m base series into higher-TF candles (factor=2 -> 2m, 5 -> 5m).
    Aligns groups on epoch; only EMITS a higher-TF candle when the full group exists
    (no partial/forward-filled bars -> no look-ahead, no fake closes)."""
    if factor <= 1:
        return base
    g = base.granularity_sec * factor
    out = []
    n = len(base)
    # group by floor(epoch / g)
    keys = base.epoch // g
    i = 0
    while i < n:
        j = i
        while j < n and keys[j] == keys[i]:
            j += 1
        grp = slice(i, j)
        # require a complete group of `factor` consecutive base bars
        if (j - i) == factor and base.epoch[j - 1] - base.epoch[i] == base.granularity_sec * (factor - 1):
            out.append(Candle(
                epoch=int(base.epoch[i]),
                open=float(base.open[i]),
                high=float(base.high[grp].max()),
                low=float(base.low[grp].min()),
                close=float(base.close[j - 1]),
            ))
        i = j
    return CandleSeries(base.symbol, g, out)
