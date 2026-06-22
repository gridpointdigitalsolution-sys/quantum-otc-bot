"""DECISIVE DIAGNOSTIC — is the Step-0 mean-reversion MONETIZABLE after the payout cap?

Step 0 found negative 1-bar autocorrelation (mean-reversion) on these assets. This probe
measures the CEILING: the raw directional accuracy of the simplest possible exploit, on
EVERY bar (max sample, no selectivity, no governor) so the number is statistically solid.

For each asset and hold H (1,2,5 bars = 1m/2m/5m):
  FADE  : signal = opposite of last bar's move; win if settle moves our way.
  FOLLOW: signal = same as last bar's move.
Settlement = realistic: enter at open[i+1], settle at close[i+H]. Binary win rule.
Compare accuracy to break-even WR at 90% and 85% payout.

If FADE accuracy < break-even (52.6% @90%) at solid n, the autocorr edge is NOT
monetizable at binary payouts -> say so plainly. No tuning rescues a sub-breakeven ceiling.
"""
import argparse
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.data.candles import CandleSeries

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")
PROVEN = ["frxXAUUSD", "frxEURUSD", "frxUSDJPY", "frxGBPUSD"]


def directional_accuracy(o, c, hold, fade=True):
    """Over all valid bars: predict next-H direction from last bar's move. Return (n, acc)."""
    n = len(c)
    wins = 0
    total = 0
    for i in range(1, n - hold - 1):
        move = c[i] - c[i - 1]
        if move == 0:
            continue
        # signal direction
        if fade:
            call = move < 0   # last bar down -> expect bounce up -> CALL
        else:
            call = move > 0
        strike = o[i + 1]
        settle = c[i + 1 + hold - 1]
        if settle == strike:
            total += 1
            continue  # tie = loss
        win = (settle > strike) if call else (settle < strike)
        wins += int(win)
        total += 1
    return total, (wins / total if total else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", type=str, default=",".join(PROVEN))
    ap.add_argument("--gran", type=int, default=60)
    args = ap.parse_args()

    print(f"\n{'='*88}\nAUTOCORR EDGE CEILING PROBE (raw fade/follow, every bar)")
    print(f"break-even: 90% payout -> 52.63% | 85% -> 54.05%")
    print(f"{'='*88}\n")
    print(f"{'asset':12} {'hold':5} {'mode':6} {'n':7} {'acc':8} "
          f"{'edge@90%':9} {'edge@85%':9} verdict")
    for asset in args.assets.split(","):
        path = os.path.join(RAW, f"{asset}_{args.gran}s.csv")
        if not os.path.exists(path):
            print(f"{asset}: no data, skip")
            continue
        cs = CandleSeries.from_csv(path, asset, args.gran)
        o, c = cs.open, cs.close
        for hold in (1, 2, 5):
            for fade in (True, False):
                nt, acc = directional_accuracy(o, c, hold, fade)
                e90 = acc - 0.5263
                e85 = acc - 0.5405
                verdict = "MONETIZABLE" if e90 > 0.01 else ("marginal" if e90 > 0 else "no edge")
                print(f"{asset:12} {hold:5} {'fade' if fade else 'follow':6} {nt:7d} "
                      f"{acc:7.3%} {e90:+8.3%} {e85:+8.3%}  {verdict}")
        print()
    print("Note: accuracy here is the UPPER BOUND (every bar, no selectivity). A real")
    print("strategy trades a SUBSET; it can beat this only if its filter concentrates the")
    print("edge. If even the raw ceiling is sub-break-even, the asset is not monetizable.")


if __name__ == "__main__":
    main()
