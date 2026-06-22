"""Lock the EXACT winning params per pair and write basket_po.json (with params) so the live
engine rebuilds the identical strategy that the backtest validated. Re-sweeps the rsi@lvl grid
for the 5 walk-forward survivors at their winning expiry, picks best by WR with 2/3 walk-forward,
stores full params + segment WRs.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.config import BotConfig, RiskConfig, PayoutGate
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from bot.strategy.s3_sweep import RsiAtLevel

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw_po")
OUT = os.path.join(PROJ, "data", "research", "basket_po.json")
GRAN = 60; PAYOUT = 0.92; BE = 1.0 / (1.0 + PAYOUT)
CFG = BotConfig(risk=RiskConfig(max_trades_per_day=100000, max_daily_loss_pct=1e9,
                daily_profit_target_pct=1e9, stop_after_consec_losses=10**9,
                cooldown_after_loss_bars=0),
                payout=PayoutGate(floor_normal=0.80, floor_offpeak_aplus=0.80))

# survivors -> (winning expiry from optimizer)
WINNERS = {"BHDCNY_otc": 300, "NGNUSD_otc": 300, "OMRCNY_otc": 180,
           "NZDJPY_otc": 180, "USDCAD_otc": 120}
GRID = [dict(ob=ob, os=os_, tol_atr=tol)
        for ob, os_ in [(70, 30), (75, 25), (68, 32), (80, 20)]
        for tol in [0.5, 1.0, 1.6]]


def bt(asset, e, o, h, l, c, strat):
    return run_backtest(asset, e, o, h, l, c, GRAN, strat, payout=PAYOUT, cfg=CFG)


def main():
    basket = []
    for asset, exp in WINNERS.items():
        cs = CandleSeries.from_csv(os.path.join(RAW, f"{asset}_{GRAN}s.csv"), asset, GRAN)
        e, o, h, l, c = cs.epoch, cs.open, cs.high, cs.low, cs.close
        n = len(c); third = n // 3
        segs = [slice(0, third), slice(third, 2*third), slice(2*third, n)]
        best = None
        for params in GRID:
            strat = RsiAtLevel(expiry_sec=exp, **params)
            r = bt(asset, e, o, h, l, c, strat)
            if r.n_trades < 120:
                continue
            seg_wr = []
            for s in segs:
                seg_wr.append(bt(asset, e[s], o[s], h[s], l[s], c[s], strat).win_rate)
            ok = sum(1 for w in seg_wr if w >= BE)
            if ok < 2 or min(seg_wr) < 0.49:
                continue
            cand = {"asset": asset, "setup": "rsi@lvl", "expiry": exp, "params": params,
                    "n": r.n_trades, "wr": round(r.win_rate, 4), "pf": round(r.dollar_pf, 3),
                    "dd": round(r.max_drawdown_pct, 2), "exp_usd": round(r.expectancy, 4),
                    "seg_wr": [round(x, 3) for x in seg_wr]}
            if best is None or cand["wr"] > best["wr"]:
                best = cand
        if best:
            basket.append(best)
            print(f"LOCK {asset:12} exp={best['expiry']}s params={best['params']} "
                  f"WR={best['wr']:.1%} PF={best['pf']:.2f} DD={best['dd']:.1f}% segs={best['seg_wr']}")
    basket.sort(key=lambda x: -x["wr"])
    json.dump(basket, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nwrote {len(basket)} pairs WITH params -> {OUT}")


if __name__ == "__main__":
    main()
