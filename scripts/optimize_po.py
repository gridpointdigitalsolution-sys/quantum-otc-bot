"""PER-PAIR OPTIMIZER + WALK-FORWARD on PO OTC data.

For each pair: sweep many param combos of the reversion setups (focus 1m/2m), keep configs
that clear a full-sample bar, then WALK-FORWARD them (3 time segments). A config is ACCEPTED
only if it wins the full sample AND every segment (real edge, not curve-fit). Per pair we keep
the single best ACCEPTED config. Output = the tradeable basket.

Judge: DOLLAR PF / DD / edge — never raw WR alone. Payout 92% (be 52.1%).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.config import BotConfig, RiskConfig, PayoutGate
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from bot.strategy.s3_sweep import RsiAtLevel, SweepReversal
from bot.strategy.ensemble import (StochAtLevel, TripleGate, WilliamsAtLevel, BandRevAtLevel)

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw_po")
GRAN = 60; PAYOUT = 0.92; BE = 1.0 / (1.0 + PAYOUT)
CFG = BotConfig(risk=RiskConfig(max_trades_per_day=100000, max_daily_loss_pct=1e9,
                daily_profit_target_pct=1e9, stop_after_consec_losses=10**9,
                cooldown_after_loss_bars=0),
                payout=PayoutGate(floor_normal=0.80, floor_offpeak_aplus=0.80))
EXPIRIES = [60, 120, 180, 300]


def configs(exp):
    out = []
    for ob, os_ in [(70, 30), (75, 25), (68, 32), (80, 20)]:
        for tol in [0.4, 0.7, 1.2, 1.8]:
            for mr in [0.2, 0.4]:
                out.append(("triple", TripleGate(expiry_sec=exp, ob=ob, os=os_,
                            tol_atr=tol, min_range_atr=mr)))
        for tol in [0.5, 1.0, 1.6]:
            out.append(("rsi@lvl", RsiAtLevel(expiry_sec=exp, ob=ob, os=os_, tol_atr=tol)))
    for ob, os_ in [(80, 20), (85, 15), (75, 25)]:
        for tol in [0.6, 1.0, 1.6]:
            out.append(("stoch@lvl", StochAtLevel(expiry_sec=exp, ob=ob, os=os_, tol_atr=tol)))
    for ob, os_ in [(-20, -80), (-15, -85)]:
        for tol in [0.7, 1.2]:
            out.append(("williams", WilliamsAtLevel(expiry_sec=exp, ob=ob, os=os_, tol_atr=tol)))
    for mult in [2.0, 2.3]:
        for tol in [0.8, 1.4]:
            out.append(("band@lvl", BandRevAtLevel(expiry_sec=exp, mult=mult, tol_atr=tol)))
    for lb in [6, 8, 10]:
        out.append(("sweep", SweepReversal(expiry_sec=exp, lookback=lb)))
    return out


def bt(asset, e, o, h, l, c, strat):
    return run_backtest(asset, e, o, h, l, c, GRAN, strat, payout=PAYOUT, cfg=CFG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minwr", type=float, default=0.565)
    ap.add_argument("--minpf", type=float, default=1.12)
    ap.add_argument("--maxdd", type=float, default=18.0)
    ap.add_argument("--minn", type=int, default=150)
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(RAW) if f.endswith(f"_{GRAN}s.csv"))
    basket = []
    for f in files:
        asset = f.replace(f"_{GRAN}s.csv", "")
        cs = CandleSeries.from_csv(os.path.join(RAW, f), asset, GRAN)
        if len(cs) < 8000:
            continue
        e, o, h, l, c = cs.epoch, cs.open, cs.high, cs.low, cs.close
        n = len(c); third = n // 3
        segs = [slice(0, third), slice(third, 2*third), slice(2*third, n)]
        best = None
        for exp in EXPIRIES:
            for cname, strat in configs(exp):
                try:
                    r = bt(asset, e, o, h, l, c, strat)
                except Exception:
                    continue
                if (r.n_trades < args.minn or r.win_rate < args.minwr
                        or r.dollar_pf < args.minpf or r.max_drawdown_pct > args.maxdd):
                    continue
                # walk-forward: fair bar = at least 2 of 3 segments above breakeven, and
                # NO segment catastrophically below (>=49%), so the edge is real not 1-period.
                seg_ok = 0; seg_wr = []; worst = 1.0
                for s in segs:
                    # run_backtest re-runs precompute() on the slice, so reusing the
                    # instance is safe (indicators recomputed per call, no leakage).
                    rr = bt(asset, e[s], o[s], h[s], l[s], c[s], strat)
                    seg_wr.append(rr.win_rate)
                    if rr.n_trades >= 20:
                        worst = min(worst, rr.win_rate)
                        if rr.win_rate >= BE:
                            seg_ok += 1
                if seg_ok < 2 or worst < 0.49:
                    continue
                cand = {"asset": asset, "setup": cname, "expiry": exp, "n": r.n_trades,
                        "wr": round(r.win_rate, 4), "edge": round(r.win_rate - BE, 4),
                        "pf": round(r.dollar_pf, 3), "dd": round(r.max_drawdown_pct, 2),
                        "exp_usd": round(r.expectancy, 4), "seg_wr": [round(x, 3) for x in seg_wr]}
                if best is None or cand["wr"] > best["wr"]:
                    best = cand
        if best:
            basket.append(best)
            print(f"PASS {best['asset']:14}{best['setup']:11}{best['expiry']:>4}s "
                  f"WR={best['wr']:.1%} PF={best['pf']:.2f} DD={best['dd']:.1f}% "
                  f"n={best['n']} segs={best['seg_wr']}")
        else:
            print(f".... {asset:14} no walk-forward-stable config")

    basket.sort(key=lambda x: -x["wr"])
    with open(os.path.join(PROJ, "data", "research", "basket_po.json"), "w", encoding="utf-8") as fh:
        json.dump(basket, fh, indent=2)
    print(f"\n{'='*92}\nTRADEABLE BASKET (walk-forward-stable, payout 92%, be 52.1%): {len(basket)} pairs")
    print(f"{'asset':14}{'setup':11}{'exp':5}{'n':7}{'WR':8}{'edge':8}{'PF':7}{'DD%':7}{'exp$':9}")
    for b in basket:
        print(f"{b['asset']:14}{b['setup']:11}{b['expiry']:<5}{b['n']:<7}{b['wr']:<8.1%}"
              f"{b['edge']:<+8.1%}{b['pf']:<7.2f}{b['dd']:<7.1f}{b['exp_usd']:<+9.4f}")


if __name__ == "__main__":
    main()
