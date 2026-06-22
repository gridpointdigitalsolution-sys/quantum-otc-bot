"""RESEARCH SWEEP — battery of strategies x ALL 24/7 assets x 1/2/3/5m.

Measures the RAW strategy edge with a relaxed risk governor (so sample size reflects the
strategy, not the daily caps). Ranks by win rate + dollar PF. Winners then get the real
governor + payout sweep + validation in the next stage.

Run:  python scripts/research_sweep.py --payout 0.90 --minwr 0.58
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import BotConfig, RiskConfig
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from bot.strategy.s1_bollinger import S1Bollinger
from bot.strategy.s2_rsi import S2RSI
from bot.strategy.fade import FadeStreak, FadeExtreme
from bot.strategy.momentum import MomentumFollow, DriftBias
from scripts.fetch_all_247 import ASSETS_247

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")
OUT = os.path.join(PROJ, "data", "research")

# relaxed governor: measure the STRATEGY edge on full sample (risk overlay applied later)
RESEARCH_CFG = BotConfig(risk=RiskConfig(
    max_trades_per_day=100000, max_daily_loss_pct=1e9, daily_profit_target_pct=1e9,
    stop_after_consec_losses=10**9, cooldown_after_loss_bars=0))

EXPIRIES = [60, 120, 180, 300]


def strategy_battery(exp):
    """All strategy configs to test at a given expiry."""
    return [
        ("S1_bb20", S1Bollinger(expiry_sec=exp, bb_n=20, bb_mult=2.0)),
        ("S1_bb14", S1Bollinger(expiry_sec=exp, bb_n=14, bb_mult=2.0)),
        ("fade_streak2", FadeStreak(expiry_sec=exp, streak=2)),
        ("fade_streak3", FadeStreak(expiry_sec=exp, streak=3)),
        ("fade_streak4", FadeStreak(expiry_sec=exp, streak=4)),
        ("fade_streak3_noadx", FadeStreak(expiry_sec=exp, streak=3, use_adx=False)),
        ("fade_ext2.0", FadeExtreme(expiry_sec=exp, k=2.0)),
        ("fade_ext2.5", FadeExtreme(expiry_sec=exp, k=2.5)),
        ("s2_rsi_bb", S2RSI(expiry_sec=exp, use_bb=True)),
        ("s2_rsi", S2RSI(expiry_sec=exp, use_bb=False)),
        ("mom_follow", MomentumFollow(expiry_sec=exp)),
        ("drift_down", DriftBias(expiry_sec=exp, bias="down")),
        ("drift_up", DriftBias(expiry_sec=exp, bias="up")),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payout", type=float, default=0.90)
    ap.add_argument("--gran", type=int, default=60)
    ap.add_argument("--minwr", type=float, default=0.58)
    ap.add_argument("--minn", type=int, default=150)
    ap.add_argument("--assets", type=str, default="")
    args = ap.parse_args()

    assets = args.assets.split(",") if args.assets else ASSETS_247
    os.makedirs(OUT, exist_ok=True)
    rows = []
    risky = {"BOOM", "CRASH"}

    for asset in assets:
        path = os.path.join(RAW, f"{asset}_{args.gran}s.csv")
        if not os.path.exists(path):
            continue
        cs = CandleSeries.from_csv(path, asset, args.gran)
        if len(cs) < 5000:
            continue
        is_risky = any(asset.startswith(p) for p in risky)
        for exp in EXPIRIES:
            for sname, strat in strategy_battery(exp):
                try:
                    r = run_backtest(asset, cs.epoch, cs.open, cs.high, cs.low, cs.close,
                                     args.gran, strat, payout=args.payout, cfg=RESEARCH_CFG)
                except Exception as e:
                    continue
                rows.append({
                    "asset": asset, "risky": is_risky, "strategy": sname,
                    "expiry": exp, "payout": args.payout, "n": r.n_trades,
                    "wr": round(r.win_rate, 4), "be": round(r.breakeven_wr, 4),
                    "edge": round(r.edge_vs_breakeven, 4), "pf": round(r.dollar_pf, 3),
                    "dd": round(r.max_drawdown_pct, 2), "exp_usd": round(r.expectancy, 4),
                    "ret": round(r.return_pct, 2),
                })

    with open(os.path.join(OUT, f"sweep_{int(args.payout*100)}.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    # rank winners: enough sample, WR threshold, positive PF
    winners = [r for r in rows if r["n"] >= args.minn and r["wr"] >= args.minwr and r["pf"] >= 1.15]
    winners.sort(key=lambda r: (r["wr"], r["pf"]), reverse=True)
    safe = [w for w in winners if not w["risky"]]

    print(f"\n{'='*100}\nRESEARCH SWEEP  payout={args.payout:.0%}  (relaxed governor = raw strategy edge)")
    print(f"configs={len(rows)}  winners(WR>={args.minwr:.0%},n>={args.minn},PF>=1.15)={len(winners)}  "
          f"SAFE(non-Boom/Crash)={len(safe)}\n{'='*100}")
    print(f"\n--- TOP 40 SAFE (non-Boom/Crash) ---")
    print(f"{'asset':10}{'strategy':20}{'exp':5}{'n':7}{'WR':8}{'edge':8}{'PF':7}{'DD%':7}{'ret%':8}")
    for w in safe[:40]:
        print(f"{w['asset']:10}{w['strategy']:20}{w['expiry']:<5}{w['n']:<7}{w['wr']:<8.1%}"
              f"{w['edge']:<+8.1%}{w['pf']:<7.2f}{w['dd']:<7.1f}{w['ret']:<8.1f}")
    print(f"\n--- TOP 15 RISKY (Boom/Crash — reported, user-flagged) ---")
    for w in [x for x in winners if x['risky']][:15]:
        print(f"{w['asset']:10}{w['strategy']:20}{w['expiry']:<5}{w['n']:<7}{w['wr']:<8.1%}"
              f"{w['edge']:<+8.1%}{w['pf']:<7.2f}{w['dd']:<7.1f}{w['ret']:<8.1f}")

    # distinct safe assets that produced >=1 winner
    sa = sorted({w["asset"] for w in safe})
    print(f"\nSAFE assets with a 60%+ winner: {len(sa)} -> {sa}")
    print(f"results -> {os.path.join(OUT, f'sweep_{int(args.payout*100)}.json')}")


if __name__ == "__main__":
    main()
