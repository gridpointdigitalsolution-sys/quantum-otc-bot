"""Pocket Option DATA SOURCE — candles + live payouts via the unofficial WS (ssid).

Uses BinaryOptionsToolsV2 (Rust-backed, maintained). UNOFFICIAL — violates PO ToS, can
break without notice (KB9). Demo first. ssid is a session token grabbed from the PO web
terminal; it EXPIRES, so it's supplied at run time (secrets/po.env or --ssid), never committed.

PO asset symbols use the `<PAIR>_otc` convention, e.g. "AUDCAD_otc", "EURGBP_otc".
get_candles(asset, timeframe_sec, period_sec) returns OHLC dicts. PO history depth is
shallow and undocumented — fetch_candles reports the REAL number returned; if it's far
short of the target, the honest answer is "record live forward" (KB7 open risk #6).
"""
from __future__ import annotations
import os

from .candles import Candle, CandleSeries


# 92% OTC currency universe (PO-target-assets.md) -> PO `_otc` symbols.
PO_OTC_92 = [
    "AEDCNY_otc", "AUDCAD_otc", "AUDCHF_otc", "AUDNZD_otc", "CHFNOK_otc",
    "EURGBP_otc", "EURNZD_otc", "EURTRY_otc", "GBPJPY_otc", "NZDUSD_otc",
    "USDCAD_otc", "USDINR_otc", "USDRUB_otc",
]
# >=90% second tier
PO_OTC_90 = ["GBPAUD_otc", "NZDJPY_otc", "AUDJPY_otc"]


def load_ssid(cli_ssid: str | None = None) -> str:
    """Resolve ssid: explicit arg > secrets/po.env (PO_SSID=...) > env var PO_SSID."""
    if cli_ssid:
        return cli_ssid
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.dirname(os.path.dirname(here))
    envp = os.path.join(proj, "secrets", "po.env")
    if os.path.exists(envp):
        with open(envp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("PO_SSID="):
                    return line.split("=", 1)[1].strip()
    v = os.environ.get("PO_SSID")
    if v:
        return v
    raise RuntimeError("No PO ssid. Put PO_SSID=... in secrets/po.env or pass --ssid.")


def _to_series(symbol: str, gran: int, rows) -> CandleSeries:
    """Normalize PO candle rows (list of dicts) to CandleSeries.
    PO rows expose time/open/high/low/close (key names vary by version)."""
    candles = []
    for r in rows:
        epoch = r.get("time") or r.get("epoch") or r.get("timestamp")
        if epoch is None:
            continue
        candles.append(Candle(
            int(float(epoch)),
            float(r.get("open")), float(r.get("high")),
            float(r.get("low")), float(r.get("close")),
        ))
    return CandleSeries(symbol, gran, candles)


async def fetch_candles(asset: str, timeframe_sec: int, total_bars: int,
                        ssid: str | None = None) -> CandleSeries:
    """Fetch up to `total_bars` candles for one PO asset. Returns CandleSeries
    (may be shorter than requested — PO history is shallow; caller reports the real n)."""
    from BinaryOptionsToolsV2 import PocketOptionAsync

    ssid = load_ssid(ssid)
    api = PocketOptionAsync(ssid)
    try:
        period = total_bars * timeframe_sec
        rows = await api.get_candles(asset, timeframe_sec, period)
        return _to_series(asset, timeframe_sec, rows)
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass


async def get_payouts(ssid: str | None = None) -> dict:
    """Live payout % per asset (broker-reported; may lag — DASHBOARD honesty note)."""
    from BinaryOptionsToolsV2 import PocketOptionAsync
    ssid = load_ssid(ssid)
    api = PocketOptionAsync(ssid)
    try:
        return await api.payout()
    finally:
        try:
            await api.shutdown()
        except Exception:
            pass
