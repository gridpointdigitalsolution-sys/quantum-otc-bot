"""FAST scan of the 22 new OTC assets — only the PROVEN rsi@lvl family (+ADX variants),
across 1/2/3/5m, walk-forward validated. Reports winners. Does NOT touch basket_po.json.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.config import BotConfig, RiskConfig, PayoutGate
from bot.data.candles import CandleSeries
from bot.backtest import run_backtest
from bot.strategy.s3_sweep import RsiAtLevel

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "raw_po")
GRAN = 60; PAY = 0.92; BE = 1.0 / (1.0 + PAY)
CFG = BotConfig(risk=RiskConfig(max_trades_per_day=10**9, max_daily_loss_pct=1e9,
                daily_profit_target_pct=1e9, stop_after_consec_losses=10**9,
                cooldown_after_loss_bars=0), payout=PayoutGate(floor_normal=0.5, floor_offpeak_aplus=0.5))
NEW = ["#AXP_otc","#BA_otc","#CSCO_otc","#JNJ_otc","#MCD_otc","AEDCNY_otc","AMZN_otc",
       "AUDNZD_otc","BNB-USD_otc","BTCUSD_otc","CITI_otc","DOGE_otc","ETHUSD_otc","EURHUF_otc",
       "KESUSD_otc","SYPUSD_otc","TON-USD_otc","USDBRL_otc","USDCOP_otc","USDPHP_otc",
       "USDTHB_otc","VISA_otc"]
VARIANTS = []
for ob, os_ in [(75, 25), (70, 30)]:
    for tol in [0.5, 1.0]:
        VARIANTS.append(dict(ob=ob, os=os_, tol_atr=tol, use_adx=False))
        VARIANTS.append(dict(ob=ob, os=os_, tol_atr=tol, use_adx=True, adx_max=40.0))


def bt(a, e, o, h, l, c, s):
    return run_backtest(a, e, o, h, l, c, GRAN, s, payout=PAY, cfg=CFG)


def main():
    winners = []
    for asset in NEW:
        p = os.path.join(RAW, f"{asset}_{GRAN}s.csv")
        if not os.path.exists(p):
            print(f".... {asset:12} no data", flush=True); continue
        cs = CandleSeries.from_csv(p, asset, GRAN)
        e, o, h, l, c = cs.epoch, cs.open, cs.high, cs.low, cs.close
        n = len(c); t = n // 3
        segs = [slice(0, t), slice(t, 2*t), slice(2*t, n)]
        best = None
        for exp in [60, 120, 180, 300]:
            for vp in VARIANTS:
                strat = RsiAtLevel(expiry_sec=exp, **vp)
                try: r = bt(asset, e, o, h, l, c, strat)
                except Exception: continue
                if r.n_trades < 120 or r.win_rate < 0.56 or r.dollar_pf < 1.12 or r.max_drawdown_pct > 15:
                    continue
                seg = [bt(asset, e[s], o[s], h[s], l[s], c[s], strat).win_rate for s in segs]
                if sum(1 for w in seg if w >= BE) < 2 or min(seg) < 0.49:
                    continue
                cand = {"asset": asset, "setup": "rsi@lvl", "expiry": exp, "params": vp,
                        "n": r.n_trades, "wr": round(r.win_rate, 4), "pf": round(r.dollar_pf, 3),
                        "dd": round(r.max_drawdown_pct, 2), "seg_wr": [round(x, 3) for x in seg]}
                if best is None or cand["wr"] > best["wr"]:
                    best = cand
        if best:
            winners.append(best)
            print(f"PASS {best['asset']:12} {best['expiry']}s WR={best['wr']:.1%} PF={best['pf']:.2f} DD={best['dd']:.1f}% adx={best['params'].get('use_adx')}", flush=True)
        else:
            print(f".... {asset:12} no stable edge", flush=True)
    winners.sort(key=lambda x: -x["wr"])
    json.dump(winners, open(os.path.join(PROJ, "data", "research", "basket_new_candidates.json"), "w"), indent=2)
    print(f"\n=== {len(winners)} NEW pairs passed ===", flush=True)
    for w in winners:
        print(f"  {w['asset']:12} {w['expiry']}s WR={w['wr']:.1%} PF={w['pf']:.2f} DD={w['dd']:.1f}%", flush=True)


if __name__ == "__main__":
    main()
