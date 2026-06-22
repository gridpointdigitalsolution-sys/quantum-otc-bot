# BACKTEST REPORT — S1 Bollinger Reversion + Autocorr Ceiling Probe

Run 2026-06-22. Engine: `bot/backtest.py` (payout-capped, next-open entry, exact-expiry
settle, full risk governor, structural anti-martingale). Data: 60k 1m bars/asset, Deriv
real-market (the only assets that PASSED Step 0). Judge = DOLLAR PF / DD / expectancy.

## S1 RESULT — FAIL (0 of 48 configs pass)
4 assets x 3 expiries (1/2/5m) x 4 payouts (92/90/85/80%). Headline bar: edge>=+3% over
break-even, PF>=1.10, DD<=25%, n>=100. **PASS = 0.**
- Trade counts tiny (n=4..87): S1 is selective + 5-trades/day governor -> 60k bars (~41
  forex days) yields too few events to conclude. Best raw: gold 300s PF 1.52 but n=15 = noise.
- 80% payout -> 0 trades (correctly blocked by the >=85% gate). Gate works.

## CEILING PROBE — the decisive test (FAIL)
Raw directional accuracy of "fade the last bar" on EVERY bar (n~55k, statistically solid):

| asset | best fade acc (any hold) | break-even @90% | monetizable? |
|---|---|---|---|
| frxXAUUSD | 51.5% | 52.63% | NO (below) |
| frxUSDJPY | 49.8% | 52.63% | NO |
| frxGBPUSD | 49.3% | 52.63% | NO |
| frxEURUSD | 49.0% | 52.63% | NO |

Even the strongest Step-0 asset's UPPER-BOUND accuracy is below break-even. 3/4 are below
50% (fading doesn't win directionally once you settle open[i+1]->close[i+H]).

## CONCLUSION (honest)
**Predictability != profitability.** Step 0's mean-reversion is statistically real but only
~a few bps — too small to clear the binary payout cap at 1-5m once realistic settlement +
embedded spread are applied. A selective subset cannot turn a sub-break-even ceiling into a
shippable edge without curve-fitting.

-> **Deriv real-market forex/gold: NOT shippable for binary. Dropped (for binary).**
-> **Deriv synthetics: already dropped (random).**
-> **Pocket Option OTC: the user's real target, a DIFFERENT broker-generated feed, still
   UNTESTED — needs a live ssid.** All code (po_source, run_step0_po, S1, backtest, probe)
   is built and runs on PO data unchanged the moment an ssid is supplied.

## WHAT WOULD CHANGE THE VERDICT
1. PO OTC feed shows real, monetizable structure (broker-generated feeds sometimes do).
2. A sub-minute regime (5-10s) on a feed with a stronger short-horizon edge (separate research).
Neither is assumed. The backtest decides. So far, nothing on Deriv clears the bar — stated plainly.
