# KB8 — WHERE / WHAT / WHEN entry framework (3-gate architecture)

Source: public "WHERE-WHAT-WHEN" infographic (ICT/SMC style), captured 2026-06-20.
Used as the bot's ENTRY DECISION STRUCTURE. Aligns with KB2 (Volman) + KB3 (z-score).
NOTE: only the framework is adopted -- the "Musa Trading Academy" VIP/robot claims
(e.g. $100->$870/mo) are unverified marketing and are NOT used.

## The 3 gates -- a trade fires ONLY if all three pass, in order

### Gate 1 -- WHERE (zone of interest) -- is price at a meaningful level?
- High-volume / value zones
- Previous high / previous low (session, prior-day)
- Order blocks (last opposite candle before an impulsive move)
- Support & resistance, round numbers (00 / 50) [KB2]
- Quant version: price at a statistical extreme -- z-score >= 2 vs moving mean,
  or pierce of double-Bollinger outer band [KB1/KB3]
=> If price is NOT at a zone, NO TRADE (this is the selectivity filter that lifts win rate).

### Gate 2 -- WHAT (manipulation) -- did the level get defended / liquidity taken?
- Fakeout / false break of the level (Volman false-break) [KB2]
- Liquidity grab / stop hunt: wick pierces beyond zone then snaps back
- Order accumulation: tight cluster/buildup at the level [KB2 buildup]
=> Confirms the level is real and big players defended it. A clean break WITHOUT this =
   skip or trade the failure.

### Gate 3 -- WHEN (entry trigger) -- exact execution candle
- Clean rejection wick off the zone
- Candlestick pattern: pin bar / engulfing / signal-bar [KB2]
- Zone defense: price holds and turns
- Candle CLOSE back inside the band / beyond the trigger level (close-confirmation)
=> Direction: reject upper zone -> PUT/SELL ; reject lower zone -> CALL/BUY.
=> Expiry: set by half-life (KB3), typically 1-5 min.

## Why this raises win rate (the honest logic)
Requiring all 3 gates = far fewer trades, but each is an A+ mean-reversion-at-extreme
with confirmation. This is the selectivity that the books say is the only real path to
60%+ on short-expiry binary. Frequency drops; accuracy rises. No martingale.

## Build mapping
Gate1 = regime + extreme detector (BB/z-score/Hurst, round-number proximity)
Gate2 = false-break / wick-rejection detector over last 1-3 bars
Gate3 = signal-bar + close-confirmation -> emit CALL/PUT + expiry
