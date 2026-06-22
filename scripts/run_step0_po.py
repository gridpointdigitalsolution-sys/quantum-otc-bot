"""STEP 0 for POCKET OPTION OTC — the real target universe.

Needs a fresh ssid (secrets/po.env PO_SSID=... or --ssid). Fetches live OTC candles,
caches to data/raw/po/, runs the same predictability gate, reports honestly.

Run:  python scripts/run_step0_po.py --ssid "<paste>" --bars 20000
      (or put PO_SSID in secrets/po.env then: python scripts/run_step0_po.py)
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.data.po_source import fetch_candles, get_payouts, load_ssid, PO_OTC_92, PO_OTC_90
from bot.step0_predictability import run_step0

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw", "po")
OUT = os.path.join(PROJ, "data", "step0")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ssid", type=str, default="")
    ap.add_argument("--bars", type=int, default=20000)
    ap.add_argument("--gran", type=int, default=60)
    ap.add_argument("--symbols", type=str, default="")
    args = ap.parse_args()

    ssid = load_ssid(args.ssid or None)
    symbols = (args.symbols.split(",") if args.symbols else PO_OTC_92 + PO_OTC_90)
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    print(f"\n{'='*78}\nSTEP 0 - POCKET OPTION OTC PREDICTABILITY GATE")
    print(f"bars/symbol(target)={args.bars}  gran={args.gran}s  symbols={len(symbols)}")
    print(f"{'='*78}\n")

    # live payouts (gate context)
    try:
        payouts = await get_payouts(ssid)
        print("LIVE PAYOUTS (broker-reported):")
        for s in symbols:
            p = payouts.get(s) if isinstance(payouts, dict) else None
            print(f"  {s:14} {p}")
        print()
    except Exception as e:
        print(f"(payout fetch failed: {e})\n")

    verdicts = []
    for sym in symbols:
        try:
            cs = await fetch_candles(sym, args.gran, args.bars, ssid)
        except Exception as e:
            print(f"{sym:14} FETCH FAILED: {e}")
            continue
        if len(cs):
            cs.to_csv(os.path.join(RAW, f"{sym}_{args.gran}s.csv"))
        if len(cs) < 500:
            print(f"{sym:14} only {len(cs)} candles -> SKIP (need >=500; PO history shallow -> may need live record)")
            continue
        gap = cs.gap_report()
        v = run_step0(sym, args.gran, cs.log_returns())
        verdicts.append(v)
        flag = "TRADEABLE" if v.tradeable else "DROP     "
        print(f"{sym:14} n={v.n_returns:6d} gaps={gap['gaps']:4d} "
              f"reject={v.n_reject}/5 dir={v.agreed_direction:11} -> {flag}")
        for t in v.tests:
            print(f"   - {t['name']:20} {('REJECT' if t['reject_random'] else 'random'):7} "
                  f"{t['direction']:11} | {t['note']}")
        print()

    def _ser(o):
        return o.item() if hasattr(o, "item") else str(o)
    with open(os.path.join(OUT, f"step0_po_{args.gran}s.json"), "w", encoding="utf-8") as f:
        json.dump([v.to_dict() for v in verdicts], f, indent=2, default=_ser)

    tradeable = [v for v in verdicts if v.tradeable]
    print(f"{'='*78}\nVERDICT SUMMARY (PO OTC, {args.gran}s)")
    print(f"{'='*78}")
    print(f"tested: {len(verdicts)}   TRADEABLE: {len(tradeable)}   DROP: {len(verdicts)-len(tradeable)}")
    for v in verdicts:
        print(f"  {'KEEP' if v.tradeable else 'drop':4} {v.symbol:14} {v.reason}")
    if not tradeable and verdicts:
        print("\n*** HONEST: no PO OTC pair shows exploitable structure at this TF. ***")


if __name__ == "__main__":
    asyncio.run(main())
