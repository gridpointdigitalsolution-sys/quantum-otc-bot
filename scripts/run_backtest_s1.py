"""Backtest S1 (Bollinger reversion) on Step-0-PROVEN assets, across 1m/2m/5m + payouts.

Signal computed on 1m candles; expiry = hold N base bars (60s->1, 120s->2, 300s->5).
Payout-capped, realistic fills, full risk governor. Judge by DOLLAR PF / DD / expectancy.

Run:  python scripts/run_backtest_s1.py
      python scripts/run_backtest_s1.py --assets frxXAUUSD,frxEURUSD --payouts 0.92,0.90,0.85
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import CONFIG
from bot.data.candles import CandleSeries
from bot.strategy.s1_bollinger import S1Bollinger
from bot.backtest import run_backtest

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")
OUT = os.path.join(PROJ, "data", "backtest")

# proven by Step 0 (deep data, Bonferroni-clean mean-reversion)
PROVEN = ["frxXAUUSD", "frxEURUSD", "frxUSDJPY", "frxGBPUSD"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", type=str, default=",".join(PROVEN))
    ap.add_argument("--payouts", type=str, default="0.92,0.90,0.85,0.80")
    ap.add_argument("--gran", type=int, default=60)
    ap.add_argument("--bbn", type=int, default=20)
    ap.add_argument("--bbmult", type=float, default=2.0)
    args = ap.parse_args()

    assets = args.assets.split(",")
    payouts = [float(x) for x in args.payouts.split(",")]
    expiries = list(CONFIG.expiries_sec)  # 60,120,300
    os.makedirs(OUT, exist_ok=True)

    print(f"\n{'='*96}\nS1 BOLLINGER REVERSION BACKTEST  (BB({args.bbn},{args.bbmult}), 1m signal)")
    print(f"assets={assets}  expiries={expiries}s  payouts={payouts}")
    print(f"{'='*96}\n")

    all_results = []
    for asset in assets:
        path = os.path.join(RAW, f"{asset}_{args.gran}s.csv")
        if not os.path.exists(path):
            print(f"{asset}: no cached candles ({path}) -> run Step 0 fetch first. SKIP.")
            continue
        cs = CandleSeries.from_csv(path, asset, args.gran)
        print(f"--- {asset}  ({len(cs)} candles) ---")
        for payout in payouts:
            for exp in expiries:
                strat = S1Bollinger(expiry_sec=exp, bb_n=args.bbn, bb_mult=args.bbmult)
                r = run_backtest(asset, cs.epoch, cs.open, cs.high, cs.low, cs.close,
                                 args.gran, strat, payout=payout)
                all_results.append(r)
                print("   " + r.summary_line())
        print()

    # save (without heavy equity/trades for the index file)
    idx = [{k: v for k, v in r.__dict__.items() if k not in ("equity_curve", "trades")}
           for r in all_results]
    with open(os.path.join(OUT, "s1_results.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))

    passes = [r for r in all_results if r.passes()]
    print(f"{'='*96}\nHEADLINE PASS BAR (pre-validation): edge>=+3%, PF>=1.10, DD<=25%, n>=100")
    print(f"{'='*96}")
    print(f"configs tested: {len(all_results)}   PASS: {len(passes)}")
    for r in sorted(passes, key=lambda x: -x.dollar_pf):
        print("  " + r.summary_line())
    if not passes:
        print("\n*** NO S1 config clears the headline bar. Best by PF: ***")
        for r in sorted(all_results, key=lambda x: -x.dollar_pf)[:5]:
            print("  " + r.summary_line())
    print(f"\nresults -> {os.path.join(OUT, 's1_results.json')}")


if __name__ == "__main__":
    main()
