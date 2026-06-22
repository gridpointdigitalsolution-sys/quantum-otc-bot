"""STEP 0 RUNNER — fetch Deriv synthetic candles + run the predictability gate.

Answers the make-or-break question: are Deriv synthetics even beatable?
Caches candles to data/raw/<symbol>_<gran>s.csv so re-runs are free (no re-fetch).

Run:  python scripts/run_step0.py
      python scripts/run_step0.py --bars 20000 --gran 60
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import CONFIG
from bot.data.deriv_source import fetch_candles
from bot.data.candles import CandleSeries
from bot.step0_predictability import run_step0

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")
OUT = os.path.join(PROJ, "data", "step0")


async def get_series(symbol: str, gran: int, bars: int) -> CandleSeries:
    path = os.path.join(RAW, f"{symbol}_{gran}s.csv")
    if os.path.exists(path):
        cs = CandleSeries.from_csv(path, symbol, gran)
        if len(cs) >= bars * 0.9:   # cached enough
            return cs
    cs = await fetch_candles(symbol, gran, bars)
    if len(cs):
        cs.to_csv(path)
    return cs


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", type=int, default=20000, help="candles per symbol")
    ap.add_argument("--gran", type=int, default=60, help="granularity seconds")
    ap.add_argument("--symbols", type=str, default="", help="comma list; default = config")
    args = ap.parse_args()

    symbols = (args.symbols.split(",") if args.symbols
               else list(CONFIG.deriv_step0_symbols))
    os.makedirs(OUT, exist_ok=True)

    print(f"\n{'='*78}\nSTEP 0 - DERIV SYNTHETIC PREDICTABILITY GATE")
    print(f"bars/symbol={args.bars}  granularity={args.gran}s  symbols={len(symbols)}")
    print(f"{'='*78}\n")

    verdicts = []
    for sym in symbols:
        try:
            cs = await get_series(sym, args.gran, args.bars)
        except Exception as e:
            print(f"{sym:10} FETCH FAILED: {e}")
            continue
        if len(cs) < 500:
            print(f"{sym:10} only {len(cs)} candles -> SKIP (need >=500)")
            continue
        gap = cs.gap_report()
        v = run_step0(sym, args.gran, cs.log_returns())
        verdicts.append(v)
        flag = "TRADEABLE" if v.tradeable else "DROP     "
        print(f"{sym:10} n={v.n_returns:6d} gaps={gap['gaps']:4d} "
              f"reject={v.n_reject}/5 dir={v.agreed_direction:11} -> {flag}")
        for t in v.tests:
            print(f"            - {t['name']:20} {('REJECT' if t['reject_random'] else 'random'):7} "
                  f"{t['direction']:11} | {t['note']}")
        print()

    # save full JSON
    out_path = os.path.join(OUT, f"step0_{args.gran}s.json")
    def _ser(o):
        if hasattr(o, "item"):   # numpy scalar -> python scalar
            return o.item()
        return str(o)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([v.to_dict() for v in verdicts], f, indent=2, default=_ser)

    tradeable = [v for v in verdicts if v.tradeable]
    print(f"{'='*78}\nVERDICT SUMMARY ({args.gran}s)")
    print(f"{'='*78}")
    print(f"tested: {len(verdicts)}   TRADEABLE: {len(tradeable)}   "
          f"DROP: {len(verdicts)-len(tradeable)}")
    for v in verdicts:
        print(f"  {'KEEP' if v.tradeable else 'drop':4} {v.symbol:10} {v.reason}")
    print(f"\nfull results -> {out_path}")
    if not tradeable:
        print("\n*** HONEST RESULT: NO Deriv synthetic shows exploitable structure at this")
        print("    timeframe. Mean-reversion on these = curve-fitting noise. The bot must")
        print("    live on PO OTC + Deriv REAL-MARKET assets. Re-run Step 0 on those. ***")


if __name__ == "__main__":
    asyncio.run(main())
