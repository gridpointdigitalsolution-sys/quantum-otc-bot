# KB7 — DISTILLED PLAYBOOK (the bot's brain)

Built 2026-06-22 from: 9 KBs (16 books) + ~6,000 video transcripts (23 binary + 6 forex
channels, mined by 6 parallel agents). Every setup here is a BACKTEST HYPOTHESIS, not a
proven edge. **No setup in the entire corpus has a verified win rate** — every "%", "$X",
"100% ITM" is marketing. Trust only what survives the 100k-trade backtest + validation.

═══════════════════════════════════════════════════════════════════════════
## THE ONE CORE INSIGHT (decides everything)
═══════════════════════════════════════════════════════════════════════════
Fixed-payout binary CAPS the win at ~85-92% but every loss is -100%. So unlike forex
(where you let winners run for big R), binary STRUCTURALLY REQUIRES A HIGH HIT-RATE.
- At 92% payout, break-even = 52.1% WR. At 85% = 54.1%.
- Therefore the RIGHT strategy family = **mean-reversion snap-backs at extremes** (high
  hit-rate, small consistent wins) + **liquidity-sweep reversals** (high-probability traps).
- The WRONG family = trend-following / big-R / "let it run" (Brad Goh's forex model). Five
  independent agents confirmed this inversion. We KEEP these traders' ENTRY TRIGGERS and
  DISCARD their R:R/exit math entirely.
This is why mean-reversion (ADF/Hurst/z-score/Bollinger — KB1/KB3) is the spine of the bot.

═══════════════════════════════════════════════════════════════════════════
## SETUPS — cross-validated, deduped, ranked by SUPPORT × book-agreement
═══════════════════════════════════════════════════════════════════════════
Confidence: HIGH = book + 3+ independent channels; MED = book + 1-2 or strong logic;
LOW = single source / must-backtest-before-trust.

### ─── TIER 1: BUILD + BACKTEST FIRST (strongest cross-validation) ───

**S1. Bollinger-Band Reversion (the flagship mean-reversion)**  CONFIDENCE: HIGH
- Sources: BOOKS KB1 (double-Bollinger), KB3 (z-score>=2) + BLW(#2/#6), binaryoptions.com(x3),
  SAM(#18), QuantProgram(A2), RockStarrFX(#1). SUPPORT 12+ across 5 channels + 2 books.
- Indicators: BB(20,2) primary; faster BB(10,2) for shorter expiry (QuantProgram). Optional
  inner+outer double band (KB1: BB(20,2)+BB(13,2.618)).
- Regime (DETECT in code): RANGE ONLY. Trade only if Hurst<0.5 (mean-reverting) OR ADX<20
  OR BB-width below its 50-bar median (bands NOT widening). If bands widening -> breakout -> skip.
- 3 gates: WHERE = price tags/closes beyond +/-2 sigma band (z-score>=2). WHAT = rejection (wick
  back inside) / candle closes back inside band. WHEN = close-confirmation candle -> enter next open.
- Direction: tag UPPER band + reject -> PUT. tag LOWER + reject -> CALL.
- Expiry: 1m (BB10,2) to 5m (BB20,2). Half-life of the band excursion sets it (KB3): compute
  OU half-life on the asset; expiry ~ half-life, clamp 1-5m.
- Invalidation: bands widening; strong trend (ADX>25); price at major S/R that may break.
- CLAIM: none verified. RISK: 1% fixed.

**S2. RSI / Stochastic Extreme + Band Confluence**  CONFIDENCE: HIGH
- Sources: KB1/KB3 + binaryoptions.com, SAM(#7), RockStarrFX(#1/#2), BLW(#3), QuantProgram(A1).
  SUPPORT 10+ across 5 channels + books.
- Indicators: RSI(14) 70/30 OR fast RSI(5) (QuantProgram, better for short expiry); OR
  Stochastic(5,3,3) 80/20 cross (RockStarrFX flagship). Layer with S1's band.
- Regime: RANGE (reversion). For RSI-in-trend variant (A1): RSI(5)<30 AND price>EMA50 = buy
  dip in uptrend (CALL); mirror for PUT.
- 3 gates: WHERE = RSI/Stoch in extreme zone AT a band edge or S/R level. WHAT = Stoch %K/%D
  cross back / RSI turns. WHEN = confirmation candle close -> next open.
- Direction: overbought+cross-down -> PUT; oversold+cross-up -> CALL.
- Expiry: 1-5m. Invalidation: trending market (false OB/OS); RSI pinned >=5 bars.

**S3. Liquidity-Sweep / Stop-Hunt Reversal (= the KB8 WHERE-WHAT-WHEN framework)**  CONFIDENCE: HIGH
- Sources: KB8 (3-gate manipulation), KB2 (Volman false-break) + Brad Trades("Entry Model #3"),
  PROFIT TRADING(SMC), Pivot Call(#6 fake-breakout). SUPPORT 5+ across 3 channels + 2 books.
  This is the single most cross-domain-validated PATTERN (book quant + price-action + SMC all agree).
- Rule (codeable): (1) price sweeps a recent swing extreme -- low[1] < min(low[2..N]) with N~5-10
  -- then (2) closes BACK inside (close[1] > low[1]) = the false break / liquidity grab, then
  (3) micro break-of-structure in the reversal direction -> enter confirm candle.
- Regime: works at range edges + at S/R; the sweep IS the signal that big players defended a level.
- Direction: swept a LOW then reclaim -> CALL; swept a HIGH then reclaim -> PUT.
- Expiry: 1-5m. Invalidation: price closes beyond the swept level (real break, not a trap);
  re-used liquidity (a level already swept can't re-trigger).
- This maps 1:1 to KB8 gates: WHERE=swing extreme/level, WHAT=sweep+reclaim, WHEN=BOS+confirm.

**S4. Engulfing + EMA10/20 Trend Filter (the ONLY backtested setup in the corpus)**  CONFIDENCE: HIGH(method)
- Source: Trading Heroes -- ON-SCREEN BACKTEST: 76% WR / ~600 trades / 27 pairs / DD 0.3% at
  1:1 RR (best subset 81%/267tr). Daily forex, but the PATTERN ports. Also Brad Goh(#1 candle),
  The Trading Channel, PO(#17). SUPPORT 4+ + a real backtest.
- Indicators: EMA10 + EMA20 (trend stack) + engulfing candle (body engulfs prior body).
- Rule: bullish engulf with EMA10>EMA20 -> CALL; bearish engulf with EMA10<EMA20 -> PUT.
- Regime: trend-continuation. NOTE: this is the one TREND setup that survives because the
  engulf gives a high-hit-rate entry; 76% WR clears even 90% payout. MUST re-test on OUR
  assets + short expiry (daily-forex result may not hold on 1m OTC).
- Expiry: 1-5m. Invalidation: engulf against EMA stack; choppy EMAs tangled.

### ─── TIER 2: BUILD AFTER TIER 1 (single/dual-source, fully numeric) ───

**S5. Parabolic SAR + Oscillator Trend-Flip**  CONFIDENCE: MED
- BinaryTrader(x2), Katie(#12), SAM(#29/30). SAR(0.02,0.2) + CCI(13)+/-100 OR RSI(14)>/<50.
  SAR flips below candle + osc confirms -> CALL; mirror PUT. 1m. Trend only, skip chop.

**S6. Fractal + Dual-MA Cross**  CONFIDENCE: MED (regime-conflicted -- TEST BOTH)
- Most-TAUGHT family (10+ videos: BinaryTrader x4, SAM, Katie x5) BUT channels disagree on
  regime (SAM=trend, Katie=range). Fractal(3-5) + SMA fast/slow (3/7, or EMA20/50). Bullish
  fractal + fast crosses above slow -> CALL. The regime conflict IS the backtest question.

**S7. Bollinger Squeeze Breakout**  CONFIDENCE: MED
- SAM(#17), BinaryTrader(#16). BB(20,2) or BB(13,2). Squeeze >=5-8 bars -> candle closes fully
  outside band while bands widen -> trade break direction. 1-5m. (Opposite regime to S1 -- this
  is the breakout side; the regime filter decides which fires.)

**S8. Schaff Trend Cycle / Momentum (low-lag for very short expiry)**  CONFIDENCE: MED
- Pocket Option official: traditional indicators FAIL below 1 min -- only fractal/momentum/STC
  work at 5-10s. STC(23,50,10), Momentum(10) cross 100, Awesome Osc(5,34) zero-cross. Only
  relevant IF we trade sub-1m (probably not first).

**S9. Williams %R Snap-Back**  CONFIDENCE: MED
- SAM(#6). Williams%R(10); hits -100 then snaps above -80 -> CALL; mirror at 0/-20 -> PUT. 1m.
  RANGE only, skip if pinned >=5 bars. (A clean mean-reversion variant of S2.)

### ─── TIER 3: IDEA BANK (lower priority / fuzzier -- test only if Tier 1-2 thin) ───
Keltner-exit+oscillator (BinaryTrader), Aroon+RSI+MA (BinaryTrader S8), Vortex+trend (S6-adjacent),
Pin-bar+20MA proximity (Pivot Call -- clean numeric), Initial-Balance breakout (Pivot Call, 70%
CLAIM, session-anchored), CPR/pivot reaction (Pivot Call), Inside-bar/3-candle PA (SAM),
linreg-channel z-score (QuantProgram -- cleaner than BB), RSI-divergence (5-50 bar window) as a
CONFIRM filter only. Donchian/ADX/Ichimoku/Fib variants -- low priority.

═══════════════════════════════════════════════════════════════════════════
## RISK GOVERNOR (EdgeFlo blueprint -- exact numbers, port verbatim)
═══════════════════════════════════════════════════════════════════════════
```
risk_per_trade_pct      = 1%  fixed (0.5% on A setup, 1% on A+)   # NO martingale, structural
max_trades_per_day      = 2 (ideal) .. 5 (hard cap)
max_daily_loss_pct      = 2%   -> HALT new entries rest of day
daily_profit_target_pct = 5%   -> HALT (lock the win)
stop_after_consec_losses= 3-5  -> HALT session
cooldown_after_loss     = N min/bars (kills revenge/tilt)
trading_window          = chosen session only (London/NY overlap to A/B-test on OTC)
payout_floor            = 90% normal / 85% off-peak (KB9) -> skip below
max_concurrent_exposure = ~5%
min_sample_before_live  = 100 trades reviewed (Rule of 100)
news_blackout           = hard veto around high-impact events (real assets); N/A pure synthetic
```
On ANY breach -> bot enters HALT (no new entries; open trades run to expiry). Anti-martingale
is STRUCTURAL (stake = fixed % of balance, impossible to size up after a loss).
EdgeScore scorecard (rolling 100 trades): Performance (expectancy+PF) + Discipline (breach count)
+ Consistency (risk-deviation) -> for the dashboard's honesty layer.

═══════════════════════════════════════════════════════════════════════════
## ENGINEERING REQUIREMENTS (for Prompt 2 -- the build) -- from quant channels + KB4
═══════════════════════════════════════════════════════════════════════════
- PAYOUT-CAP IN EVERY BACKTEST: win=+payout%, loss=-100%. Breakeven WR=1/(1+payout). A backtest
  without this is fantasy (Moon Dev: 588%->5% once costs added).
- FRACTIONAL KELLY sizing: f=(b*p-q)/b, b=payout fraction; use 1/4-1/2 Kelly; f<=0 = no trade.
- WALK-FORWARD (Pardo): rolling train->OOS test, concatenate OOS. Report WFE.
- MONTE CARLO permutation on P&L (p-value, not WR) + MULTIPLE-TESTING correction (White's
  Reality Check / Bonferroni) -- testing many setups x assets x expiries WILL throw fake winners.
- VOL KILL-SWITCH: ATR-percentile gate halts entries in chaos (QuantProgram "go to cash").
- ROBUSTNESS: broad profitable param plateau (heatmap), not one spike; low param count; test
  across many assets, never one cherry-picked.
- HARNESS: backtesting.py-style (init precompute indicators / next per-bar, no look-ahead) +
  TA-Lib for indicators (talib.RSI/BBANDS/ATR) + VectorBT for param sweeps.
- ENTRY REALISM: signal on candle CLOSE -> enter NEXT candle open -> settle on exact expiry price.
- MULTI-STRATEGY: host several uncorrelated setups gated by a regime classifier, not one signal.

═══════════════════════════════════════════════════════════════════════════
## ASSET MAPPING + STEP-0 WARNING (critical honesty)
═══════════════════════════════════════════════════════════════════════════
| Asset class | Setups that fit | Honest viability |
|---|---|---|
| Deriv Volatility indices (R_10..R_100, 1HZ) 92-93%, 24/7 | S1,S2,S9 (mean-rev) | WARNING: GBM-RANDOM-WALK by design. Mean-reversion may NOT exist -- could be curve-fit noise. STEP 0 (autocorr/runs/variance-ratio/Hurst) MUST prove exploitable structure FIRST. Likely HARDEST to beat. |
| Deriv Boom/Crash (spike) | spike-scalp only (asymmetric) | NOT mean-reverting. Boom spikes UP->PUT-to-catch is asymmetric; niche, test separately. |
| Deriv Step Index | low-vol reversion | test in Step 0. |
| PO OTC currencies (92%, KB9 list) | S1,S2,S3,S4,S6 | Broker-GENERATED feed -- MAY carry exploitable microstructure/patterns. Possibly more tractable than Deriv synthetics. Each pair verified on its own logged data. |
| Deriv forex/indices/commodities | S3,S4 | market-hours only; real price action -> S3/S4 most likely to transfer. |

**The make-or-break question Step 0 answers:** are Deriv synthetics (pure RNG) even beatable?
If not, the bot lives on PO OTC + Deriv real-market assets. Do NOT assume -- TEST.

═══════════════════════════════════════════════════════════════════════════
## REJECTED (do not build)
═══════════════════════════════════════════════════════════════════════════
- Deriv DIGIT contracts (Over/Under, Even/Odd) via martingale -- Deriv Navigator's whole
  model is RNG digit-% + martingale recovery. Violates NO-MARTINGALE. The ~9%-payout Under-8
  needs 92% WR; 3 losses = blowup. REJECT. (A non-martingale digit-skew bet could be studied
  later, but the taught version is pure martingale -- out.)
- All "100%/99% NEVER LOSE" signal/Telegram/AI-bot affiliate content (Cosmo entire channel,
  BINARY OPTIONS UK music-demos, BLW app upsells, vfxAlert promos) -- fabricated, zero rules.
- Trend-following big-R / "let winners run" exits (Brad Goh forex) -- structurally wrong for
  fixed payout. Keep their entries (S3), discard exits.
- Volume-spike setups on synthetic OTC (no real volume feed).

═══════════════════════════════════════════════════════════════════════════
## BACKTEST-READY TABLE (Prompt 2 consumes this directly)
═══════════════════════════════════════════════════════════════════════════
| setup_id | assets | timeframe/expiry | entry_rule | regime_filter | params | confidence |
|---|---|---|---|---|---|---|
| S1 | PO-OTC ccy, Deriv-vol(if Step0 ok) | 1-5m | tag+/-2sigma band + reject + close-back-inside -> fade | Hurst<0.5 OR ADX<20 OR BBwidth<median | BB(20,2)+BB(10,2) | HIGH |
| S2 | PO-OTC ccy, Deriv-vol | 1-5m | RSI(5/14) or Stoch(5,3,3) extreme + cross at band/level -> fade | range (ADX<20) | RSI 70/30, Stoch 80/20 | HIGH |
| S3 | PO-OTC, Deriv real-mkt | 1-5m | sweep swing extreme (N=5-10)+reclaim+micro-BOS -> reversal | at S/R or range edge | swing_lookback=5-10 | HIGH |
| S4 | Deriv real-mkt, PO-OTC | 1-5m | engulf + EMA10/20 stack -> continuation | trend (EMA10 vs EMA20) | EMA10,EMA20,engulf | HIGH(method) |
| S5 | PO-OTC | 1m | SAR flip + CCI/RSI confirm | trend, skip chop | SAR(.02,.2),CCI13/RSI14 | MED |
| S6 | PO-OTC | 1m | fractal + fast/slow MA cross | TEST trend AND range | Fractal3-5,SMA3/7 | MED |
| S7 | PO-OTC, Deriv-vol | 1-5m | BB squeeze >=5-8 bars -> close outside + widen -> break | vol-expansion | BB(20,2)/BB(13,2) | MED |
| S9 | PO-OTC | 1m | Williams%R -100->snap>-80 -> fade | range, skip if pinned | %R(10) | MED |

═══════════════════════════════════════════════════════════════════════════
## RANKED SHORTLIST -- build & backtest in THIS order
═══════════════════════════════════════════════════════════════════════════
1. **S1 Bollinger Reversion** -- highest cross-validation (5 channels + 2 books + the whole
   KB1/KB3 quant spine). Cleanest to code. The spine of the bot.
2. **S3 Liquidity-Sweep Reversal** -- only pattern where book-quant + price-action + SMC + KB8
   ALL converge. High-probability, codeable, fits binary's high-WR need.
3. **S2 RSI/Stoch Extreme** -- natural confluence layer on S1; turns S1 from single-signal to
   AND-gated (lifts selectivity = lifts WR, the whole game).
4. **S4 Engulfing+EMA** -- the ONLY setup with a real on-screen backtest (76% WR). Must re-prove
   on our assets/expiry, but it earns a slot for being the one validated entry.
5. **S7 Squeeze Breakout** -- the breakout counterpart to S1, so the bot has a setup for BOTH
   regimes (reversion when ranging, breakout when expanding) -- the regime classifier picks.

Build S1 end-to-end first (data->signal->backtest->validate->report) BEFORE adding S2-S5.

═══════════════════════════════════════════════════════════════════════════
## COVERAGE REPORT (honest)
═══════════════════════════════════════════════════════════════════════════
~6,000 transcripts across 29 channels; 6 agents read ~240 highest-signal files in depth
(~4% by file, but distinct-setup saturation was high -- these channels repeat 5-15 core setups
across thousands of re-skinned videos).
- BLW (1,652): ~14 deep + full filename/grep survey. Repetitive; saturation reached.
- SAM Trading: ~48 read -- HIGHEST per-file value, most disciplined numeric setups.
- BinaryTrader: 19/54 -- fully mechanical, best indicator-combo params.
- RockStarrFX: ~6 deep -- one coherent 3-step reversal system.
- Pivot Call, Trading Heroes, PROFIT TRADING, Pocket Option, TradingwithThan, Deriv Nav,
  binaryoptions.com, Katie, BINARY OPTIONS UK: sampled 6-48 each.
- Quant channels (Moon Dev, QuantProgram, Part Time Larry, Financial Wisdom): ~18 read -- the
  engineering gold (payout-cap, Kelly, walk-forward, kill-switch).
- Brad Goh x6: 27 read -- EdgeFlo guardrail spec is the single highest-value import.
- Alice | Binary Guides: MINED (45/73 read, ~62%) on 2026-06-22 after first agent misfired.
  ~20 distinct codeable setups -- a goldmine of cleanly-parameterized setups. See ALICE
  INTEGRATION section below. Mostly REINFORCED S1-S4; added S10 (MACD-triple-gate) + S11
  (SuperTrend+EMA150). The 28 unread = motivational/meta/live-vlog, no missed setups.
- Near-zero-value channels (confirmed): Cosmo (100% affiliate), projectoption (stock options,
  zero transfer), PZTrading (EA vendor), BINARY OPTIONS UK (music-only demos).

═══════════════════════════════════════════════════════════════════════════
## WHAT THE CORPUS DOES NOT GIVE US / OPEN RISKS
═══════════════════════════════════════════════════════════════════════════
1. ZERO verified win rates. Every number is marketing. The edge is unproven until OUR backtest.
2. No per-asset regime data. No channel says which Deriv synthetic / PO pair mean-reverts vs
   trends. We must classify each asset ourselves (Step 0).
3. The synthetic-randomness risk (biggest). Deriv volatility indices are engineered near-random
   -- mean-reversion edges may simply not exist; a naive backtest WILL curve-fit noise. Step 0
   predictability gate is mandatory before trusting any synthetic result.
4. Exact params often inferred, not stated. Many channels say "RSI/Bollinger" without numbers;
   we used standard defaults as STARTING points to optimize, not author-validated optima.
5. Sub-1-min is a different game. Traditional indicators fail <1m (PO confirms); if we ever go
   to 5-10s, only fractal/momentum apply -- separate research.
6. PO live data depth unknown. May need to record forward to hit 100k trades; honest if so.
7. Regime-conflict in S6 (trend vs range) unresolved by sources -- backtest decides.

═══════════════════════════════════════════════════════════════════════════
## ALICE INTEGRATION (added 2026-06-22, 45/73 videos mined)
═══════════════════════════════════════════════════════════════════════════
Alice = Pocket Option/Quotex, FOREX pairs only (she explicitly says NEVER OTC), payout>=80%,
multi-TF (higher TF marks level/trend, M1 times entry), default expiry 2-3m, risk <=2%.
~20 codeable setups; her house style = oscillator-cross/extreme + candlestick-at-level
confirm + EMA150/200 directional gate. Win-rate claims unverified (only 3-4 show real
backtests, all 57-67% WR = barely above breakeven -> MUST backtest).

REINFORCED (bumps confidence/support on existing Tier-1):
- S1 (BB reversion): her #15 BB(23,2)+RSI+Stoch re-entry, #14 Envelopes+RSI, #16 Keltner+RSI50.
- S2 (RSI/Stoch extreme): her #12 Triple-RSI(5/14/21), #13 Stoch+RSI50+MACD (67% WR/100 deals).
- S3 (sweep/level reversal): her #17 S/R-bounce (SUPPORT 4), #18 breakout-&-retest (never enter
  1st breakout candle), #20 supply/demand zone, #21 FVG rebound -- all the same liquidity family.
- S4 (engulfing+EMA): her #19 pullback-checklist + #24 candlestick library (engulf/star/marubozu).
- Regime filter: her global ADX<20 = NO-TRADE confirms our regime gate. Skip when MAs tangled/flat.

NEW SETUPS ADDED:
**S10. MACD Triple-Gate**  CONFIDENCE: HIGH (Alice's best-specified + only one with a real backtest)
- MACD(12,26,9) + EMA(100 or 200) + optional SAR(0.02,0.20). CALL: MACD crosses UP below zero
  line + price ABOVE EMA (+SAR dots below). PUT mirror. Expiry 3m. Trend regime. No-trade: cross
  against EMA side, chop. Real self-reported backtest: 100 trades 64W/34L +$1,720 ($100/tr, 80%
  payout, EURUSD) = ~64% WR. Worth backtesting alongside S4.
**S11. SuperTrend + EMA150 + Momentum**  CONFIDENCE: HIGH (fully mechanical)
- SuperTrend(ATR12, mult3) + EMA150. Entry: ST color flip (green->CALL/red->PUT) + price correct
  side of EMA150 + flip candle is a growing-momentum candle. Enter on close. Expiry 2m. Trend.
  No-trade: weak flip candle, signal against EMA150.

ALICE RISK NOTE: she allows max-1-step martingale -- WE REJECT (no martingale, structural). Her
own math (60% WR -> 79.9% chance of losing the base stake on a 3-streak) actually argues FOR our
fixed-stake rule. Keep our rule; her math supports it.

CAVEAT: Alice trades real FOREX pairs, NOT OTC. Her edges (if any) are on real-market microstructure
-> most relevant to Deriv real-market assets + PO real (non-OTC) pairs. On 24/7 synthetic OTC they
must be re-proven (Step 0). Her 57-67% real backtests barely clear 80%-payout breakeven (~55%) -- thin.

UPDATED SHORTLIST NUDGE: S10 (MACD-triple-gate) joins the build queue right after S4 -- it's the
2nd setup in the whole corpus with an actual trade-counted backtest. Add S10+S11 to the backtest table.

-- END KB7. This is the brain. Prompt 2 builds from the shortlist + table + engineering reqs.
   Cross-ref: KB1-3 (mean-rev math), KB4 (validation), KB8 (S3 framework), KB9/PO-target-assets
   (payout gate), DASHBOARD-SPEC, DERIV-ASSETS/PAYOUTS-REFERENCE.
