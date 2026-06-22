# Pocket Option — target assets + payouts (captured 2026-06-20, demo)

Source: PO demo trading terminal, Currencies → OTC list. Timeframe M1 available.

## Break-even math (the gate)
- Payout 92% → break-even win rate = 1 / (1 + 0.92) = **52.08%**
- Payout 91% → **52.36%** · Payout 90% → **52.63%**
- RULE: bot only trades assets paying **≥ 90%**. Anything we backtest must clear the
  break-even by a real margin (target 60%+ on filtered A+ setups).

## OTC CURRENCY pairs @ 92% (primary universe — pick the cleanest-reverting)
AED/CNY · AUD/CAD · AUD/CHF · AUD/NZD · CHF/NOK · EUR/GBP · EUR/NZD · EUR/TRY ·
GBP/JPY · KES/USD · NZD/USD · TND/USD · UAH/USD · USD/ARS · USD/CAD · USD/INR ·
USD/RUB · USD/VND · YER/USD  (all +92%)

## Slightly lower (still tradeable, >=90%)
GBP/AUD +91% · NZD/JPY +91% · AUD/JPY +90% · QAR/CNY +89% (skip, <90%)

## Not yet captured (check later if needed)
Cryptocurrencies / Commodities / Stocks / Indices OTC payouts — only pull if the
currency set isn't enough. The 92% currency list is plenty to start.

## LIVE PAYOUT GATE (user-locked rule 2026-06-20) — BOTH BROKERS
Bot MUST scan live payout on Deriv AND Pocket Option before EVERY entry. Reject below floor.
- **Normal hours: floor = 90%** (break-even WR 52.63%).
- **Off-peak / overnight (payouts dip): floor = 85%** — allowed ONLY for A+ setups
  (break-even WR 54.05%; do NOT relax setup quality to take a weak-payout trade).
- **Below 85% (the 30-40% peak-hour drops): NEVER trade. Auto-skip.**
- Rule: required WR rises as payout falls; bot must clear the current asset's break-even by
  a real margin or skip. Payout floor is a hard pre-trade filter, not a suggestion.
- Deriv NOTE: Deriv quotes payout as potential return per contract (not a flat % badge like
  PO). Bot reads Deriv's live payout field and applies the same floor. VERIFY exact field
  when building the Deriv data layer; confirm equivalence to user.
- Dashboard surfaces live payout % per asset per broker (see DASHBOARD-SPEC.md).

## Build implications
- Plenty of 92% assets -> bot can scan MANY pairs, trade only the ones currently in a
  clean mean-reverting regime (per KB3 regime filter). More assets = more A+ setups
  without overtrading any single one.
- Cross/exotic OTC pairs (USD/ARS, USD/VND, KES/USD, etc.) are synthetic feeds --
  expect strong mean-reversion but verify each on its own logged data (KB-validation).
