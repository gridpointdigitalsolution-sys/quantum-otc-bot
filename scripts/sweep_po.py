"""SWEEP on Pocket Option real-market OTC data (data/raw_po/).

Full strategy battery x all cached PO pairs x 1/2/3/5m at REAL payout 0.92.
Judges DOLLAR PF / DD / edge-vs-breakeven (be=52.1% at 92%). Relaxed governor = raw edge.
Then re-ranks; survivors go to Step 0 + validation.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.config import BotConfig, RiskConfig, PayoutGate
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from scripts.research_sweep import strategy_battery, EXPIRIES

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw_po")
OUT = os.path.join(PROJ, "data", "research")

# relaxed governor + payout gate floor lowered so 92% trades aren't blocked
RESEARCH_CFG = BotConfig(
    risk=RiskConfig(max_trades_per_day=100000, max_daily_loss_pct=1e9,
                    daily_profit_target_pct=1e9, stop_after_consec_losses=10**9,
                    cooldown_after_loss_bars=0),
    payout=PayoutGate(floor_normal=0.80, floor_offpeak_aplus=0.80))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payout", type=float, default=0.92)
    ap.add_argument("--gran", type=int, default=60)
    ap.add_argument("--minn", type=int, default=150)
    ap.add_argument("--minwr", type=float, default=0.55)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    be = 1.0 / (1.0 + args.payout)

    files = sorted(f for f in os.listdir(RAW) if f.endswith(f"_{args.gran}s.csv"))
    rows = []
    for f in files:
        asset = f.replace(f"_{args.gran}s.csv", "")
        cs = CandleSeries.from_csv(os.path.join(RAW, f), asset, args.gran)
        if len(cs) < 5000:
            continue
        for exp in EXPIRIES:
            for sname, strat in strategy_battery(exp):
                try:
                    r = run_backtest(asset, cs.epoch, cs.open, cs.high, cs.low, cs.close,
                                     args.gran, strat, payout=args.payout, cfg=RESEARCH_CFG)
                except Exception:
                    continue
                rows.append({"asset": asset, "strategy": sname, "expiry": exp,
                             "n": r.n_trades, "wr": round(r.win_rate, 4),
                             "edge": round(r.win_rate - be, 4), "pf": round(r.dollar_pf, 3),
                             "dd": round(r.max_drawdown_pct, 2),
                             "exp_usd": round(r.expectancy, 4), "ret": round(r.return_pct, 2)})

    with open(os.path.join(OUT, "sweep_po.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)

    winners = [r for r in rows if r["n"] >= args.minn and r["wr"] >= args.minwr and r["pf"] >= 1.10]
    winners.sort(key=lambda r: (r["wr"], r["pf"]), reverse=True)

    print(f"\n{'='*104}\nPOCKET OPTION SWEEP  payout={args.payout:.0%}  breakeven={be:.1%}  (real-market OTC)")
    print(f"configs={len(rows)}  winners(WR>={args.minwr:.0%},n>={args.minn},PF>=1.10)={len(winners)}\n{'='*104}")
    print(f"{'asset':16}{'strategy':20}{'exp':5}{'n':7}{'WR':8}{'edge':8}{'PF':7}{'DD%':7}{'exp$':9}")
    for w in winners[:50]:
        print(f"{w['asset']:16}{w['strategy']:20}{w['expiry']:<5}{w['n']:<7}{w['wr']:<8.1%}"
              f"{w['edge']:<+8.1%}{w['pf']:<7.2f}{w['dd']:<7.1f}{w['exp_usd']:<+9.4f}")
    pairs = sorted({w["asset"] for w in winners})
    print(f"\nDistinct pairs with a winner: {len(pairs)} -> {pairs}")
    print(f"results -> {os.path.join(OUT, 'sweep_po.json')}")


if __name__ == "__main__":
    main()
