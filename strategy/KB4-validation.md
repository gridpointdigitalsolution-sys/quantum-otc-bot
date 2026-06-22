# KB4 — Strategy Validation: Proving a Win Rate Is REAL, Not Luck or Curve-Fit

Sources: David Aronson, *Evidence-Based Technical Analysis* (statistical significance, data-mining bias, Monte Carlo permutation) · Robert Pardo, *The Evaluation and Optimization of Trading Systems* (walk-forward analysis, degrees of freedom, overfitting).

Purpose: decide whether our 60%+ win-rate target is a genuine edge before risking money. The core principle from both books: **a profitable backtest is consistent with having an edge, but does NOT prove it** (affirming-the-consequent fallacy). You can only prove the edge by failing to disprove the null hypothesis "this strategy has zero expected return / no predictive power" and by confirming performance survives on data the optimizer never saw.

---

## 1. Is the backtested result statistically significant? (Aronson — hypothesis testing)

**The frame.** Assume the null hypothesis H0: the strategy has **zero expected return** (no predictive power; on detrended data a useless rule returns 0). A profitable backtest is "evidence." The question: *could a return this good have happened by pure chance if H0 were true?*

**The p-value** = the fraction of the chance/no-skill distribution that lies at or above your observed return. It is the probability of seeing a result this good (or better) IF the strategy is worthless.
- **Significance threshold: p ≤ 0.05** (scientific convention Aronson uses). Only then reject "it's luck."
- A p-value says nothing about the probability the strategy is good — only how unlikely the evidence is under "no skill." Improbable-under-H0 evidence lets you infer H0 is likely false.

**Win-rate significance (binomial / proportion test) — the actual math for a 60% target:**
- Under "no edge" a directional bet is a coin flip, p₀ = 0.50. Standard error of an observed win proportion = `SE = sqrt(p₀(1-p₀)/N) = sqrt(0.25/N)`.
- Z-score of your result: `Z = (observed_win_rate − 0.50) / SE`. Significant at 5% one-tailed when **Z ≥ 1.645** (≈ 1.96 two-tailed).
- Worked examples for a **60% observed win rate** (0.10 above chance):
  - N=30 → SE=0.091 → Z=1.10 → p≈0.14 → **NOT significant** (could easily be luck).
  - N=70 → SE=0.060 → Z=1.67 → p≈0.047 → **just significant.**
  - N=100 → SE=0.050 → Z=2.00 → p≈0.023 → significant.
  - N=200 → SE=0.035 → Z=2.83 → p≈0.002 → strongly significant.
- Takeaway: a 60% win rate needs **~70+ independent trades minimum** to clear p=0.05, and that's before any data-mining penalty (Section 2). Note: win rate alone is NOT edge for options — weight by payoff (test mean P&L per trade the same way), since a 60% hit rate with negative expectancy still loses.

---

## 2. Data-mining / data-snooping bias (Aronson — the silent killer)

**What it is.** When you test many rules/parameter sets and keep the best one, the winner's backtest performance is **upward-biased** — inflated above its true merit by luck. "Best of 1,000 rules" looks spectacular under a single-rule yardstick yet is often statistically worthless. This is the #1 reason live results collapse vs. backtest (out-of-sample deterioration).

**Why it happens — the bias grows with these 5 factors:**
1. **# of rules/variants tested** ↑ → bias ↑ (more chances to get lucky). *This is the dominant factor — count every variant you ever ran.*
2. **# of observations/trades** ↑ → bias ↓ (more data dilutes luck).
3. **Correlation among the variants tested** — less correlated → bias ↑.
4. **Positive outlier returns present** → bias ↑ (one lucky day inflates the winner; diluted by large N).
5. **Low variation in true merit among variants** (all similarly mediocre) → bias ↑.

**How to correct for it (so the p-value is honest):** the naïve single-rule p-value is invalid after data mining. Use a method that builds the chance distribution of *the best-of-all-rules-tested*:
- **White's Reality Check / bootstrap** — resamples the daily-return histories of ALL tested rules with replacement to get the sampling distribution of the best rule under "no skill," then computes a corrected p-value. (Forecaster's Reality Check software.)
- **Monte Carlo permutation method (Masters)** — see Section 3; run the permutation across the whole rule set and compare the *best* observed rule to the distribution of the *best* noise-rule per permutation.
- Quick conservative fallback (Bonferroni): required single-test significance = 0.05 / (number of rules tested). Test 100 variants → each must clear p ≤ 0.0005. Over-strict but safe.

**Practical defenses:** keep an honest count of every variant tried; prefer few, theory-justified parameters; hold back true out-of-sample data the optimizer never touches (Section 4).

---

## 3. Monte Carlo permutation test (Aronson/Masters) — robustness without distribution assumptions

Tests H0: "the rule's signals are randomly paired with market moves" — i.e. the rule has no real timing skill. Destroys any edge by scrambling, then asks how often noise beats your real result.

**Exact procedure:**
1. Take the **detrended** one-day-forward market price changes over the backtest period.
2. Take the time series of the rule's output signals (+1 long / −1 short / 0 flat) **in original order**.
3. **Randomly permute** (shuffle) the price-change series and pair it with the in-order signal series — sampling **without replacement** (each price change used once). This is a "noise rule."
4. Compute each pairing's return = signal × price-change; average them → one noise-rule mean return.
5. Repeat steps 3–4 a **large number of times, e.g. 5,000** permutations.
6. Form the sampling distribution of those 5,000 noise-rule mean returns.
7. **p-value = fraction of noise-rule returns ≥ your real rule's return.** Significant if p ≤ 0.05.
8. For a data-mined system, permute the whole rule set and compare your best real rule to the distribution of the best noise rule each pass (this folds in the data-mining correction).

Also use Monte Carlo on the **trade sequence** (shuffle trade order / bootstrap the equity curve, e.g. 1,000–5,000 runs) to get a distribution of max drawdown and final equity — confirms the drawdown you'll actually face and that profit isn't dependent on one lucky ordering.

---

## 4. Walk-Forward Analysis (Pardo) — the verdict on overfitting

**Why it's the gold standard:** WFA judges the strategy **exclusively on out-of-sample data the optimizer never saw**, then rolls forward. Pardo: it is "idiot-proof" — very hard to overfit with eyes open. A strategy that fails WFA will not make money live.

**Exact procedure:**
1. Split history into an **in-sample (IS) optimization window** + a following **out-of-sample (OOS) window**.
2. Optimize parameters on the IS window only → pick the best set.
3. Trade that frozen set on the OOS window; **record OOS results only.**
4. Slide both windows forward by one OOS-length; re-optimize on the new IS, test on the new OOS.
5. Repeat across the whole history → stitch all OOS segments into one continuous out-of-sample track record. Run **many** walk-forwards (the more, the more confidence); a strategy can fluke one window but won't fluke many.

**Window sizing rule of thumb:** OOS (trading/step) window = **1/8 to 1/3 of the IS window.**
- e.g. 24-month IS → trade/re-optimize every 3–6 months OOS.
- Larger IS window → longer reliable life between re-optimizations; shorter window → re-optimize more often. Faster/short-term strategies use smaller windows (1–3 yr); slower strategies need larger windows to gather enough trades.

**Walk-Forward Efficiency (WFE) — the headline metric:**
- `WFE = annualized OOS (post-optimization) profit ÷ annualized IS (optimization) profit`.
- **WFE ≥ 50–60% = robust.** WFE > 100% possible (OOS can beat IS). **WFE ≈ 25% or less = overfit or unsound — reject.**
- Also require: a large number of **profitable individual walk-forwards** and significant **total OOS profit**. Watch OOS max drawdown — if it greatly exceeds IS drawdown, trouble.
- After go-live, keep computing real-time WFE; if it diverges sharply from backtest WFE, the edge has decayed — stop and re-evaluate.

---

## 5. How much data / how many trades to be trustworthy

- **Minimum 30 trades** is the classic statistical floor; **prefer 70–100+** for a 60% win-rate claim (Section 1), and more if many parameters or many variants were tested.
- Under 30 trades → extra caution required: strategy must be **theoretically sound**, **robust across a wide parameter range**, and ideally **profitable across multiple markets/underlyings** to compensate for weak statistics.
- **Degrees of freedom (Pardo):** `Rdf% = 100 × [1 − (Used DF / Original DF)]` where used DF ≈ data points consumed by indicators/rules and original DF ≈ sample size.
  - **Target remaining DF ≥ 90%.** A 30-day MA on a 100-day window = 70% → too tight, invalid. A 10-day MA on 1,000 days = 99% → fine.
  - Practical reading: your data sample/trade count must dwarf the lookback lengths and rule count. More optimizable parameters ⇒ you need a proportionally larger history AND trade sample.
- Trades should be **evenly distributed** across the test window, with **low standard deviation** of win/loss size and run length, and consistent quarter-by-quarter and year-by-year — inconsistency signals fragility.

---

## 6. Overfitting red flags & parameter limits (Pardo)

- **Definition:** overfitting = fitting too many parameters for the available data → great IS, poor OOS/live. Mild overfit can still profit; massive overfit loses money live.
- **Fewest parameters possible.** Each added optimizable parameter sharply raises overfit risk. Drop any parameter with little performance impact — fix it to a constant. Pre-screen each parameter one-at-a-time (others held fixed) and only optimize the few that actually move the needle.
- **Profit-spike test (the single biggest visual tell):** a great parameter set surrounded by **poor** neighbors = a fragile statistical outlier → reject. A profitable set surrounded by **similarly profitable neighbors (a plateau)** = robust → keep. Always inspect the whole optimization surface, not just the peak.
- **No overscanning:** step size not too small, range not too large; remember each step is a % change (3→4 days is +33%, but 100→101 is +1%) — use sensible relative steps so you're not mining noise.
- **Red-flag checklist:** spectacular IS but collapsing OOS; WFE ≤ 25%; result sits on an isolated spike; results hinge on one or a few outlier trades/days; more parameters than the data can support (DF < 90%); win rate not significant once # of variants tested is accounted for; profit concentrated in one period or one walk-forward.

---

## 7. GO-LIVE CHECKLIST (run on every candidate before risking money)

1. **Theory first** — the edge has a logical market reason (order flow, vol skew, mean reversion, etc.); never ship a black-box that only "backtests well."
2. **Sample size** — ≥ 70–100 trades for a 60% win-rate claim (≥ 30 absolute floor); enough data that remaining **degrees of freedom ≥ 90%**.
3. **Single-rule significance** — win rate (and mean P&L per trade) clears **p ≤ 0.05** (Z ≥ 1.645) vs. the no-edge baseline.
4. **Honest variant count** — write down every rule/parameter set ever tested; apply the **data-mining correction** (White's Reality Check or permutation-on-the-set, or Bonferroni p ≤ 0.05/N) and re-check significance.
5. **Monte Carlo permutation** — 5,000 shuffles of signals vs. detrended returns; real result must beat noise at **p ≤ 0.05**.
6. **Monte Carlo trade-order / equity bootstrap** — 1,000+ runs; confirm max drawdown is survivable and profit doesn't depend on lucky ordering.
7. **Walk-forward analysis** — many rolling windows, OOS = 1/8–1/3 of IS; judge on stitched OOS only.
8. **WFE ≥ 50–60%**, majority of individual walk-forwards profitable, significant total OOS profit, OOS drawdown ≤ IS drawdown.
9. **Robustness** — profitable parameter sits on a **plateau** (good neighbors), not an isolated spike; ideally holds across multiple underlyings/regimes.
10. **Consistency** — trades evenly spread, low variance of win/loss size & run length, profit not concentrated in one period or a few outlier trades; then size small live and monitor real-time WFE for decay.
