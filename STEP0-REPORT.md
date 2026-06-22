# STEP 0 REPORT — Asset Predictability Gate (the make-or-break test)

Run: 2026-06-22. Code: `bot/step0_predictability.py` + `scripts/run_step0.py`.
Data cached: `data/raw/*.csv`. Full JSON: `data/step0/step0_60s.json`.
Tests per asset (close-to-close 1m log returns): autocorrelation, runs (Wald-Wolfowitz),
variance-ratio (Lo-MacKinlay q=2 & q=4, heteroskedasticity-robust), Hurst (R/S).
Verdict rule: TRADEABLE only if >=2 tests reject randomness AND agree on a direction a
setup family can exploit. Multiple-testing correction applied to the headline (below).

## RESULT 1 — Deriv SYNTHETICS (20,000 1m bars each = well-powered) → **FAIL**

| symbol | n | tests rejecting random | direction | raw verdict |
|---|---|---|---|---|
| R_10 | 20k | 0/5 | none | DROP |
| R_25 | 20k | 1/5 | mixed | DROP |
| R_50 | 20k | 2/5 | trend | (raw KEEP) |
| R_75 | 20k | 0/5 | none | DROP |
| R_100 | 20k | 0/5 | none | DROP |
| 1HZ10V | 20k | 0/5 | none | DROP |
| 1HZ50V | 20k | 1/5 | trend | DROP |
| 1HZ100V | 20k | 1/5 | trend | DROP |
| stpRNG | 20k | 0/5 | none | DROP |
| BOOM500 | 20k | 0/5 | none | DROP |
| CRASH500 | 20k | 3/5 | trend | (raw KEEP) |

**Multiple-testing correction (the honest headline).** 11 symbols × ~3 p-value tests = ~33
tests. At alpha=0.05 you EXPECT ~1.6 false rejections by chance; we saw ~2 (R_50, CRASH500)
— consistent with pure noise. Lowest p-value anywhere = CRASH500 VR(q=4) **p=0.0186**.
Bonferroni threshold = 0.05/33 = **0.0015**. **Nothing clears it.** Both "raw KEEP" symbols
read as *trend* (the WRONG family for fixed-payout binary, which structurally needs a high
hit-rate / mean-reversion edge) and are marginal.

→ **VERDICT: Deriv synthetics are statistically random — unbeatable as designed.** Building a
mean-reversion edge on them = curve-fitting noise. **DROPPED.** (Confirms KB7's warning.)
CRASH500's only real asymmetry is its spike structure (KB7: "spike-scalp only, niche") — not
a vanilla CALL/PUT continuation edge. Not pursued.

## RESULT 2 — Deriv REAL-MARKET (forex + gold) → **PASS** (after deep-data refetch)

First pass was UNDERPOWERED: my pagination broke at the weekend gap, returning only ~1.9k
1m bars. Fixed (page backward across closed sessions) -> refetched **60,000 bars** each.
With real power, all four show STRONG, Bonferroni-surviving MEAN-REVERSION:

| symbol | n | reject | key evidence | verdict |
|---|---|---|---|---|
| frxXAUUSD (gold) | 60k | 4/5 | runs p≈0 (z=+7.7); VR(q2) p=0.0019; VR(q4) p=0.0056; lag1=-0.024 | **KEEP** |
| frxEURUSD | 60k | 3/5 | runs p≈0 (z=+6.5); lag1=-0.028 (band 0.008); VR(q2) p=0.033 | **KEEP** |
| frxUSDJPY | 60k | 2/5 | runs p≈0 (z=+13.8); autocorr sig lags 1-5 | **KEEP** |
| frxGBPUSD | 60k | 2/5 | runs p≈0 (z=+6.3); lag1=-0.015 | **KEEP** |

Multiple-testing: these runs/VR p-values are ~0 (z=6-14), orders of magnitude below any
Bonferroni threshold (0.05/20=0.0025). This is REAL structure, not noise. Direction =
mean_revert = the CORRECT family for fixed-payout binary (high hit-rate fade).

**CAVEAT (must be settled by the backtest):** negative 1m autocorr on real forex is partly
the bid-ask-bounce microstructure artifact. It is real in the price series, but whether it
survives the PAYOUT CAP over a full 1m/2m/5m expiry is the open question. So these PASS the
predictability gate and EARN a backtest; the payout-capped backtest is the true arbiter.

## RESULT 3 — Pocket Option OTC (the ACTUAL primary target) → **UNTESTED**

KB7: PO OTC is broker-GENERATED and "possibly more tractable than Deriv synthetics." It is the
user's main universe (92% OTC currency list, PO-target-assets.md). **Cannot fetch PO data
without a live `ssid`** (unofficial WS). Not yet supplied → Step 0 on the real target is BLOCKED.

## BOTTOM LINE / DECISION POINT
- **Deriv synthetics: dead.** Proven noise (well-powered, Bonferroni-clean). Will not be traded.
- **Deriv real-market (gold + EUR/GBP/JPY USD majors): PASS.** Real Bonferroni-surviving
  mean-reversion. These are PROVEN ENOUGH to build S1 + backtest on now. The payout-capped
  backtest decides if the structure is actually monetizable.
- **PO OTC: still UNTESTED** — the user's primary target; needs a live ssid. po_source.py +
  run_step0_po.py are BUILT and ready; paste an ssid to run the identical gate on the OTC pairs.

**Decision (user: "Both, PO first"):** PO needs the ssid (paste when ready). Meanwhile, to not
idle, S1 + the backtest engine are being built on the Step-0-PROVEN Deriv real-market assets,
producing the first REAL payout-capped numbers. The same pipeline runs on PO OTC the instant
the ssid lands. We never build on an asset that failed the gate.
