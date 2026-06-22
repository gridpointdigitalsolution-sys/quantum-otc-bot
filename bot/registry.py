"""Strategy registry — maps a basket entry {setup,expiry,params} to a live Strategy instance.

The optimizer writes data/research/basket_po.json (list of winning configs). The live engine
and dashboard rebuild the exact same strategy objects from that file via build_strategy().
One source of truth: backtest and live use the identical class + params = no drift.
"""
from __future__ import annotations

from .strategy.s3_sweep import RsiAtLevel, SweepReversal
from .strategy.ensemble import StochAtLevel, TripleGate, WilliamsAtLevel, BandRevAtLevel
from .strategy.s1_bollinger import S1Bollinger
from .strategy.fade import FadeStreak, FadeExtreme

REGISTRY = {
    "rsi@lvl": RsiAtLevel,
    "triple": TripleGate,
    "stoch@lvl": StochAtLevel,
    "williams": WilliamsAtLevel,
    "band@lvl": BandRevAtLevel,
    "sweep": SweepReversal,
    "S1_bb": S1Bollinger,
    "fade_streak": FadeStreak,
    "fade_extreme": FadeExtreme,
}


def build_strategy(setup: str, expiry_sec: int, params: dict | None = None):
    """Instantiate a strategy from a basket entry. params optional (defaults used if omitted)."""
    if setup not in REGISTRY:
        raise KeyError(f"unknown setup '{setup}' (have {list(REGISTRY)})")
    return REGISTRY[setup](expiry_sec=expiry_sec, **(params or {}))
