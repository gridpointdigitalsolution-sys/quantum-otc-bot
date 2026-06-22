"""Re-validate the 5 basket pairs WITH the new ADX trend-avoidance + dead-candle filters.
Per pair: try baseline vs filter variants, walk-forward each, keep the BEST (highest WR with
2/3 segments above breakeven, n>=100). Filter is adopted ONLY if it helps. Writes basket_po.json
with FULL params so the live engine reproduces it exactly.
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
GRAN = 60; PAY = 0.92; BE = 1.0 / (1.0 + PAY)
CFG = BotConfig(risk=RiskConfig(max_trades_per_day=10**9, max_daily_loss_pct=1e9,
                daily_profit_target_pct=1e9, stop_after_consec_losses=10**9,
                cooldown_after_loss_bars=0), payout=PayoutGate(floor_normal=0.5, floor_offpeak_aplus=0.5))

# base config per pair (expiry + the proven ob/os/tol)
BASE = {
    "NGNUSD_otc": dict(expiry=300, ob=75, os=25, tol_atr=0.5),
    "BHDCNY_otc": dict(expiry=300, ob=75, os=25, tol_atr=1.0),
    "OMRCNY_otc": dict(expiry=180, ob=75, os=25, tol_atr=1.0),
    "NZDJPY_otc": dict(expiry=180, ob=75, os=25, tol_atr=1.0),
    "USDCAD_otc": dict(expiry=120, ob=75, os=25, tol_atr=0.5),
}
# filter variants to try (added on top of base)
VARIANTS = [
    ("baseline", dict(use_adx=False, min_range_atr=0.0)),
    ("adx40", dict(use_adx=True, adx_max=40.0, min_range_atr=0.0)),
    ("adx35", dict(use_adx=True, adx_max=35.0, min_range_atr=0.0)),
    ("mr0.3", dict(use_adx=False, min_range_atr=0.3)),
    ("adx40+mr", dict(use_adx=True, adx_max=40.0, min_range_atr=0.3)),
    ("adx35+mr", dict(use_adx=True, adx_max=35.0, min_range_atr=0.3)),
]


def bt(asset, e, o, h, l, c, strat):
    return run_backtest(asset, e, o, h, l, c, GRAN, strat, payout=PAY, cfg=CFG)


def main():
    basket = []
    for asset, base in BASE.items():
        cs = CandleSeries.from_csv(os.path.join(RAW, f"{asset}_{GRAN}s.csv"), asset, GRAN)
        e, o, h, l, c = cs.epoch, cs.open, cs.high, cs.low, cs.close
        n = len(c); third = n // 3
        segs = [slice(0, third), slice(third, 2*third), slice(2*third, n)]
        exp = base["expiry"]
        sp = {k: base[k] for k in ("ob", "os", "tol_atr")}
        best = None
        print(f"\n{asset}:")
        for vname, vparams in VARIANTS:
            params = {**sp, **vparams}
            strat = RsiAtLevel(expiry_sec=exp, **params)
            r = bt(asset, e, o, h, l, c, strat)
            if r.n_trades < 100:
                print(f"  {vname:10} n={r.n_trades} (too few)"); continue
            seg = [bt(asset, e[s], o[s], h[s], l[s], c[s], strat).win_rate for s in segs]
            ok = sum(1 for w in seg if w >= BE)
            tag = "PASS" if (ok >= 2 and min(seg) >= 0.49) else "fail-wf"
            print(f"  {vname:10} WR={r.win_rate:.1%} PF={r.dollar_pf:.2f} DD={r.max_drawdown_pct:.1f}% n={r.n_trades} segs={[round(x,2) for x in seg]} {tag}")
            if tag != "PASS":
                continue
            cand = {"asset": asset, "setup": "rsi@lvl", "expiry": exp,
                    "params": params, "n": r.n_trades, "wr": round(r.win_rate, 4),
                    "pf": round(r.dollar_pf, 3), "dd": round(r.max_drawdown_pct, 2),
                    "exp_usd": round(r.expectancy, 4), "variant": vname,
                    "seg_wr": [round(x, 3) for x in seg]}
            # prefer higher WR; require filter to BEAT baseline by >=0.3% to adopt (else keep baseline)
            if best is None or cand["wr"] > best["wr"] + (0.0 if cand["variant"] == "baseline" else 0.003):
                if best is None or cand["wr"] > best["wr"]:
                    best = cand
        if best:
            basket.append(best)
            print(f"  -> CHOSEN {best['variant']} WR={best['wr']:.1%} params={best['params']}")
    basket.sort(key=lambda x: -x["wr"])
    json.dump(basket, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nwrote {len(basket)} pairs -> {OUT}")
    for b in basket:
        print(f"  {b['asset']:12} {b['expiry']}s {b['variant']:10} WR={b['wr']:.1%} PF={b['pf']:.2f} DD={b['dd']:.1f}%")


if __name__ == "__main__":
    main()
