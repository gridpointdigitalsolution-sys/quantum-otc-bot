# KB6 — Volatility, Probability & No-Martingale Risk Sizing

Sources: Natenberg *Option Volatility & Pricing* / Cofnas (probability-of-touch, delta-as-probability) · Sinclair *Positional Option Trading* (EWMA/GARCH, edge, Kelly) · Van Tharp *Trade Your Way to Financial Freedom* (expectancy, R-multiples, position sizing).

Purpose: give the binary bot a defensible way to (a) turn a short-horizon volatility estimate into the probability price is above/below a level after 1–5 minutes, and (b) size each fixed-payout bet so it survives and compounds **without ever increasing size after a loss**.

---

## PART A — VOLATILITY → PROBABILITY (the engine of the entry filter)

### 1. The square-root-of-time rule (Natenberg)

Volatility is quoted **annualized** (a "20% stock" moves ±20% over a year, one standard deviation). To use it over minutes you must rescale, because volatility grows with the **square root of time**, not linearly:

```
σ(horizon) = σ_annual × √(t / T)
```

- `T` = periods per year for the chosen sampling unit.
- For **1-minute bars**: a 24/5 FX/synthetic market ≈ **N ≈ 525,600 minutes/year** (use the venue's actual trading minutes; for a 24/7 synthetic index it's literally 60×24×365 = 525,600).
- Equivalent daily form: `σ_daily = σ_annual / √252` (252 trading days). Then `σ_per_min = σ_daily / √(minutes per session)`.

**One-standard-deviation move over the horizon, in price terms:**

```
1σ move ($) = Price × σ_per_min × √(minutes ahead)
```

So if 1-min σ = 0.04% and you look 4 minutes ahead, the expected ±1σ band = `Price × 0.0004 × √4 = Price × 0.0008` (±0.08%). ~68% of outcomes land inside that band.

### 2. From the band to a probability (the normal-distribution logic)

Natenberg/Cofnas treat the underlying as roughly lognormal → log-returns roughly **normal**. Probability of being above/below a level is just the normal CDF of the standardized distance:

```
z = (Target − Price) / (Price × σ_per_min × √minutes)
P(price > Target) = 1 − Φ(z)      P(price < Target) = Φ(z)
```

`Φ` = standard normal CDF. Worked Natenberg example: a break-even 7.1% **below** spot with ~1 expiry's worth of vol gave **68% above / 32% below** — i.e. that distance was ~0.47σ, and Φ gives ~0.68. The book repeatedly reads probabilities straight off the risk curve this way (e.g. "+9.9% move required → 32% probability", "+4.7% required → 41%").

**Reference distances (one-tailed, normal):**

| Distance from spot | P(touch/exceed that side) |
|---|---|
| 0.25σ | ~40% |
| 0.50σ | ~31% |
| 1.0σ | ~16% |
| 1.5σ | ~7% |
| 2.0σ | ~2.3% |

### 3. Probability of TOUCH ≈ 2× probability of finishing beyond (key for binaries)

For a continuous (Brownian) path, the chance of **touching** a barrier any time before the horizon is approximately **double** the chance of **finishing** beyond it (reflection principle):

```
P(touch level before t) ≈ 2 × P(finish beyond level at t)   [for levels not too far, no drift]
```

This matters because a "higher/lower at expiry" binary uses the *finish* probability, while a "touch/no-touch" uses the *touch* probability — never mix them. Delta is the option-world shortcut: **an option's delta ≈ the risk-neutral probability it finishes in-the-money** (Natenberg/Cofnas "PRO = probability" via deltas), so a 0.30-delta strike ≈ 30% finish-ITM.

### 4. Estimating the short-horizon σ you actually plug in

**(a) Simple realized vol (the naïve model).** σ over next N bars ≈ σ over previous N bars: `σ = stdev(log returns of last N bars)`. Sinclair's warning: this has a **windowing effect** — one big bar inflates σ for N bars then drops out, causing jumps (his MMS example: a single 12% earnings bar pushed 30-day vol 17.8% → 39.3%, then back to 23.3% thirty days later). It also **ignores volatility clustering**. Fine as a baseline; bad as the only input.

**(b) EWMA (Sinclair's preferred robust model).** Weight recent returns more, decay old ones exponentially:

```
σ²_t = λ · σ²_(t−1) + (1 − λ) · r²_(t−1)
```

- `r` = latest log return; `λ` = decay (RiskMetrics standard **λ ≈ 0.94**; Sinclair says **0.9–0.99**, lower λ = faster reaction).
- No window-drop jumps; reacts smoothly; one tunable parameter. **This is the recommended live estimator for the bot.**
- Half-life of information ≈ `ln(0.5)/ln(λ)` bars (λ=0.94 → ~11 bars; λ=0.97 → ~23 bars).

**(c) GARCH(1,1)** adds mean-reversion to a long-run variance:
```
σ²_t = γV + α·r²_(t−1) + β·σ²_(t−1)   (α+β+γ = 1, V = long-run variance)
```
Sinclair's blunt verdict: GARCH forecasts are **"generally no better than a simple EWMA"**, MLE params are unstable, needs ~1,000 points. **Don't bother — use EWMA.** If you want mean-reversion cheaply, hand-set GARCH params (e.g. α≈0.9, β≈0.02–0.04 for indices) and use consistently rather than re-fitting.

---

## PART B — VOLATILITY CLUSTERING: WHAT TO EXPLOIT

Sinclair's one durable empirical fact (model-agnostic): **volatility clusters in the short term and mean-reverts in the long term.**

- **Short-horizon persistence:** today's (this minute's) volatility is the best guess of the next minute's. High-vol regimes stay high for a stretch; quiet stays quiet. → The EWMA σ you measure *now* is a genuine forecast for the next 1–5 min, not noise.
- **Long-horizon mean reversion:** extreme vol decays back toward its average. → Don't extrapolate a spike forever; size down during spikes, expect normalization.
- **Trading implication for a binary bot:**
  - **Use the clustering, not the level.** Filter entries by *regime*: only take "price stays in band" style trades when EWMA σ is **low/falling**; demand a bigger edge (further OTM strike, higher payoff) when σ is **high/rising**.
  - A single big bar is an **outlier to discount** (Sinclair literally throws out the earnings bar), not a new permanent vol level — anti-window the simple estimator or rely on EWMA.
  - Momentum analog (Sinclair): the *robust* edges are phenomena that survive any measurement method (vol clustering, price momentum). Start from the phenomenon, then quantify — don't curve-fit a model and hope.

---

## PART C — EDGE & EXPECTED VALUE (Natenberg / Sinclair)

- **You need edge first; risk management cannot rescue a negative edge.** Sinclair: "find a situation with edge, structure a trade, then control the risk … bad risk management will lead to losses" but good risk management on no edge still loses.
- **Edge = your probability is better than the price-implied probability.** For a binary paying `b` per 1 risked on a win and losing the stake on a loss, expected value:
  ```
  EV = p·b − (1 − p)·1     where p = your true win probability
  ```
  You have edge only when `p > 1/(1+b)`. Example: a payout of 0.80 (typical binary) needs **p > 1/1.8 = 55.6%** just to break even. **The house's 80% payout means a coin-flip (50%) bleeds −10% per trade.** Edge must clear the payout hurdle, not 50%.
- **A small edge compounds — if you survive.** Tharp's marble game: 60% win, 1:1 payoff → expectancy +0.20 per dollar risked; over 1,000 trials at $2 risk ≈ +$400. Sinclair's Kelly point: the Kelly criterion **maximizes long-term geometric growth** of a small repeatable edge — but "because of compounding, it is reasonably common that an equal number of wins and losses leaves you with a net loss," which is exactly why sizing (Part E) dominates.

---

## PART D — VAN THARP: EXPECTANCY, R-MULTIPLES, AND WHY SIZING WINS

### Expectancy formula (Tharp Formula 6-1)
```
Expectancy = (PW × AW) − (PL × AL)
```
PW/PL = prob of win/loss; AW/AL = average win/loss **expressed per dollar risked (R)**.
- Marble game 1: (0.6×1) − (0.4×1) = **+0.20R** per trade.
- Marble game 2: 36% win rate but big payoffs → **+0.78R** per trade — *four times better than the 60%-win game.* **Win rate is NOT the goal; expectancy per dollar risked is.**

### R-multiples
- **R = your initial risk on the trade** (entry − stop, or the stake on a binary). Every outcome is measured in R: a win that returns 0.8× the stake = +0.8R; a full loss = −1R.
- A system can have a **<35% hit rate and still be very profitable** if winners are large-R. One 10R winner pays for seven 1R losers.
- For a **binary** the R-multiple is fixed and ugly: win = `+bR` (e.g. +0.8R), loss = `−1R`. You can't engineer big-R winners, so **edge (p) is your only lever** — which makes the win-rate threshold from Part C non-negotiable.

### Position sizing is the dominant variable
- Tharp: of psychology / sizing / system, **position sizing is where most of your P&L actually comes from.** "Position size can let you make a little profit, make a lot, or cause you to go bankrupt — no matter how good your system is."
- A "money-management stop" (exit at −$1,000) is **not** position sizing — it tells you *when to get out*, not *how many units*. Sizing answers **"how much / how many."**

---

## PART E — NO-MARTINGALE SIZING (the survival rules)

### Anti-martingale only
- **Martingale** = increase size after a loss (double-up). Tharp: a 10-loss streak starting at $1 loses **$2,047** and forces a **$2,048** bet to recover $1 — risking $4,000 to win $1; "casinos love" this; "generally do not work — in the casinos or in the market"; "you will eventually have a big enough streak to go bankrupt." **NEVER implement this.**
- **Anti-martingale** = size **up only as equity grows, down as it shrinks.** All sound models are anti-martingale: the dollar bet is a fixed % of *current* equity, so it falls automatically during drawdowns. **This is mandatory for the bot.**

### The Percent-Risk Model (Tharp Model 3 — use this)
```
Units = (Equity × Risk%) / RiskPerUnit
```
For a binary, RiskPerUnit = the stake-at-risk per contract, so simply:
```
Stake = Equity × Risk%        (recomputed every trade off CURRENT equity)
```
- IBM example: $50k account, 2.5% risk = $1,250 risk budget, $4 stop → 312 shares.
- **Tharp's risk-per-trade guidance:**
  - Trading **other people's money** → **< 1%**.
  - Trading **your own** → **under 3% is "probably fine"; over 3% = "gunslinger."**
  - Tharp's own preference when stated: **1%–1.5%**, "2–3% would push the envelope."
  - **Tight-stop / high-frequency systems (← our binary bot): "adopt much smaller risk levels … about half (or less)"** of the above. → **target ~0.5%–1% of equity per binary, and lean to the low end.**

### Why low % — the drawdown table (Tharp's 55-day breakout test)
Same system, only risk% changed:

| Risk % per trade | Max Drawdown |
|---|---|
| ~1% | ~6% |
| ~3% | ~13% |
| ~5% | ~22% |
| 10% | ~46% |
| 15% | ~62% |
| 25% | ~84% (best return-to-risk ratio — but unsurvivable) |

The *best risk-adjusted return* sat at 25% risk — but it required an **84% drawdown** no human or account survives, and margin calls began at 10%. **Conclusion: pick the risk% by the drawdown you can survive, not the return you want.** Cutting risk% cuts drawdown roughly proportionally while you keep most of the edge.

### Risk of ruin (the binary case)
- Even a **positive-expectancy** game ruins you if the bet is too large vs. equity. Tharp: bet 100% of a +20%-EV game and one loss = broke; bet 50% and a few losses gut you — you can no longer realize the long-run edge.
- Practical ruin driver = **bet fraction vs. losing-streak length.** With win prob `p`, the chance of a run of `k` losses is `(1−p)`^k; over thousands of trades long streaks are *expected* (Tharp: "over 1,000 trials you could easily have 10 losses in a row" even at 60% win). At fixed fraction `f` of equity per trade, `k` straight losses multiply equity by `(1−f)^k`.
  - f = 1% → 10 losses ≈ **−9.6%** equity. Survivable.
  - f = 5% → 10 losses ≈ **−40%**. Brutal.
  - f = 10% → 10 losses ≈ **−65%**. Effectively ruined.
- **Set f so the worst plausible streak (e.g. 15–20 losses) still leaves >60–70% equity.** At 1%, a 20-loss streak = −18%. That's the design target.

### Fractional-Kelly cross-check (Sinclair)
- Kelly fraction for a binary with edge: `f* = p − (1−p)/b` (= edge/odds). E.g. p=0.58, b=0.8 → `f* = 0.58 − 0.42/0.8 = 0.055` → full Kelly ≈ 5.5% of bankroll.
- **Never bet full Kelly.** Sinclair: full Kelly drawdowns are "unpalatably," and because `f*` is *estimated* from noisy data, **even HALF-Kelly still carries a ~25% chance of over-betting** (true f could be below your estimate, or even negative). His table: to hold over-betting risk to ~10% you scale to roughly **0.05–0.20 of measured Kelly**.
- **Operating rule: size = min( Percent-Risk cap (~0.5–1%), quarter-Kelly or less ).** Quarter-Kelly of the 5.5% example ≈ 1.4% — already near the Tharp tight-stop ceiling, so the **~0.5–1% percent-risk cap binds first.** Good: both books point to the same small number.

---

## 10-LINE SUMMARY — vol→probability method + safe sizing rules

1. **Estimate σ with EWMA**, not a rolling window: `σ²_t = λσ²_(t−1) + (1−λ)r²_(t−1)`, λ≈0.94 (Sinclair: EWMA ≥ GARCH in practice).
2. **Rescale by √time** to the horizon: `σ_h = σ_per_min × √(minutes ahead)`; quote everything in price as `Price × σ_h`.
3. **Probability via normal CDF:** `z = (Target − Price)/(Price·σ_h)`; `P(above) = 1 − Φ(z)`, `P(below) = Φ(z)`. Calibrate to Natenberg's 0.47σ→68% benchmark.
4. **Touch ≈ 2× finish:** use *finish* prob for higher/lower binaries, *touch* prob (≈ double) for touch/no-touch — never mix.
5. **Exploit clustering:** this-minute σ predicts next-minute σ; trade range-style binaries only when EWMA σ is **low/falling**, demand more edge when it's high; discard single outlier bars.
6. **Edge must clear the payout hurdle:** for payout b, break-even is `p = 1/(1+b)` (0.8 payout → **55.6%**, not 50%); only trade when your modeled p beats it with margin.
7. **Judge systems by expectancy, not win rate:** `E = (PW·AW) − (PL·AL)` in R; for a binary R is fixed (win +0.8R, loss −1R), so edge p is the only lever.
8. **Anti-martingale ONLY — never raise size after a loss.** Stake = **% of current equity**, recomputed each trade (Tharp Percent-Risk Model). Martingale = guaranteed eventual ruin.
9. **Size small:** tight-stop/high-freq binary → **~0.5%–1% of equity per trade** (Tharp's "half or less" for tight stops; binds before quarter-Kelly). At 1%, a 20-loss streak only costs ~18%.
10. **Pick risk% by survivable drawdown, not target return** (25% risk gave best ratio but 84% DD = dead); design so the worst plausible losing streak still leaves >60–70% of equity.
