"""(1) Test S10/S11 trend setups on all PO pairs. (2) Walk-forward the leading candidates:
split each pair's month into 3 equal time segments, run the SAME fixed strategy on each.
A real edge holds in ALL segments; a curve-fit shows in only one. No re-optimization.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.config import BotConfig, RiskConfig, PayoutGate
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from bot.strategy.s4_trend import MacdTripleGate, SuperTrendEma
from bot.strategy.s3_sweep import RsiAtLevel

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw_po")
GRAN = 60; PAYOUT = 0.92; BE = 1.0 / (1.0 + PAYOUT)
CFG = BotConfig(risk=RiskConfig(max_trades_per_day=100000, max_daily_loss_pct=1e9,
                daily_profit_target_pct=1e9, stop_after_consec_losses=10**9,
                cooldown_after_loss_bars=0),
                payout=PayoutGate(floor_normal=0.80, floor_offpeak_aplus=0.80))


def bt(asset, cs, strat, sl=None):
    e, o, h, l, c = cs.epoch, cs.open, cs.high, cs.low, cs.close
    if sl:
        e, o, h, l, c = (x[sl] for x in (e, o, h, l, c))
    return run_backtest(asset, e, o, h, l, c, GRAN, strat, payout=PAYOUT, cfg=CFG)


def main():
    files = sorted(f for f in os.listdir(RAW) if f.endswith(f"_{GRAN}s.csv"))
    series = {f.replace(f"_{GRAN}s.csv", ""): CandleSeries.from_csv(os.path.join(RAW, f),
              f.replace(f"_{GRAN}s.csv", ""), GRAN) for f in files}

    # ---- (1) trend setups sweep ----
    rows = []
    for asset, cs in series.items():
        if len(cs) < 5000:
            continue
        for exp in [120, 180, 300]:
            for name, strat in [("macd_triple", MacdTripleGate(expiry_sec=exp)),
                                ("supertrend", SuperTrendEma(expiry_sec=exp))]:
                try:
                    r = bt(asset, cs, strat)
                except Exception:
                    continue
                if r.n_trades >= 80:
                    rows.append((asset, name, exp, r.n_trades, r.win_rate, r.dollar_pf, r.max_drawdown_pct))
    rows.sort(key=lambda x: -x[4])
    print(f"\n=== S10/S11 TREND SETUPS (PO, payout 92%, be {BE:.1%}) — top 12 ===")
    for a, s, e, n, wr, pf, dd in rows[:12]:
        print(f"{a:14}{s:14}{e:<5}n={n:<6}WR={wr:.1%} edge={wr-BE:+.1%} PF={pf:.2f} DD={dd:.1f}%")

    # ---- (2) walk-forward the leading reversion candidates ----
    print(f"\n=== WALK-FORWARD (3 time segments, fixed params) — does edge persist? ===")
    cands = [("NGNUSD_otc", RsiAtLevel, dict(expiry_sec=300, tol_atr=0.5)),
             ("BHDCNY_otc", RsiAtLevel, dict(expiry_sec=300, tol_atr=0.5)),
             ("USDCAD_otc", RsiAtLevel, dict(expiry_sec=120, tol_atr=0.5)),
             ("USDPKR_otc", RsiAtLevel, dict(expiry_sec=180, ob=68, os=32, tol_atr=1.0))]
    for asset, cls, kw in cands:
        cs = series.get(asset)
        if not cs:
            print(f"{asset}: no data"); continue
        n = len(cs); third = n // 3
        segs = [slice(0, third), slice(third, 2 * third), slice(2 * third, n)]
        full = bt(asset, cs, cls(**kw))
        line = f"{asset:12} FULL WR={full.win_rate:.1%} PF={full.dollar_pf:.2f} n={full.n_trades} | segs:"
        ok = 0
        for s in segs:
            r = bt(asset, cs, cls(**kw), sl=s)
            mark = "+" if r.win_rate >= BE else "-"
            if r.win_rate >= BE:
                ok += 1
            line += f" [{mark}WR={r.win_rate:.0%} PF={r.dollar_pf:.2f} n={r.n_trades}]"
        line += f"  => {ok}/3 segments above breakeven"
        print(line)


if __name__ == "__main__":
    main()
