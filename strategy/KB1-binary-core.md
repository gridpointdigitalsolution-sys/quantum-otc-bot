# KB1 — Binary / Fixed-Time Options Core (Short-Expiry, OTC, No Martingale)

> Synthesized from: Nekritin *Binary Options* (2013), Cofnas *Trading Binary Options* (Bloomberg), Chan *Quantitative Trading*.
> **Target build:** automated 1–5 minute CALL/PUT bot on OTC instruments (Pocket Option / Deriv). Fixed payout (~70–95%), **no early exit**, **no martingale**.

---

## 0. PLATFORM REALITY (what transfers, what doesn't)

Our OTC product is **non-laddered high/low**: you only pick **CALL (finish above) / PUT (finish below)** at a fixed expiry, for a fixed payout, with **no strikes and no early exit**. Cofnas treats every such trade as theoretically **at-the-money / 50%** — so **all edge must come from the signal + win-rate**, never from strike/premium structure.

**Drop entirely (cannot be built on Pocket/Deriv):** strangles, premium-collection / volatility-short spreads, selling a strike, legging out, limit-order "make your market," and the "roll-out" re-entry (martingale-adjacent anyway). Keep only their *concepts* (mean-reversion, distance-from-mean, duration-vs-exposure).

---

## 1. THE PAYOUT GATE (compute this first for every setup)

Win returns `payout × stake`; a loss costs `1 × stake`. The payout shortfall is your structural cost (the binary analogue of spread/commission — and it's huge).

**Break-even win rate:**  `W* = 1 / (1 + payout)`

| Payout | Break-even win rate | Practical min to deploy (margin) |
|---|---|---|
| 70% | 58.8% | ~63%+ |
| 80% | 55.6% | ~60%+ |
| 85% | 54.1% | ~58%+ |
| 90% | 52.6% | ~57%+ |
| 95% | 51.3% | ~56%+ |

**Per-trade expectancy (per $1 staked):** `E = W·payout − (1−W)`

**Rules:**
- **Never take a setup whose backtested win-rate doesn't clear `W*` with real margin.** At 80% payout (Pocket/Deriv default per Cofnas), you need **~56% just to break even** → demand **≥60%** before trusting it live.
- **Lower payout → require a higher-probability (stronger-signal, closer-to-mean) entry.** Higher payout lets weaker setups qualify.
- On fixed-80% platforms the "cheap OTM, big payout, low hit-rate" trade does **not** exist — edge is **entirely win-rate**, which raises the signal-quality bar.

---

## 2. ENTRY SETUPS (exact indicators + parameters + CALL/PUT conditions)

### 2A. Double Bollinger Band mean-reversion — **primary setup (Cofnas)**
- **Inner band: BB(20, 2)** — 20-period SMA ± 2σ → price inside ~96% of the time.
- **Outer band (EBB): BB(13, 2.618)** — 13-period MA ± 2.618σ (2.618 = Fib extension) → captures ~99%.
- **CALL** when price **pierces BELOW the lower band and then closes back ABOVE it** (return-into-band confirmation). Piercing the **lower EBB then returning** = strongest buy.
- **PUT** when price **pierces ABOVE the upper band and then closes back BELOW it**. Piercing the **upper EBB then returning** = strongest sell.
- **Never fade a bare touch** — price can "ride the band" a long time. Require the close-back-inside confirmation.
- **Skip if several candles in a row hug the band** ("sticky" = undecided) — wait.
- **Narrow bands = breakout pending → do NOT range-fade** (can snap against you).
- **Confluence booster:** band edge coinciding with a horizontal S/R level (or Fib 61.8%) = high-conviction zone.

### 2B. z-score / %b reversion — **same logic, codeable form (Chan)**
For a single instrument with no pair, fade deviation of price from its own moving average in σ units:
```
z = (price − MA) / movingStdDev          # this IS Bollinger %b
Enter CALL  when z ≤ −2
Enter PUT   when z ≥ +2
(Optimized tighter variant, validate OOS: enter ±1, exit 0.5)
```
Exit is the expiry (see §3). In a reversion regime **never attach a stop-loss** — a stop exits at the worst moment. Exit only on expiry / mean-touch / detected regime flip.

### 2C. Expiry-matched short-timeframe triggers (Cofnas drills)
- **1-min expiry:** 1-minute **Three-Line-Break** (or Renko) chart → enter **the instant the brick color reverses**.
- **5-min expiry:** wait for a **parabolic exhaustion curve** → enter **opposite direction once it peaks and starts reversing** (fade the blow-off).
- **~30-min expiry:** instrument ranging ~30 pips + double Bollinger → enter at **outer band touch + reversal**, direction = the reversal.

### 2D. Support / Resistance bounce (Nekritin + Cofnas)
- **Level = price repeatedly failed to cross.** Strength ∝ number of touches/bounces (**≥3 touches = strong**).
- **Weight round "big figures" (ending 0 or 5) higher** — psychologically harder to breach.
- **CALL** at a strong, multiply-tested **support** that price reaches and **bounces** off.
- **PUT** at a strong, multiply-tested **resistance** that price reaches and **bounces** off.
- Intraday S/R is noisier than daily/weekly → require tighter momentum confirmation.

### 2E. Three-Line-Break reversal engine (Cofnas)
- New brick only on a new close-high (white) / close-low (black). **Reversal brick** prints only when price penetrates the high/low of the **previous 3 bricks**.
- Heuristic: scan prior window's max consecutive bricks; a run approaching that historical max = high reversal probability. **Small/shrinking bricks = tiring trend = breakout pending.** "Reversal followed by another reversal" = strong continuation.

### 2F. Moving-average / trend regime (Cofnas)
- Pair: **MA(21)** vs **MA(50)**. 21 above 50 = up-bias; price probing the 50-MA = possible trend change.
- Example cross rule (illustrative): 21-MA crosses above 50-MA → ATM CALL.
- Trend-angle score: ~**37–45°** trendline = stable rideable trend; near-90° = parabolic = fade.

### 2G. Candlesticks (confirmation, Cofnas)
Hammer (long wick ≈2× body) = reversal; Doji = indecision (trade the break after it); Bullish/Bearish **Engulfing** = mood flip → CALL/PUT; Tweezers (equal highs/lows) = reversal. **Reliability scales with timeframe** — 1-min candles weak; use as confirmation only, not standalone on 1-min.

> **Indicators not in these books:** RSI and MACD parameters/levels, and pivot-point formulas, are **NOT** specified by Cofnas/Nekritin/Chan. Source those elsewhere; do not invent thresholds from these texts.

---

## 3. EXPIRY / DURATION SELECTION

### 3A. Half-life formula — sets your exact expiry (Chan, highest-value)
Fit Ornstein-Uhlenbeck on the series at your trading bar resolution (e.g. 1-min):
```
dz = θ · (prev_z − mean) + error      # OLS: regress per-bar change on lagged level
Half-life = ln(2) / |θ|               # θ is the (negative) slope
```
- The half-life **is** the statistically-correct holding period. If half-life ≈ 3 bars on 1-min data → ~3-min expiry. Shorter expiry = exit before reversion completes; longer = overstay.
- Robust because it uses the whole series, not just trade days.

### 3B. Cofnas chart↔expiry map
| Expiry | Chart |
|---|---|
| 1 min | 1-min Renko |
| 5 min | 1-min Three-Line-Break |
| 15 min | 15-min candlestick |
| EOD | 30-min Three-Line-Break |
| EOW | 1-day Three-Line-Break |

### 3C. Duration principle (Nekritin)
**Use the shortest expiry that preserves your statistical edge.** Less time in = less exposure to an adverse move = higher win probability for a range/reversion bet. Derive the window empirically: **measure % of times the instrument moved > X within candidate window Y**, pick the window that maximizes edge. (Move probability scales with the window — e.g. S&P moves >1%/day only ~19% of days.)

---

## 4. FILTERS THAT RAISE WIN RATE

### 4A. Volatility-regime via Bollinger width (Cofnas)
- **Narrow bands = low vol = breakout pending** → do NOT range-fade; either sit out or play the break.
- **Wide bands = high vol** → bigger swings; favor extreme/reversal fades but size down.
- **Extreme volatility = reversal signal** (regression to mean). It's the **rate-of-change** of vol, not the level, that matters most.
- Optional confirm: VIX (S&P ≈ −0.85 corr), or per-asset vol indexes OVX/GVZ etc.

### 4B. Trend vs range detection (Cofnas 5-step pre-trade flow)
scan fundamentals → rank trend → check ranging → check pattern → evaluate vol → trade.
- **Trend:** higher-highs+higher-lows (or inverse), confirmed by 3-line-break persistence + 50-MA + trendline angle. → reversion fades fail in strong trends ("don't stand in front of a freight train").
- **Range:** ≥3 tested S/R touches, narrowing range/triangle. → reversion setups valid.

### 4C. News / regime gating (Chan + Cofnas)
- **Suppress reversion entries around scheduled news/releases and abnormal directional bursts.** A move *with* news = momentum regime (reversion will lose); a move *without* news = liquidity event = reversion likely.
- Always review the economic calendar first. Either **avoid** the release instant, or run a dedicated **break/Fib-retrace** news tactic (below) — never blind-fade into news.

### 4D. Session timing (Cofnas)
- FX binaries ~24h (Mon 03:00 EST Asia open → Fri NY close). Cross pairs (GBP/JPY, EUR/JPY) show cleaner patterns (no USD noise).
- Day-of-week bias (reusable): **Monday** best contrarian; **Wednesday** best ATM/balanced; **Thursday** go-with-crowd; **Friday** deep-ITM only. Treat intraday moves as **noisy** → require stronger momentum filters.

### 4E. Confidence ranking 1–5 (Cofnas) — measurable edge filter
Rank each candidate trade 1–5 before entry; **skip anything < 3** (a 2 = trading against your own judgment). Over time, high-confidence trades should show materially higher win-rate — log it.

### 4F. Multi-indicator independence (Nekritin)
If using ≥2 indicators, **at least two must come from DIFFERENT groups** (avoid colinearity/curve-fit):
Trend (MA, ADX) · Volume (OBV, A/D) · Volatility (Bollinger, Keltner) · Momentum (Stochastics, ROC) · OB/OS (RSI, CCI).
- **Forbidden:** MACD + MA (both trend). **Good:** trend + volume, or trend + OB/OS.

### 4G. Fibonacci confluence (Cofnas)
Use 38.2 / 50 / **61.8** (61.8 on daily = most important). A level **just past 61.8%** faces strong resistance → low success unless big momentum. 3-line-break reversal landing **on the 61.8% Fib** = ideal. Use BB-edge + S/R + Fib61.8 confluence to upgrade conviction.

---

## 5. MONEY MANAGEMENT (no martingale)

### 5A. Per-trade sizing
- **Fixed-fractional: default 2% of equity per trade.** Band 1–5%, **hard cap 5%**, never exceed. Lower toward 1–2% the more consecutive losses your backtest shows. If no backtest, start at 2%.
- On OTC, max-loss = stake, so simply: **stake = Account × Risk%** (round down).
- Anti-martingale core (all three authors): **de-lever after losses, lever up only on profits.** Never increase size to recover a loss. Treat a loss as a contra-directional signal ("switch horses"), not a reason to double.

### 5B. Kelly fraction (Chan) — optimal stake, then halve it
Binary discrete form:
```
f* = (W·payout − (1−W)) / payout       # = edge ÷ payout
```
- **Trade at HALF-Kelly (`f*/2`)** — fat tails + noisy estimates make full Kelly too violent.
- Cap by worst-case: `maxLeverage = (tolerable drawdown) / (worst historical single loss)`; use the **smaller** of half-Kelly and this cap.
- Re-estimate W on a rolling lookback (≈6-month for daily; shrink proportionally for minute bars), update ≥ daily. As edge decays, Kelly auto-drives stake → 0 (built-in kill-switch).

### 5C. System halt cutoffs (predetermine BEFORE trading)
- **Drawdown cutoff:** stop when live DD from **peak** > (historical max DD × 1.5). Keep max DD < 20%, ideally < the system's average annual return.
- **Consecutive-loss cutoff:** halt when consecutive losses > (historical max × 1.5–2). E.g. backtest max 7 → halt at ~10.
- **Use BOTH** (protects against one bad cluster *and* many small losses). DD always measured from net equity high. Acts as an aggregate trailing stop that can lock in profit; tighten the % once at target.
- Reference DD math: 5 consecutive 2% losses ≈ 9.6% DD; 5 × 5% losses ≈ 20.2% DD → justifies 2% default.

### 5D. Reinvestment & withdrawals (Nekritin)
- **Reinvest 100% of profit during operation.** If you eat 100% of losses but only reinvest part of wins, you're doomed.
- Take profit only at a **preset target / fixed period / DD cutoff** — never bleed per-trade. (Compounding: $50k @ 30%/yr → ~$408k in 8 yrs.)

### 5E. Diversification (Nekritin)
- Run **≥2 regime-uncorrelated systems** (e.g. one reversion/OB-OS + one trend-follow) across multiple instruments, each in a **separate account** with independent cutoffs.
- **Pyramid capital toward the LOW-DD/low-return stable system**, less to the high-DD aggressive one. DD and expectancy matter far more than raw profit.

---

## 6. STATISTICAL / EDGE CONCEPTS

- **Mean reversion = the backbone.** ±2σ (96%) and ±2.618σ (99%) are low-probability outliers expected to revert. Chan: reversion regimes are more prevalent than trending. Nekritin: an instrument is most likely to end where it started over an interval (normal distribution). CME: ~80% of OTM options expire worthless.
- **Pick mean-reverting instruments, not trending ones.** Indexes revert; commodities (gold, oil) and most FX trend → worse for reversion. Validate with **ADF / stationarity test** (t-stat more negative = more stationary; crit 1%=−3.819, 5%=−3.343). Cointegration ≠ correlation.
- **Expectancy = W·avgWin − L·avgLoss** (per trade). General break-even identity: `W×win − L×loss ≥ 0`.
- **Chase Sharpe (consistency), not raw return:** `g = r + S²/2`. Sharpe <1 not viable; ~2 profitable most months; >3 most days. More independent bets → higher Sharpe (law of large numbers) — the structural reason short-frequency can win, **provided positive per-trade mean survives the payout shortfall.**
- **Casino framing (Nekritin):** a <1% house edge wins long-run via repetition + fixed rules + no emotion. Any slight, validated edge + strict risk management compounds.
- **Edges decay (~1–2 yr life cycle).** Plan proactive changes (improve on robust data without overfitting); never reactively flip a system mid-drawdown.

---

## 7. BACKTESTING & VALIDATION (don't ship a lie)

- **Sample size:** ≥200 trades minimum; intraday/minute systems want **500+**. Chan: required data ≈ `252 × (#free parameters)` at the model's bar frequency; **keep ≤5 free parameters total** (entry, exit, thresholds, lookbacks, holding period all count).
- **Span all regimes:** the test window MUST contain an uptrend, a downtrend, AND a sideways/choppy stretch. A long-biased system tested only on a bull market gives fake results.
- **No curve-fitting:** ≥2 uncorrelated indicators (different groups); sensitivity-test every parameter — if only the single optimal value works, it's overfit; strip conditions one at a time and keep the simplest model whose OOS performance holds.
- **Out-of-sample:** split ~50/50 (test ≥1/3 of train); optimize on train only; prefer **rolling-window re-optimization** ("parameterless"). Require similar in-sample vs OOS results.
- **Look-ahead bias:** lag every indicator to the **prior completed bar**; never use the current bar's high/low/close before it closes. Validation trick: backtest full data (file A) vs data truncated by N bars (file B) — overlapping rows must be **identical**; any mismatch = leak.
- **Transaction cost / payout reality is decisive:** the #1 way short-term backtests lie is ignoring cost. For us, the **payout shortfall (1−payout)** is that cost — your edge must clear the §1 break-even with margin.
- **Mean-reversion traps:** scrub bad ticks / outliers (a >4σ bar with no market-wide move = bad print that fakes reversion P&L); watch survivorship if filtering a universe.
- **Graduated deployment (all authors):** backtest → demo/paper (Chan: log ~100 live trades per 1,000 backtested) → small live → scale. Paper trading is the only honest test of a very-fast strategy (sub-minute needs bid/ask, not just last price).

---

## 8. OTC / SYNTHETIC-INSTRUMENT NOTES

- Every OTC high/low trade is theoretically **ATM/50%** — no strike edge; **win-rate is the entire game.**
- **No early exit** → expiry is your only exit; set expiry ≈ half-life (§3A).
- Prefer **mean-reverting synthetics/indexes** over trending instruments; validate each with ADF before deploying a reversion bot.
- Deriv synthetics have *defined, stable volatility* by construction — a clean fit for fixed σ-band thresholds and the half-life expiry method. Still gate by regime (§4) and avoid the few discontinuous-jump instruments.
- No order book / fixed payout → "make your market," limit-fill, and spread-arb tactics are N/A; replace with a **payout-threshold filter** (skip trades when the platform's offered payout drops the setup below its required `W*`).

---

## TOP BUILDABLE SETUPS — 10-line summary

1. **Double-Bollinger reversion (primary):** BB(20,2)+BB(13,2.618); CALL on pierce-below-then-close-back-inside lower band, PUT on the upper — strongest on the EBB; never fade a bare touch.
2. **z-score reversion (codeable twin):** z=(price−MA)/movStd; CALL z≤−2, PUT z≥+2; NO stop-loss in reversion regime — exit = expiry only.
3. **Set expiry by half-life:** `ln(2)/|θ|` from an OU fit on 1-min bars → that's your 1–5 min window (don't guess).
4. **1-min Three-Line-Break / Renko color-reversal** entry for 1-min expiry; **fade parabolic exhaustion** for 5-min expiry.
5. **S/R bounce:** CALL at ≥3-touch support, PUT at ≥3-touch resistance, weight round "big figures" higher; upgrade with Fib-61.8 / band confluence.
6. **Payout gate (mandatory):** `W*=1/(1+payout)`; at 80% payout demand **≥60%** backtested win-rate before any setup is allowed live.
7. **Regime filter:** narrow bands = breakout pending (don't fade); strong trend = skip reversion; suppress all entries around scheduled news.
8. **Sizing:** fixed 2%/trade (cap 5%) or **half-Kelly** `f*=(W·payout−(1−W))/payout ÷ 2`; **de-lever after losses, never increase to recover** — strictly anti-martingale.
9. **Cutoffs:** halt on DD-from-peak > 1.5× historical max OR consecutive losses > 1.5× historical max; reinvest 100% until a preset profit/period target.
10. **Validate honestly:** ≥500 minute-bar trades across bull/bear/range, ≤5 params, lag all inputs (no look-ahead), OOS split + rolling re-opt, then paper → small live → scale.
