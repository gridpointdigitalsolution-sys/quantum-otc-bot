# KB3 — Quant Mean-Reversion Math (Chan: *Algorithmic Trading* + *Machine Trading*)

Statistical core for predicting short-term (1–5 min) direction on mean-reverting / OTC-style series.
Source: Ernest P. Chan, *Algorithmic Trading* (2013) Ch.2–3,8 and *Machine Trading* (2016) Ch.3–4.
Everything below is codeable. Formulas + thresholds + parameter values only.

---

## 1. Is the series mean-reverting? (regime detection)

A price series is **mean-reverting ⇔ stationary**. Three independent tests; run all three, require agreement.

### 1.1 ADF test (Augmented Dickey-Fuller) — the primary test
Fit the linear model:
```
Δy(t) = λ·y(t-1) + μ + β·t + α₁·Δy(t-1) + … + αₖ·Δy(t-k) + ε(t)
```
- `Δy(t) = y(t) − y(t-1)`
- Regress Δy(t) (dependent) on y(t-1) (independent) → coefficient **λ**.
- **Test statistic = λ / SE(λ)** (a t-stat).
- Null hypothesis: λ = 0 (random walk). Reject if the stat is **more negative** than the critical value.
- Critical values (depend on sample size): **1% = −3.46, 5% = −2.87, 10% = −2.59**.
- **Practical params:** set drift `β = 0` (intraday drift ≪ noise), keep offset `μ ≠ 0` (mean is rarely zero), lag **k = 1** (k=0 often fails; price changes have serial correlation).
- λ MUST be negative for mean reversion. If λ > 0 → series trends → do NOT trade mean-reversion on it.
- Use **midprices**, not trade prices, to avoid phantom bid-ask-bounce mean reversion that can't actually be traded.

### 1.2 AR(1) coefficient — equivalent fast check
```
Y(t) − μ = φ·(Y(t-1) − μ) + ε(t)
```
- `|φ| < 1` → stationary / mean-reverting.  `φ = 1` → random walk.  `|φ| > 1` → trending.
- Smaller φ (further below 1) = stronger/faster mean reversion.
- Estimate φ via OLS or MLE (ARIMA(1,0,0)). Example: AUD.USD 1-min midprice → φ = 0.99997 ⇒ technically stationary but ~random walk (too weak to trade).
- For AR(p), pick lag p by **minimizing BIC** (penalizes complexity; brute-force search lags 1..60).

### 1.3 Hurst exponent (H) — degree of mean reversion
Diffusion of log-prices `z = log(y)`:
```
Var(τ) = ⟨ |z(t+τ) − z(t)|² ⟩  ∝  τ^(2H)
```
- **H = 0.5** → geometric random walk.
- **H < 0.5** → mean-reverting (the smaller, the stronger; H→0 = strongly reverting).
- **H > 0.5** → trending (H→1 = strongly trending).
- H is a continuous **regime indicator**: compute H on a rolling window → switch the bot ON (mean-revert mode) only while H < ~0.45.

### 1.4 Variance Ratio test — significance for H
Tests whether `Var(z(t)−z(t−τ)) / [τ · Var(z(t)−z(t−1))] = 1` (i.e. H = 0.5).
- Output: `h = 1` → reject random-walk null (series is stationary); `h = 0` → can't reject.
- `pValue` = probability the random-walk null is true.

**Key caveat:** these tests are *demanding* (need ≥90% certainty), but you can profit at much lower certainty — use the **half-life** as the practical go/no-go instead.

---

## 2. Half-life of mean reversion — the master parameter

Drop drift + lagged terms from the ADF model → Ornstein-Uhlenbeck SDE:
```
dy(t) = (λ·y(t-1) + μ)·dt + dε
E[y(t)] = y₀·exp(λt) − (μ/λ)·(1 − exp(λt))
```
Price decays exponentially toward `−μ/λ` with:

```
half-life = −log(2) / λ        (λ from the same Δy vs y(t-1) regression)
```

- λ < 0 required. λ ≈ 0 → half-life enormous → not tradeable (too few round trips).
- **Half-life sets every lookback in the strategy.** Use `lookback = round(half-life)` for the moving average and moving std — and as the natural holding period. This avoids brute-force optimizing the lookback (less data-snooping).
- Rule: don't use a 5-bar MA when half-life is 20 bars. Set lookback = a small multiple of the half-life.

---

## 3. Entry / exit signals (z-score)

### 3.1 z-score
```
zScore(t) = ( price(t) − MA(price, lookback) ) / STD(price, lookback)
```
with `lookback = half-life`. MA/STD are **moving** (mean drifts slowly; even a stationary series with 0<H<0.5 has time-growing variance).

### 3.2 Linear (parameterless) strategy — for validation, not live
Hold units **negatively proportional** to the z-score:
```
units(t) = − zScore(t)        (or  −(price − MA)/STD )
```
Virtually parameter-free → minimal data-snooping bias. Downside: unbounded capital (no cap on deviation) — use to *prove* the edge exists, not to trade.

### 3.3 Bollinger-band strategy — for live trading
Enter when |z| exceeds `entryZscore`, exit at `exitZscore` (with `exitZscore < entryZscore`):
```
longEntry  :  zScore < −entryZscore     // price cheap → buy
longExit   :  zScore >= −exitZscore
shortEntry :  zScore >  entryZscore      // price rich → sell
shortExit  :  zScore <=  exitZscore
```
- Chan's working example: **entryZscore = 1, exitZscore = 0** (exit at the mean) → on GLD-USO: APR 17.8%, Sharpe 0.96 (vs much weaker linear version).
- `exitZscore = 0` → exit at mean. `exitZscore = −entryZscore` → flip to opposite side.
- Hold 0 or ±1 unit at a time → trivial capital allocation & risk control.
- **Shorter lookback + smaller entry/exit z** → shorter holding, more round-trips, generally higher profit (good for 1–5 min bars). Tune entryZscore on a training set only.

### 3.4 Kalman-filter variant — adaptive, fewer free params
Treat the **mean (moving average) as a hidden state** instead of a fixed-lookback MA:
```
State:        x(t) = x(t-1) + B·u(t)          (hidden mean random-walks)
Measurement:  y(t) = x(t) + D·ε(t)            (observed price = mean + noise)
```
- Replaces the fixed lookback entirely → the filter self-adapts the mean/spread bar-by-bar.
- B, D estimated by MLE on training data. **Danger:** B (noise covariance) is easy to overfit — keep it diagonal/minimal, few params.
- In *Algorithmic Trading* Ch.3 the Kalman filter dynamically estimates the hedge ratio (slope) + spread mean for a cointegrated pair, then the spread z-score drives entries. Useful when the "fair value" itself drifts (OTC-style synthetic series).

---

## 4. ML for short-term direction (Chan, *Machine Trading* Ch.4)

Setup that consistently worked: **predict next-bar return sign from past returns at multiple lookbacks.**
Predictors for SPY next-day return: `ret1, ret2, ret5, ret20` (1/2/5/20-bar past returns). Adapt lookbacks to your bar size.

### 4.1 Stepwise regression — best simple model
- Start from linear regression, then **auto feature-selection**: add predictors one at a time while goodness-of-fit improves (criterion: SSE / **AIC** / **BIC**), then remove one at a time. Stop when no improvement.
- Result on SPY: plain multiple regression overfit (in-sample Sharpe 1.4 → out-of-sample 0.1). Stepwise picked **only `ret2`** (coef negative = mean-revert from 2-bar return) → OOS CAGR 0.4%→10.6%, Sharpe 0.1→0.7. **Fewer predictors = less overfit.**
- Trade rule: long if predicted return > 0, short if < 0; or only act when |predicted| > threshold; or size ∝ |predicted return|.

### 4.2 Regression / classification tree
- Recursively split on the best predictor (minimize child-node variance / MSE). Each leaf = a set of inequalities = a ready-made trade rule (e.g. "ret2 < 1.53% AND ret1 < −1.39% → buy"). Use only extreme leaves (highest +ve / most −ve expected return).
- **Overfit control:** `MinLeafSize = 100` (large leaves), `MinParentSize`, `MaxNumSplits`. Using ALL leaves boosted in-sample to 73% CAGR but OOS to −7.2% (textbook overfit).

### 4.3 Overfit-reduction stack (apply to ALL models)
1. **Train/test split** — always hold out the **second half** as test (chronological, never random for the final OOS check).
2. **K-fold cross-validation** — split training set into K (e.g. **K=5**) folds; train on K−1, validate on held-out fold; keep the model with best cross-validation accuracy (lowest MSE/loss). Lets you safely use all leaves.
3. **Bagging** — resample training set with replacement, train many models, average predictions.
4. **Random subspace** — sample the *predictors* per model.
5. **Random forest** — bagging + random subspace (trees only).
6. **Boosting** — sequentially focus models on prior prediction errors.

### 4.4 Hard ML cautions
- Financial data are **non-stationary** (return distribution drifts) → models that worked in one period fail forward. Retrain by appending the latest bar to the training set.
- More **predictors help** these methods — fundamentals add uncorrelated signal vs technicals.
- Prefer the **simplest model that holds OOS** (stepwise/single-predictor) over complex nets.

---

## 5. Position sizing — Kelly (use HALF)

Gaussian-return optimal leverage:
```
f = m / s²
```
- `m` = mean excess return, `s²` = variance of excess returns (same period units).
- f = leverage that **maximizes compounded growth** (reinvested profits).

Multi-strategy / portfolio allocation:
```
F = C⁻¹ · M
```
- `F` = vector of optimal leverages, `C` = covariance matrix of strategy returns, `M` = vector of mean excess returns.

**Why half-Kelly:** estimation error in m and s² is unavoidable; overestimating m or underestimating s² → over-leverage → **ruin (equity→0)**. Underestimating → merely slower growth. So:
- Deploy **f/2 (half-Kelly)** as standard practice.
- Treat full Kelly as an **upper bound**, never a target — full Kelly often exceeds broker max leverage or would have produced a −100% drawdown in backtest under real (fat-tailed) returns.
- Better still: numerically optimize growth on the **empirical** (non-Gaussian) return distribution rather than the Gaussian f.

---

## 6. Validation / avoiding data-snooping & look-ahead

- **Test the series first, the strategy second.** ADF / Variance-Ratio / half-life use *every bar* → far higher statistical significance than a backtest (which yields few round-trips). A series that passes stationarity (or has a short half-life) guarantees *some* profitable strategy exists, even if your specific one fails.
- **Look-ahead bias:** using in-sample data to compute half-life → lookback is a real source of bias Chan flags explicitly. Compute parameters only on the training set; freeze them for OOS.
- **Train on first half, test on untouched second half** (chronological). For ML, additionally K-fold CV *inside* the training set.
- **Minimize free parameters:** prefer the linear/parameterless mean-revert and the half-life-derived lookback over brute-force-optimized parameters.
- **Use midprices** (not last-trade) to kill phantom bid-ask-bounce reversion.
- Beware non-stationarity: even a "passing" series can stop reverting; retrain / re-test rolling.

---

## 10-line summary — directly usable math for a 1-min direction bot

1. **Regime gate:** compute rolling **Hurst H**; trade mean-reversion only while **H < ~0.45** (H≈0.5 = random walk, skip).
2. **Confirm with ADF:** regress `Δy(t)` on `y(t-1)`, lag k=1, β=0 → need **λ/SE(λ) < −2.87** (5%) and **λ < 0**.
3. **Half-life = −log(2)/λ** → this single number sets the MA/STD lookback and the expected hold time.
4. **Signal:** `zScore = (price − MA(lookback)) / STD(lookback)` on **midprices**, lookback = round(half-life).
5. **Entry/exit:** long when `z < −1`, short when `z > +1`, exit at `z = 0` (entryZscore=1, exitZscore=0); shrink z & lookback for more 1-min round-trips.
6. **Adaptive option:** Kalman filter the mean (`x(t)=x(t-1)+Bu`, `y=x+Dε`) so the fair-value drifts — keep B diagonal/minimal.
7. **ML edge:** stepwise regression on past returns `ret1,ret2,ret5,…`; expect a **negative `ret2` coef** (mean-revert) → trade sign of predicted return.
8. **Overfit guard:** large leaves (`MinLeafSize≈100`), **K=5 cross-validation**, train on first half / test untouched second half, retrain rolling.
9. **Size with half-Kelly:** `f = m/s²`, deploy **f/2**; full Kelly = upper bound only (ruin risk from estimation error).
10. **Validate the series before the strategy** (tests use every bar = higher significance); freeze all params on training data to kill look-ahead bias.
