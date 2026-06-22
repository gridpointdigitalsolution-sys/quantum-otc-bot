"""Pluggable strategy interface — one contract every setup implements.

A strategy looks at CLOSED bars only and, on each bar i, emits a Signal or None.
The backtester enters at bar i+1 OPEN and settles at the expiry close. No look-ahead:
a strategy may use close[:i+1] but NEVER close[i+1:].

Signal.direction: "CALL" (price up over expiry) or "PUT" (price down).
Signal.expiry_sec: chosen per setup (KB7: half-life clamp 60..300).
Signal.quality: "A" or "A+" -> drives risk % and the off-peak payout allowance.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Signal:
    bar_index: int          # the CLOSED bar that produced the signal
    direction: str          # "CALL" | "PUT"
    expiry_sec: int
    quality: str = "A"      # "A" | "A+"
    reason: str = ""


class Strategy:
    """Base class. Subclasses implement precompute() + signal_at()."""
    name = "base"

    def __init__(self, expiry_sec: int = 60, **params):
        self.expiry_sec = expiry_sec
        self.params = params

    def precompute(self, o, h, l, c) -> None:
        """Compute all indicator arrays once (vectorized). Store on self."""
        raise NotImplementedError

    def signal_at(self, i: int) -> Signal | None:
        """Return a Signal for CLOSED bar i, or None. Uses only data <= i."""
        raise NotImplementedError

    def warmup(self) -> int:
        """Bars to skip at the start (indicator warm-up)."""
        return 50
