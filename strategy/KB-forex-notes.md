# KB-FOREX-NOTES (parked — for the TITAN/forex bot, NOT the options bot)

From the Brad Goh ecosystem digest (2026-06-22). These are FOREX-specific methods that do
NOT transfer to short-expiry fixed-payout binary (binary has no SL/TP, fixed expiry, capped
payout). Kept here for reference if useful to the forex side. Nothing deleted.

## Why these don't fit binary
Binary = fixed expiry + capped payout (~85-92%) + every loss -100% -> needs HIGH win rate.
Forex below = let-winners-run, big R:R, multi-bar/multi-day holds, discretionary stop moves.
Opposite math. (Their ENTRY triggers DID transfer -> see KB7 S3/S4; only the exit/bias math is parked.)

## Parked forex methods
- **SL/TP in pips** — SL beyond invalidation swing, TP at next level. (Binary has neither.)
- **R:R 1:2-1:5 + "let winners run / no partials / scale out / monster moves"** — the core
  Brad Goh exit doctrine. Their traders run 30-50% WR with big R. Invalid for fixed payout.
- **HTF top-down swing bias** — Daily/4H/Weekly premium-discount ranges as a HOLDING method.
  (The HTF-confirmation IDEA transferred to KB7; the multi-day HOLD did not.)
- **Fibonacci retracement, trendline-swing, MA-ride** — multi-bar position tools.
- **Lot-size / pip-value position calculators**, spread/leverage mechanics. (Kept only the
  pre-entry spread sanity check + the EdgeFlo guardrails for the options bot.)
- **Overnight / weekend holds**; instrument-specific reads (Gold order-flow, BTC sentiment,
  news-driven volatility plays).
- **Discretionary stop-moving** ("I've earned the right to override") — explicitly non-mechanical.

## projectoption (Chris Butler) — separate, parked
Pure STOCK OPTIONS theory: Greeks (delta/gamma/theta/vega), implied volatility, spreads, term
structure, premium selling. Zero transfer to binary OR forex price-action. If a stock-options
project ever starts, this is the source. Otherwise ignore.

## What DID transfer to the options bot (see KB7, not here)
- 3-gate confluence entry (Trading Geek) -> KB7 S1-S4 gate structure.
- Liquidity-sweep / stop-hunt reversal (Brad Trades "Entry Model #3") -> KB7 S3.
- Engulfing + candle triggers -> KB7 S4.
- EdgeFlo risk-guardrail model + EdgeScore -> KB7 Risk Governor.
- Rule-of-100, consec-loss halt, no-revenge cooldown, fixed-risk no-martingale -> KB7 Risk Governor.
