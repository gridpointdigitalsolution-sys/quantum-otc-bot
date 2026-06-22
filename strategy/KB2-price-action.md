# KB2 — Bob Volman Price Action (Codeable Logic for a 1–5 min Binary/Fixed-Time Bot)

Source: *Forex Price Action Scalping* (70-tick eur/usd, 20 EMA) + *Understanding Price Action* (5-minute eur/usd, 25 EMA).
Both books are the SAME method at different speeds. For a 1–5 min options bot use the **5-minute UPA framework** as the primary timeframe (25 EMA), and treat the scalping-book setups (DD/FB/SB/BB/RB) as the entry-trigger library.

Goal of this file: at the moment of a candle close, output **UP / DOWN / NO-TRADE** for the next 1–5 minutes based on whether a *with-trend pullback break* (high probability) or a *false break* (high probability reversal) is firing.

---

## 0. CORE PHILOSOPHY (drives every rule below)
- **Trade WITH the dominant pressure, after a pullback peters out.** Highest-probability event in the method = enter with-trend the moment a stalling pullback breaks back in the trend direction.
- **Direction is decided by the trend + the pullback exhaustion, NOT by the entry candle alone.** A single candle never decides direction; the *context* (trend + pullback + break) does.
- He targets ~10 pip with ~6–7 pip avg risk → he only needs to be right ~40%+ to profit. **For a binary bot you need >50% directional hit-rate in the next N minutes, so only take the A-grade conditions in §7.**

---

## 1. TREND / DOMINANT PRESSURE (the directional bias filter — MUST compute first)
Compute on the working timeframe (5-min). Direction of the *next* move strongly favors the dominant pressure.

Codeable proxies (combine; require agreement):
```
ema = EMA(close, 25)            # 5-min;  use EMA(close,20) on faster frames
bias_up   = close > ema  AND ema_slope_up   AND (count_higher_highs+higher_lows > count_lower_highs+lower_lows)
bias_down = close < ema  AND ema_slope_down AND (count_lower_highs+lower_lows > count_higher_highs+higher_lows)
```
- `ema_slope_up = ema[0] > ema[3]` (rising over last ~3 bars). Down = inverse.
- Swing structure over last ~18 bars (≈ 1.5 hrs on 5-min — Volman's stated lookback): **more higher-highs/higher-lows than lower-highs/lower-lows ⇒ pressure UP**; inverse ⇒ DOWN; alternating ⇒ NO bias (skip).
- **EMA is a guide, not a barrier.** Price may pierce it; do not require an exact touch. Strong spikes leave the EMA lagging.
- If `bias_up == bias_down == false` (range/choppy) → only Range-Break / Block-Break logic (§5–6) applies, never with-trend pullback trades.

---

## 2. PULLBACK QUALITY (the setup must form INSIDE a valid pullback to the EMA)
A with-trend entry is only valid when a corrective swing against the trend has stalled, ideally near the 25/20 EMA.

Valid pullback (for a downtrend short; mirror for long):
- Retraces **~40–60%** of the prior with-trend leg (`0.35 ≤ retrace ≤ 0.70` acceptable; >70% lowers odds).
- **One-directional / diagonal**: pullback candles mostly the *opposite* color of the trend leg (downtrend → pullback prints mostly bullish/white bodies). Count: `opp_color_bodies / pullback_len ≥ 0.6`.
- **No interruption**: in the pullback, no candle's extreme is broken in the trend direction *until* the signal bar appears (i.e. in a bullish pullback, no candle low is taken out until the turn).
- Reaches the **EMA area** (within ~1×ATR of EMA). "Area," not exact touch.
- **First pullback** of a fresh trend = strongest (FB-eligible). Later pullbacks fight harder → prefer SB (§4).

`bad_pullback`: bars TALLER than the trend leg's bars (countertrend strength), or block/horizontal shape with no clear angle, or retrace >70% → downgrade or skip.

---

## 3. ENTRY TRIGGER PRIMITIVES (the actual break mechanics — all boolean)
Everything keys off **"a bar takes out the high/low of a prior signal bar/line by ≥1 pip."**

```
doji(bar)        = abs(close-open) ≤ 0.30 * (high-low)        # small/indecision body
bull_body(bar)   = close > open
bear_body(bar)   = close < open
breaks_up(b,sig)   = b.high > sig.high          # ideally +1 pip
breaks_down(b,sig) = b.low  < sig.low
signal_bar_short = the bar at the TOP of a stalling pullback whose LOW gets taken out
signal_bar_long  = the bar at the BOTTOM of a stalling pullback whose HIGH gets taken out
```
- **Signal bar must be small/compressed** relative to neighbors. Hard cap in scalping book: signal bar ≤ 7 pip tall (so a ~10 pip stop fits). Reject "biggest bar in the neighborhood" signals — they are not compression.
- **Equal extremes = a signal LINE**: 2+ neighboring bars (often dojis) sharing the same high (for shorts) or low (for longs). Breaking the shared level is the trigger. More equal touches = stronger.
- Enter on the **break of the signal bar/line in the trend direction**, the moment it happens (next-bar open often gaps through it).

---

## 4. THE FIVE SETUPS (entry-trigger library — each is a boolean detector)

### DD — Double Doji (with-trend, fastest)
Two (or more) neighboring **dojis** with ~equal trend-side extremes, sitting in the EMA at the end of a pullback. Enter on break of the shared extreme in the trend direction.
```
DD_short = bias_down AND valid_pullback_up AND near_ema
           AND len(neighbor_dojis_equal_highs) ≥ 2
           AND dojis_are_compressed (smaller than surrounding bars)
           AND next_bar.low < dojis.min_low
```
Reject if the two bars are tall/uncompressed, or if a round number / price cluster sits directly in the path to target (§8).

### FB — First Break (with-trend, high-conviction)
The **first** pullback to a sharp, one-directional trend that burst out of consolidation. Enter the instant the *first* pullback bar is broken in trend direction. Requires all 3: (1) abrupt one-directional trend leg (long bodies closing on their extreme), (2) firm straight pullback to EMA area, (3) it is the FIRST pullback of that trend. Signal bar ≤ 7 pip. Skip FB if any condition weak → wait for SB.

### SB — Second Break (with-trend, MOST RELIABLE / preferred)
Two FBs in a row: first break fails → pullback re-tests EMA → second break fires. Forms a **double top (M) at top of bullish pullback** (short) or **double bottom (W) at bottom of bearish pullback** (long).
```
SB_short = bias_down AND pullback_up_to_ema
           AND first_break_down_then_recovery (failed FB)
           AND second_push_up makes ~equal-or-lower high vs first (M-top, doesn't exceed prior high much)
           AND a bar then breaks_down the second signal bar
```
- Volman's stated edge ranking: **SB > FB** (double/triple top is a stronger tell than a single top). Skip most FBs *in favor of* the SB.
- Invalidation of SB premise: the second low (in W) should TEST the first low (~same level). If you'd be entering ~7 pip away with no test of the prior low/EMA → not high probability, skip.

### BB — Block Break (multi-purpose; works in trend OR range)
A tight cluster of bars in a narrow vertical span (a mini-range) with ≥1 horizontal barrier of equal touches. Enter on break of the box barrier in the favorable direction.
```
block = ≥4 bars within a span ≤ ~5–6 pip, with top OR bottom barrier having ≥2-3 equal touches
BB_long = bias_up (or range w/ higher-bottom in box) AND block AND next_bar.high > box_top
```
- Best BBs: the EMA literally pushes price out of the box (EMA rising into box bottom for a long).
- A **higher bottom inside the box** (long) / **lower top inside the box** (short) = strong confirming tell.
- "Whatever is compressed will eventually unwind." Longer the barrier holds → sharper the break.

### RB — Range Break
A well-respected range (2+ touches each barrier) that finally breaks **with buildup** at the broken barrier. Same buildup rule as below — no buildup = likely false break.

---

## 5. BUILDUP & BREAK QUALITY (the single biggest probability filter — from UPA Ch.2)
**Avoid every break that is not built up.** Three break grades:
| Grade | Condition | Action |
|---|---|---|
| **Proper break** | Tight sideways **buildup cluster right AT the barrier** before the break; stop fits tightly just past the buildup | TRADE (with-trend) |
| **Tease break** | Some buildup but not at the barrier; protective level is far | Marginal — expect a counter back into range first; tight-stop risk |
| **False/Non-buildup break** | Bar breaks out with NO preceding buildup at the level | DO NOT trade for continuation; expect FAILURE (fade candidate) |

Codeable buildup detector at a barrier:
```
buildup = last K bars (K≈3–6) before break are small-range AND clustered within ~3 pip
          AND sit directly against the barrier being broken
proper_break  = break_of_barrier AND buildup AND with_dominant_pressure
nonbuildup_break = break_of_barrier AND NOT buildup   # high failure probability
```
**Rule of thumb for failure:** the more extended the prior move AND the poorer the break is built → the higher the chance it gets countered (reverses). This is the bot's main *reversal* signal.

---

## 6. FALSE BREAK / FALSE HIGH-LOW (the high-probability REVERSAL trigger)
A **false break** traps everyone who traded the break → they must exit in the opposite direction → fuels the reverse move. This is the most reliable reversal pattern and is directly tradeable as a *countertrend* fixed-time entry when it occurs at a key level.

```
false_high = bar breaks a prior high  THEN next bar is opposite-color AND its low gets taken out
false_low  = bar breaks a prior low   THEN next bar is opposite-color AND its high gets taken out
```
Highest-value false breaks (take these as REVERSAL signals):
- A break **against the dominant pressure** that fails (e.g. in a downtrend, a bullish poke above a pullback high that immediately gets slammed back below → strong SHORT). This is exactly how Volman's best SB shorts complete.
- A false break of a **round number** (§8) or a clearly defended barrier with multiple prior touches.
- A break that occurred with **no buildup** (§5) → expect reversal.

`false_high in resistance` → next move DOWN. `false_low in support` → next move UP.
A false high/low *in line with* the trend (top of an up-leg) = only a minor momentum stall (expect a pullback, not a reversal) — weaker signal.

---

## 7. PROBABILITY: what RAISES vs LOWERS odds of continuation (bot scoring)
**RAISES odds the directional move continues (score +):**
- Break is **with dominant pressure** AND has **buildup** at the barrier (§5).
- Setup sits **in/at the EMA** at the end of a clean 40–60% diagonal pullback (§2).
- Signal is **SB / DD with equal extremes** (multiple touches) vs a lone bar.
- Trend leg was **one-directional with long bodies closing on extremes** (FB-quality origin).
- **Clear path to target** — no clusters / round numbers / opposite-side EMA in the way (§8).
- "**Trend equals trend**": after a strong first leg, the second leg tends to mirror it → expect similar-size continuation.
- **Double pressure** present (with-trend entries + countertrend exits both push same way) — e.g. false break that just trapped the other side.

**LOWERS odds / NO-TRADE (score − / veto):**
- **No buildup** before the break (non-buildup break) → likely false.
- Pullback bars **taller** than trend bars, or retrace **>70%**, or block-shaped not diagonal.
- A **round number, price cluster, or prior pullback level** sits between entry and target (chart resistance/support in the path).
- Break drives **straight into** a round number / opposite EMA.
- **Second-or-later** pullback being traded as an FB (FB only valid on first pullback).
- **Range / choppy** (no EMA bias, alternating swings) → skip all with-trend logic.
- **Bad conditions**: news spike, widened spread, dead session (lunch doldrums) → flat. (Volman: don't trade the wider-spread / news windows.)

Suggested gate: take a directional binary trade only when (with-trend setup AND buildup AND clean path) **OR** (clean false break at a defended level/round number). Otherwise NO-TRADE.

---

## 8. ROUND NUMBERS & SUPPORT/RESISTANCE (path & level logic)
- **00 (full cent) and 50 (half cent) levels** are the most defended zones. Treat as **zones**, not exact pips.
- **Vacuum/magnet effect**: when price is near a round number with little between, it tends to get pulled to it → short-term directional bias toward the level.
- Round number can hold even after being breached by a few pip. Don't trade a with-trend DD *straight into* a round number (participation too thin). Prefer to be positioned a pip on the *near* side of it.
- **Cracked support → becomes resistance; cracked resistance → becomes support.** First retest of a broken level from the other side is a high-odds fade in the trend direction (do NOT buy into first test of broken support-now-resistance).
- **Any cluster of bars** above a long-entry / below a short-entry = resistance/support in the path → lowers continuation odds.
- **Tests**: price returning to a prior high/low/level "to the pip" and holding = confirmation; a break that fails the test = reversal tell.

---

## 9. EXIT / VALIDITY (for a fixed-time bot, mostly informational, but the "tipping point" defines invalidation)
- Binary/fixed-time: position auto-resolves at expiry, so the main use is **expiry sizing** ≈ enough bars to reach ~10 pip (Volman's target). On 5-min, that's typically the next **1–3 bars**; set expiry 3–5 min.
- **Tipping point** = the pip level (just past the signal bar / pattern extreme) beyond which the setup is invalid. If price violates it *before* the move develops, the directional thesis is dead — for a martingale/again-entry bot, treat tipping-point violation as "thesis failed, do not re-enter same direction."
- Expect a **pullback/retest of the break level** on a large fraction of valid trades — a small adverse excursion right after entry is normal and does NOT invalidate as long as the tipping point holds. (Don't design the bot to bail on the first tick against it.)
- Never widen the target; the directional edge is in the *entry context*, not in holding longer.

---

## 10. PSEUDOCODE — directional decision at each bar close
```python
if bad_conditions(): return "NO_TRADE"             # news / wide spread / dead session
bias = trend_bias()                                # §1  -> UP / DOWN / NONE

# A) WITH-TREND continuation (preferred)
if bias != NONE and valid_pullback(bias) and near_ema():
    if (DD() or FB_first_pullback() or SB() or BB()) and buildup_at_signal() and clean_path(bias):
        if confirm_break(bias):                    # signal bar/line taken out in trend dir
            return "UP" if bias==UP else "DOWN"

# B) FALSE-BREAK reversal (only at defended level / round number, against an exhausted move)
if false_break_at_key_level():                     # §6 + §8
    return "DOWN" if false_high_in_resistance() else "UP"

# C) RANGE: fade barriers only with buildup-failure (false break); break only with buildup
return "NO_TRADE"
```

---

## 10-LINE SUMMARY — most codeable, highest-probability setups
- **SB (Second Break)** is the flagship: in a trend, a failed first break then a second break of an M-top (short) / W-bottom (long) at the EMA → enter trend direction. Highest reliability.
- **DD (Double Doji)**: ≥2 neighboring compressed dojis with equal trend-side extremes in the EMA at a 40–60% pullback → break of the shared extreme = with-trend entry.
- **FB (First Break)**: only on the FIRST pullback to a sharp one-directional trend; break first pullback bar in trend direction. Skip if not textbook.
- **Direction = dominant pressure** (close vs 25/20 EMA + EMA slope + more HH/HL than LH/LL), set BEFORE looking at the entry candle.
- **Buildup is the master filter**: trade breaks only when a tight cluster sits AT the barrier; a **non-buildup break = expect failure** (fade it).
- **False high/low** is the reversal trigger: break of a high/low that immediately reverses (opposite-color bar + its extreme taken out) → trade the reverse, strongest at round numbers / defended levels.
- **Signal bar must be small/compressed** (≤7 pip; smaller than neighbors); equal extremes across 2+ bars form a stronger "signal line."
- **Round numbers (00 & 50)** act as zones: magnet/vacuum pull toward them, defense at them; don't trade straight INTO one; first retest of a cracked level fades in trend direction.
- **Boost odds**: clean path to ~10 pip (no clusters/round numbers in the way), one-directional trend leg with long bodies, "trend-equals-trend" mirroring, double pressure from a just-trapped opposite side.
- **Kill odds (NO-TRADE)**: no buildup, pullback >70% or taller-than-trend bars, range/choppy (no EMA bias), path blocked, second-or-later pullback traded as FB, or bad spread/news conditions.
