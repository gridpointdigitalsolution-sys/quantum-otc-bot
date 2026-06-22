"""Deep-fetch Pocket Option OTC candle history via get_candles_advanced pagination.

PO basic get_candles caps at 150 bars. get_candles_advanced(asset, period, offset, time)
returns a window ENDING at `time`; we walk `time` backward to accumulate deep history.
Caches one CSV per asset (data/raw_po/<asset>_60s.csv). Real-market OTC only.

Run: python scripts/fetch_po.py --steps 300 --gran 60
"""
import argparse, asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.data.po_source import load_ssid
from bot.data.candles import Candle, CandleSeries

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw_po")


def is_currency_otc(sym: str) -> bool:
    """Keep real-market FX OTC pairs (6-letter code + _otc). Drop stocks (#, _otc on tickers),
    crypto (-USD), indices (VIX), commodities handled separately."""
    if not sym.endswith("_otc"):
        return False
    base = sym[:-4]
    if "#" in base or "-" in base:
        return False
    return len(base) == 6 and base.isalpha()


async def fetch_one(api, asset, gran, steps):
    seed = await api.get_candles(asset, gran, 150 * gran)
    if not seed:
        return None
    rows = {int(x["timestamp"]): x for x in seed}
    end = min(rows) - gran
    stalls = 0
    for _ in range(steps):
        try:
            r = await api.get_candles_advanced(asset, gran, 150 * gran, end)
        except Exception:
            stalls += 1
            r = None
        if not r:
            stalls += 1
        else:
            before = len(rows)
            for x in r:
                rows[int(x["timestamp"])] = x
            stalls = 0 if len(rows) > before else stalls + 1
        if stalls >= 3:
            break
        end = min(rows) - gran
    candles = [Candle(int(x["timestamp"]), float(x["open"]), float(x["high"]),
                      float(x["low"]), float(x["close"])) for x in rows.values()]
    candles.sort(key=lambda c: c.epoch)
    return CandleSeries(asset, gran, candles)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--gran", type=int, default=60)
    ap.add_argument("--minpayout", type=int, default=90)
    ap.add_argument("--assets", type=str, default="")
    args = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)

    from BinaryOptionsToolsV2 import PocketOptionAsync
    api = PocketOptionAsync(load_ssid())
    await asyncio.sleep(4)

    if args.assets:
        assets = args.assets.split(",")
    else:
        po = await api.payout()
        assets = sorted(s for s, p in po.items()
                        if is_currency_otc(s) and p >= args.minpayout)
    print(f"fetching {len(assets)} OTC FX pairs, steps={args.steps}")

    for i, a in enumerate(assets, 1):
        try:
            cs = await fetch_one(api, a, args.gran, args.steps)
        except Exception as e:
            print(f"[{i}/{len(assets)}] {a:14} ERR {repr(e)[:50]}")
            continue
        if not cs or len(cs) < 500:
            print(f"[{i}/{len(assets)}] {a:14} too few ({len(cs) if cs else 0})")
            continue
        path = os.path.join(RAW, f"{a}_{args.gran}s.csv")
        cs.to_csv(path)
        span = (cs.epoch[-1] - cs.epoch[0]) / 86400
        print(f"[{i}/{len(assets)}] {a:14} {len(cs):6} bars (~{span:.1f}d)")
    try:
        await api.shutdown()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
