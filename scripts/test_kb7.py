"""Test the KB7 high-confidence selective setups (S3 sweep + S/R-gated RSI + confluence)
on all cached PO OTC pairs, at real 92% payout. Selectivity = the WR lever."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.config import BotConfig, RiskConfig, PayoutGate
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from bot.strategy.s3_sweep import SweepReversal, RsiAtLevel
from bot.strategy.confluence import ConfluenceFade

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw_po")
GRAN = 60
PAYOUT = 0.92
BE = 1.0 / (1.0 + PAYOUT)
CFG = BotConfig(risk=RiskConfig(max_trades_per_day=100000, max_daily_loss_pct=1e9,
                daily_profit_target_pct=1e9, stop_after_consec_losses=10**9,
                cooldown_after_loss_bars=0),
                payout=PayoutGate(floor_normal=0.80, floor_offpeak_aplus=0.80))
EXPIRIES = [60, 120, 180, 300]


def battery(exp):
    return [
        ("sweep_lb8", SweepReversal(expiry_sec=exp, lookback=8)),
        ("sweep_lb6", SweepReversal(expiry_sec=exp, lookback=6)),
        ("sweep_lb10", SweepReversal(expiry_sec=exp, lookback=10)),
        ("rsi@lvl_t0.5", RsiAtLevel(expiry_sec=exp, tol_atr=0.5)),
        ("rsi@lvl_t1.0", RsiAtLevel(expiry_sec=exp, tol_atr=1.0)),
        ("rsi@lvl_6822", RsiAtLevel(expiry_sec=exp, ob=68, os=32, tol_atr=1.0)),
        ("conf_v2", ConfluenceFade(expiry_sec=exp, min_votes=2, use_adx=True)),
    ]


def main():
    files = sorted(f for f in os.listdir(RAW) if f.endswith(f"_{GRAN}s.csv"))
    rows = []
    for f in files:
        asset = f.replace(f"_{GRAN}s.csv", "")
        cs = CandleSeries.from_csv(os.path.join(RAW, f), asset, GRAN)
        if len(cs) < 5000:
            continue
        for exp in EXPIRIES:
            for sname, strat in battery(exp):
                try:
                    r = run_backtest(asset, cs.epoch, cs.open, cs.high, cs.low, cs.close,
                                     GRAN, strat, payout=PAYOUT, cfg=CFG)
                except Exception:
                    continue
                rows.append((asset, sname, exp, r.n_trades, r.win_rate, r.dollar_pf,
                             r.max_drawdown_pct, r.expectancy))

    # rank by WR among decent samples
    good = [x for x in rows if x[3] >= 100]
    good.sort(key=lambda x: -x[4])
    print(f"\n{'='*100}\nKB7 SELECTIVE SETUPS on PO OTC  payout=92%  breakeven={BE:.1%}")
    print(f"{'asset':15}{'setup':14}{'exp':5}{'n':7}{'WR':8}{'edge':8}{'PF':7}{'DD%':7}{'exp$':9}")
    print('='*100)
    for a, s, e, n, wr, pf, dd, ex in good[:35]:
        print(f"{a:15}{s:14}{e:<5}{n:<7}{wr:<8.1%}{wr-BE:<+8.1%}{pf:<7.2f}{dd:<7.1f}{ex:<+9.4f}")
    # pairs with a real edge: WR>=57, PF>=1.2, n>=120
    strong = [x for x in good if x[4] >= 0.57 and x[5] >= 1.2 and x[3] >= 120]
    sp = sorted({x[0] for x in strong})
    print(f"\nSTRONG (WR>=57%, PF>=1.2, n>=120): {len(strong)} configs on {len(sp)} pairs -> {sp}")


if __name__ == "__main__":
    main()
