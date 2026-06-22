# KB5 — Systems & Methods: Reusable Building Blocks
**Sources:** Kaufman *Trading Systems & Methods* (5th ed) · Carver *Systematic Trading* · Clenow *Following the Trend* (2nd ed)
**Purpose:** Concrete indicators, volatility/regime filters, signal-combining, and non-martingale risk sizing for a 1–5 min directional bot.

> Note on timeframe: these books are mostly daily-bar systems. The **math is timeframe-agnostic** — substitute "bar" for "day" and re-fit lookbacks shorter (e.g. ER over 10 bars = 10 of your 1-min bars). Carver explicitly notes the framework works intraday; only volatility annualisation changes (use √(bars/year) instead of √256).

---

## 1. Kaufman Adaptive Indicators (KAMA / Efficiency Ratio)

### Efficiency Ratio (ER) — the core "noise" / regime gauge
ER = |signal| / |noise| over n bars:
```
ER = |P_t − P_{t-n}|  /  Σ |P_i − P_{i-1}|   (i from t-n+1 to t)
```
- Numerator = net directional move; denominator = sum of absolute bar-to-bar changes.
- **ER = 1** → price moved one direction every bar (clean trend). **ER → 0** → choppy/sideways.
- "Fractal efficiency." Noise ≠ volatility: 100 up = ER 1; +100/−100/+100 = same range, ER near 0.
- **Default n = 10** (test 8–10). Keep n < 14 — price rarely runs >14 bars one way; larger n just shrinks ER without adding info.
- **Standalone use as a regime filter:** trade trend/breakout rules only when ER is high (e.g. >0.30–0.40 for our bot); switch to mean-reversion or stand aside when ER is low. This is the single most reusable Kaufman idea.

### KAMA (Kaufman's Adaptive Moving Average)
An EMA whose smoothing constant changes each bar based on ER:
```
KAMA_t = KAMA_{t-1} + sc_t × (P_t − KAMA_{t-1})
sc_t   = [ ER_t × (fastest − slowest) + slowest ]²
fastest = 2/(N_fast+1)   slowest = 2/(N_slow+1)
```
- **Defaults:** N_fast = 2, N_slow = 30, ER period = 10. Squaring sc means slow end ≈ 900-bar trend (line stalls in noise); fast end ≈ 4–5 bar EMA in clean trends.
- TradeStation default expansion (ER=10, fast=2→0.6667, slow=30→0.0645):
  ```
  KAMA = KAMA[1] + (( |C-C[10]| / Σ|C-C[1]|over10 *0.6022) + 0.0645)² * (C - KAMA[1])
  ```
- **Trade rule:** go with KAMA slope direction (long when it turns up). Add a small filter so trivial penetrations don't flip the trend — e.g. require change ≥ **0.1 × stdev of KAMA changes**. Leave slow bound at 30; raise fast bound above 2 to desensitise.
- Same ER-driven adaptive trick applies to **Adaptive RSI** and **Adaptive Stochastic** (vary the lookback by ER) — makes oscillators faster in trends, slower in chop.

### Parabolic SAR (adaptive trailing stop, reusable for exits)
```
SAR_t = SAR_{t-1} + AF_t × (EP − SAR_{t-1})
```
EP = extreme point (highest high since entry for longs). AF starts 0.02, +0.02 on each new extreme, **capped 0.20**. Constraint: SAR may never be inside the last 2 bars' range. Good cheap volatility-aware trailing exit.

---

## 2. Volatility Measures, Filters & Regime Detection

### True Range / ATR (the workhorse)
```
TR_t = max(High_t, Close_{t-1}) − min(Low_t, Close_{t-1})
ATR  = moving average of TR   (Clenow uses EMA; smoothing method "matters very little")
```
- ATR = expected size of a normal bar. Two jobs: **(a) position sizing** (§5), **(b) normalising everything to volatility** so thresholds are comparable across instruments/regimes.

### Volatility-standardised distance (Clenow pullback / Carver vol-adjust)
Any price distance should be divided by volatility before you threshold it:
```
units = (Price − Reference) / ATR        (or / stdev of price changes)
```
- Clenow counter-trend entry: long in a bull market when `(highest_close_20 − close)/ATR ≥ 3` (price 3 ATR below the 20-bar high). Threshold in **ATR units is portable**; raw $ or % is not.
- Carver's EWMAC divides the MA crossover by the stdev of price changes (price points, not %) before scaling.

### Std-dev vs ATR
- ATR: range-based, simplest, good enough. Std-dev: compute on **daily/bar returns, never on price levels**. Either works for sizing; pick one and stay consistent.

### Regime detection (what filter to use when)
1. **ER (Kaufman)** — best trend-vs-chop classifier. High ER → trend rules; low ER → fade or flat.
2. **Trend filter (Clenow):** EMA50 > EMA100 = bullish regime → only take longs; reverse for shorts. Cheap directional gate. Adding a trend filter to a raw breakout materially cuts whipsaw losses.
3. **Volatility band (rule-of-thumb, appears across all 3):** skip trades when current ATR is far outside its own recent average (both abnormally low — about to jump — and abnormally high — panic). Carver warns low-vol periods precede vol spikes + reversals; size off entry-time ATR only.

---

## 3. Oscillators — construction + thresholds that actually work

### RSI (Wilder)
```
RS = AvgUp / AvgDown   (avg of up-closes / avg of down-closes over n, as positives)
RSI = 100 − 100/(1+RS)
```
- Wilder smoothing (average-off): `AvgUp_t = AvgUp_{t-1} + (max(P_t−P_{t-1},0) − AvgUp_{t-1})/n`, same for down.
- **Default n = 14** (half a ~monthly cycle). Thresholds **30 / 70**. For more frequent signals shorten n; 30/70 hold because the 0–100 scale self-normalises.
- RSI is *dampened*, rarely tags 70/30 — fewer but cleaner extremes than stochastic.

### Stochastic %K / %D
```
%K = 100 × (Close − Lowest_Low_n) / (Highest_High_n − Lowest_Low_n)
%D = 3-bar SMA of %K   (%D-slow = 3-bar SMA of %D)
```
- Thresholds **80 / 20** (or 70/30). Stochastic moves faster, exaggerates swings, often tags 90/10.
- **What actually works:** don't trade raw %K (unstable). Use %D crossing its signal line (%D-slow) *after* penetrating an extreme, like MACD. Lane's high-probability pattern = **Failure**: after crossing out of an extreme, price pulls back to the signal line but fails to re-cross → confirmation of reversal.
- Adaptive stochastic: vary n by ER (slowend/fastend like KAMA).

### Williams A/D Oscillator (volatility-self-normalising, useful intraday)
```
BP = High − Open ;  SP = Close − Low
DRF = (BP + SP) / (2 × (High − Low))    → ranges 0..1
```
- Denominator is the bar range → auto-adjusts to volatility, so overbought/oversold bands (80/20, or 70/30 if smoothed ~0.30 EMA) stay stable over time. Good for short bars where ATR-normalising matters.

### General oscillator rule
Bands are **not predictive on their own** — they say "stretched," not "reversing." Use them as a *secondary timing/confirmation* layer on top of a trend/regime gate, not as the primary entry.

---

## 4. Combining Signals — Carver's Forecast Framework (the key reusable architecture)

Decouple **direction-and-conviction** (forecast) from **sizing** (§5). A forecast is a number proportional to expected risk-adjusted return (≈ expected Sharpe).

### Step 1 — scale every rule to a common unit
- Standardise each rule so its **expected absolute value ≈ 10**. (+10 = average buy, −10 = average sell, +5 weak, −20 strong.)
- `forecast_scalar = 10 / (natural average abs value of the raw rule)`. Compute the scalar on **price/structure data, not P&L**, to avoid overfitting.
- **Cap every forecast to [−20, +20].** Reasons: risk control, thin data at extremes, mean-reversion at extremes (dead-cat bounce), and low-vol-inflated forecasts that precede spikes. A raw +25 → +20.

### Step 2 — example rule (EWMAC trend, intraday-portable)
```
raw = EWMA_fast − EWMA_slow          EWMA decay A = 2/(L+1); recursive E_t = A·P_t + (1−A)·E_{t-1}
vol_adj = raw / stdev(price changes in price points)
forecast = forecast_scalar × vol_adj    (then cap ±20)
```
- Use **fast:slow ratio = 4** (2:8, 4:16, 8:32, 16:64…). Forecast scalars: 2,8→10.6 · 4,16→7.5 · 8,32→5.3 · 16,64→3.75 · 32,128→2.65 · 64,256→1.87.
- Adjacent pairs correlate ~0.90; **prune any variation pair correlating >0.95** (no added diversification).

### Step 3 — combine multiple rules into one forecast
```
combined = Σ (weight_i × forecast_i) × FDM
```
- Weights sum to 1; set by hand (start equal) or bootstrap. Don't pick weights by raw backtest Sharpe (overfits).
- Averaging less-than-correlated forecasts shrinks the range below 10 → restore it with the **Forecast Diversification Multiplier (FDM)**.
- **FDM = 10 / (natural combined-forecast volatility)**. Rule-of-thumb table (assets × avg correlation):

  | #rules | ρ=0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
  |---|---|---|---|---|---|
  | 2 | 1.41 | 1.27 | 1.15 | 1.10 | 1.0 |
  | 3 | 1.73 | 1.41 | 1.22 | 1.12 | 1.0 |
  | 4 | 2.0 | 1.51 | 1.27 | 1.10 | 1.0 |
  | 5 | 2.2 | 1.58 | 1.29 | 1.15 | 1.0 |

- **Floor all correlations at 0** before using them (negative correlations → dangerously large multipliers).

---

## 5. Position Sizing & Risk Targeting (NO martingale)

### Core principle
Size purely off **(volatility, forecast strength, capital)** — never off account size inside the trading rule, never increase size after losses. This is the structural opposite of martingale.

### Clenow ATR risk-parity (simplest, drop-in)
```
contracts = (Equity × RiskFactor) / (ATR × PointValue)     → round DOWN
```
- `RiskFactor` ≈ **0.0015–0.002 (15–20 bps)** target daily impact per position. Each position is engineered to move the book ~that % on a normal day, so volatile and quiet instruments contribute equally. Size fixed at entry; scale whole strategy by tuning one number.

### Carver volatility-scalar chain (more general; works for one bot too)
```
1. percentage_vol_target  → cash_vol_target = capital × %target
   daily_cash_vol = annual_cash_vol / 16        (√256; intraday use √bars-per-year)
2. instrument_currency_vol = block_value × price_vol_%      (block_value = P&L per 1% move)
   instrument_value_vol     = instrument_currency_vol × FX
3. volatility_scalar = daily_cash_vol_target / instrument_value_vol   (= position at forecast +10)
4. position = volatility_scalar × forecast / 10
```
- Position scales **linearly with forecast** (forecast −20 → 2× short; +5 → half long). Doubling price vol halves position. Don't round intermediates; round only final contracts.
- **Position inertia:** skip re-trades when the target position changes <10% — cuts churn/costs.

### Risk-of-ruin / how much to risk (the non-negotiable part)
- **Set % vol target = your expected Sharpe** (Kelly-optimal). SR 0.5 → 50% target.
- **Then HALVE it (Half-Kelly).** Full Kelly at SR 0.5 = 10% chance of losing half your capital over 10 yrs.
- **Haircut the backtest Sharpe first:** multiply backtested SR by **0.75** (even with clean out-of-sample bootstrap) before plugging into Kelly; cap expected SR at **1.0** no matter how good the backtest. Carver runs a 35-yr SR≈1.0 system at only **37% target**, not 100%.
- 10-yr ruin table (SR 0.5, zero skew): 25% target → <1% chance of losing half; 50% → 10%; 100% → 40%; 200% → 93%. **Stay ≤25–37%.**
- **Negative-skew strategies (most option-selling / mean-reversion): run at HALF again** — they show great backtest SR then blow up; penalty for over-betting is far worse with negative skew.
- **Leverage sanity check:** no single position should be wiped out by the largest conceivable move (CHF 2015 = 16% gap → only ≤7× leverage survived). Diversify so one instrument is a small slice.

---

## 6. Avoiding Over-Optimization (Carver + Kaufman)

- **Cause:** picking the rule/variation that best fits past data; narrative fallacy makes overfit rules feel "explainable." Overfit → great backtest, poor live.
- **Data-first vs ideas-first:** "ideas first" (form hypothesis, then test once) overfits far less than mining data for what worked. If you must fit, fit **explicitly and once**, on a fitting window, then test untouched out-of-sample (or expanding-window walk-forward — fit only on past data each step).
- **Fit on structure, not P&L:** forecast scalars, FDM, vol estimates are all derived from price-distribution data, never from returns — so they can't be tuned to flatter the curve.
- **Diversify instead of optimise:** more rules + more instruments (low correlation) raises the realistic ceiling; prune variations correlating >0.95 (no benefit).
- **Expect a haircut:** apply 0.75× to backtest SR; never believe SR>1.0. Realised performance is "never as good as backtest." Future returns likely lower than history.
- **Avoid over-trading:** keep cost ≤ ~0.13 SR/yr; use position inertia (no re-trade <10%); slower rules if costs bite. The other two cardinal sins alongside over-fitting are over-trading and over-betting (§5).

---

## 10-LINE SUMMARY — most useful building blocks for our bot
1. **Efficiency Ratio (ER, n≈10)** = `|net move| / Σ|bar moves|` → primary trend-vs-chop regime gate; only run directional/breakout logic when ER > ~0.3–0.4.
2. **KAMA** = ER-driven adaptive EMA (`sc=[ER·(0.667−0.0645)+0.0645]²`, fast2/slow30) — trades on slope, with a 0.1-stdev filter to ignore noise penetrations.
3. **ATR** (`TR = max(H,C₋₁) − min(L,C₋₁)`, EMA-smoothed) is the universal volatility unit — normalise every distance/threshold to ATR units so they're portable across regimes.
4. **Clenow ATR sizing:** `contracts = Equity × 0.0015–0.002 / (ATR × pointvalue)`, round down — equal-risk, fixed at entry, no add-on-loss (anti-martingale).
5. **Carver forecast scaling:** standardise each signal to expected |value|=10, **cap ±20**; size **linearly** with forecast (`position = vol_scalar × forecast/10`).
6. **Combine signals** as a weighted average × **FDM** (≈1.1–1.4 for 2–4 lowly-correlated rules; floor correlations at 0); prune any pair correlating >0.95.
7. **RSI(14) 30/70** and **Stochastic %K/%D 20/80** as *confirmation* layers, not primary entries — use the cross-out-of-extreme + "failure" retest, not the band touch alone.
8. **Risk target = Half-Kelly:** %vol-target = (0.75 × backtest SR, capped at 1.0) ÷ 2; keep ≤25–37%; halve again for negative-skew/option-selling strategies.
9. **Regime layering that works:** EMA50>EMA100 directional gate + ER trend filter + ATR vol-band (skip abnormal-vol bars) before any entry — kills most whipsaw.
10. **Anti-overfit discipline:** ideas-first, fit once out-of-sample, derive scalars from price structure (not P&L), diversify rather than optimise, apply a 0.75 SR haircut, never trust SR>1.0.
