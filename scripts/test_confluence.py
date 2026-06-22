"""Push WR up via AND-gated confluence on the proven Range Break assets.

Sweeps min_votes (2/3) x streak x k x expiry on RB100/RB200, at 3 payouts (0.85/0.90/0.92)
to show sensitivity. Judges DOLLAR PF / DD / edge-vs-breakeven, never raw WR alone.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.config import BotConfig, RiskConfig
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from bot.strategy.confluence import ConfluenceFade

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw")
RESEARCH_CFG = BotConfig(risk=RiskConfig(
    max_trades_per_day=100000, max_daily_loss_pct=1e9, daily_profit_target_pct=1e9,
    stop_after_consec_losses=10**9, cooldown_after_loss_bars=0))

ASSETS = ["RB100", "RB200"]
EXPIRIES = [180, 300]
GRAN = 60
PAYOUTS = [0.85, 0.90, 0.92]

CONFIGS = []
for mv in (2, 3):
    for streak in (3, 4):
        for k in (2.0, 2.5):
            CONFIGS.append((f"v{mv}_s{streak}_k{k}", dict(min_votes=mv, streak=streak, k=k)))

def main():
    rows = []
    for asset in ASSETS:
        path = os.path.join(RAW, f"{asset}_{GRAN}s.csv")
        if not os.path.exists(path):
            print(f"MISSING {path}"); continue
        cs = CandleSeries.from_csv(path, asset, GRAN)
        for exp in EXPIRIES:
            for cname, kw in CONFIGS:
                strat = ConfluenceFade(expiry_sec=exp, **kw)
                r = run_backtest(asset, cs.epoch, cs.open, cs.high, cs.low, cs.close,
                                 GRAN, strat, payout=0.90, cfg=RESEARCH_CFG)
                if r.n_trades < 80:
                    continue
                rows.append((asset, cname, exp, r))

    rows.sort(key=lambda x: x[3].win_rate, reverse=True)
    print(f"\n{'='*108}\nCONFLUENCE FADE on Range Break  (relaxed governor = raw edge)  payout shown 90%")
    print(f"{'asset':8}{'config':14}{'exp':5}{'n':7}{'WR':8}{'be':7}{'edge':8}{'PF':7}{'DD%':7}{'exp$':9}")
    print('='*108)
    for asset, cname, exp, r in rows:
        print(f"{asset:8}{cname:14}{exp:<5}{r.n_trades:<7}{r.win_rate:<8.1%}{r.breakeven_wr:<7.1%}"
              f"{r.edge_vs_breakeven:<+8.1%}{r.dollar_pf:<7.2f}{r.max_drawdown_pct:<7.1f}{r.expectancy:<+9.4f}")

    # payout sensitivity on the single best config
    if rows:
        asset, cname, exp, _ = rows[0]
        kw = dict(CONFIGS[[c[0] for c in CONFIGS].index(cname)][1])
        cs = CandleSeries.from_csv(os.path.join(RAW, f"{asset}_{GRAN}s.csv"), asset, GRAN)
        print(f"\n--- PAYOUT SENSITIVITY: best = {asset} {cname} @{exp}s ---")
        for p in PAYOUTS:
            strat = ConfluenceFade(expiry_sec=exp, **kw)
            r = run_backtest(asset, cs.epoch, cs.open, cs.high, cs.low, cs.close,
                             GRAN, strat, payout=p, cfg=RESEARCH_CFG)
            print(f"  payout={p:.0%} be={r.breakeven_wr:.1%}  WR={r.win_rate:.1%} "
                  f"edge={r.edge_vs_breakeven:+.1%} PF={r.dollar_pf:.2f} DD={r.max_drawdown_pct:.1f}% "
                  f"exp=${r.expectancy:+.4f} -> {'PASS' if r.passes() else 'FAIL'}")

if __name__ == "__main__":
    main()
