"""Deep-fetch ALL Deriv 24/7 synthetic + basket assets -> data/raw cache.

Big one-time pull so the research sweep has enough trades for solid stats. Robust
(reconnect-hardened source). Skips assets already cached at >= target depth.

Run:  python scripts/fetch_all_247.py --bars 100000
"""
import argparse, asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.data.deriv_source import fetch_candles
from bot.data.candles import CandleSeries

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")

ASSETS_247 = [
    # Continuous (volatility) indices
    "R_10","R_25","R_50","R_75","R_100",
    "1HZ10V","1HZ15V","1HZ25V","1HZ30V","1HZ50V","1HZ75V","1HZ90V","1HZ100V",
    # Crash/Boom (user-flagged risky; included for completeness, ranked separately)
    "BOOM300N","BOOM500","BOOM600","BOOM900","BOOM1000","BOOM150N","BOOM50",
    "CRASH300N","CRASH500","CRASH600","CRASH900","CRASH1000","CRASH150N","CRASH50",
    # Daily Reset (drift), Jump (momentum), Range Break (mean-revert), Step
    "RDBULL","RDBEAR","JD10","JD25","JD50","JD75","JD100","RB100","RB200",
    "stpRNG","stpRNG2","stpRNG3","stpRNG4","stpRNG5",
    # Baskets (24/7-ish, real-driven)
    "WLDAUD","WLDEUR","WLDGBP","WLDUSD","WLDXAU",
]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", type=int, default=100000)
    ap.add_argument("--gran", type=int, default=60)
    args = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)
    for i, sym in enumerate(ASSETS_247, 1):
        path = os.path.join(RAW, f"{sym}_{args.gran}s.csv")
        if os.path.exists(path):
            cs = CandleSeries.from_csv(path, sym, args.gran)
            if len(cs) >= args.bars * 0.85:
                print(f"[{i}/{len(ASSETS_247)}] {sym:10} cached {len(cs)} -> skip", flush=True)
                continue
        try:
            cs = await fetch_candles(sym, args.gran, args.bars)
            if len(cs):
                cs.to_csv(path)
            print(f"[{i}/{len(ASSETS_247)}] {sym:10} fetched {len(cs)}", flush=True)
        except Exception as e:
            print(f"[{i}/{len(ASSETS_247)}] {sym:10} FAILED {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
