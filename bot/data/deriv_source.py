"""Deriv DATA SOURCE — historical candles via official WebSocket `ticks_history`.

Deriv is the ONLY broker with an official, supported API. We use it for both Step 0
predictability data and live trading later. No token needed for ticks_history of
synthetic/public symbols, but we authorize with the demo token when present so the
same path works for account-scoped calls.

ticks_history candle request:
  {"ticks_history": "R_100", "style": "candles", "granularity": 60,
   "count": 5000, "end": <unix>, "adjust_start_time": 1}
returns {"candles": [{"epoch","open","high","low","close"}...]}.
Max 5000 candles/request -> paginate backward via `end`.
"""
from __future__ import annotations
import asyncio
import json
import os
import time

from ..data.candles import Candle, CandleSeries

WS_URL_TMPL = "wss://ws.derivws.com/websockets/v3?app_id={app_id}"
MAX_COUNT = 5000


def _load_env(path: str) -> dict:
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _secrets_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.dirname(os.path.dirname(here))  # .../option trading bot
    return os.path.join(proj, "secrets", "deriv.env")


async def fetch_candles(symbol: str, granularity_sec: int, total: int,
                        app_id: str | None = None) -> CandleSeries:
    """Fetch up to `total` candles for `symbol` by paging backward. Returns CandleSeries."""
    import websockets

    env = _load_env(_secrets_path())
    app_id = app_id or env.get("DERIV_APP_ID", "1089")
    url = WS_URL_TMPL.format(app_id=app_id)

    all_candles: list[Candle] = []
    end = int(time.time())
    stale_reconnects = 0

    async def _one_page(ws, count, end_):
        req = {"ticks_history": symbol, "style": "candles",
               "granularity": granularity_sec, "count": count,
               "end": end_, "adjust_start_time": 1}
        await ws.send(json.dumps(req))
        return json.loads(await ws.recv())

    while len(all_candles) < total:
        try:
            async with websockets.connect(url, max_size=2**23, ping_interval=15,
                                          ping_timeout=20, close_timeout=5) as ws:
                while len(all_candles) < total:
                    count = min(MAX_COUNT, total - len(all_candles))
                    resp = await _one_page(ws, count, end)
                    if "error" in resp:
                        raise RuntimeError(f"Deriv error for {symbol}: {resp['error'].get('message')}")
                    cs = resp.get("candles", [])
                    if not cs:
                        return CandleSeries(symbol, granularity_sec, all_candles)
                    batch = [Candle(int(c["epoch"]), float(c["open"]), float(c["high"]),
                                    float(c["low"]), float(c["close"])) for c in cs]
                    all_candles.extend(batch)
                    oldest = min(c.epoch for c in batch)
                    new_end = oldest - granularity_sec
                    if new_end >= end:   # no progress (out of history) -> done
                        return CandleSeries(symbol, granularity_sec, all_candles)
                    end = new_end
                    await asyncio.sleep(0.10)  # gentle on the public endpoint
        except (RuntimeError,):
            raise
        except Exception as e:
            # connection dropped (keepalive/timeout) -> reconnect and continue from `end`
            stale_reconnects += 1
            if stale_reconnects > 30:
                print(f"  [{symbol}] giving up after {stale_reconnects} reconnects: {e}")
                break
            await asyncio.sleep(0.5)
            continue

    return CandleSeries(symbol, granularity_sec, all_candles)
