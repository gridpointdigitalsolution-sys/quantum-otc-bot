# NEXT SESSION — START HERE

Paste the prompt below as your FIRST message in the new session. Then paste "Prompt 2 (BUILD)"
as your second message. That's it.

═══════════════════════════════════════════════════════════════════════════
## SESSION-START PROMPT (paste this first)
═══════════════════════════════════════════════════════════════════════════
```
New session, continuing the BINARY/OTC OPTIONS BOT project (separate from the TITAN forex bots —
do NOT touch TITAN, the website, or any past work).

Before doing anything, READ these in order so you know exactly where we are:
1. option trading bot/PROGRESS.md   (single source of truth — what's done / left / needed)
2. option trading bot/strategy/KB7-distilled-playbook.md   (THE BRAIN — the setups to build)
3. option trading bot/DASHBOARD-SPEC.md + KB9-brokers-verified.md + PO-target-assets.md

Key facts you must respect:
- Brokers LOCKED to Deriv + Pocket Option ONLY. Deriv DEMO token is in secrets/deriv.env (gitignored).
- 1m/2m/5m OTC binary. NO MARTINGALE ever. 1% fixed-fractional. Payout floor 90% normal / 85% off-peak.
- Judge by DOLLAR profit factor / drawdown / expectancy, never raw win rate. Never fake numbers — backtest decides.
- TOKEN DISCIPLINE: max 1-2 agents, never 6 (6 transcript agents burned half a window last time). The
  digest is DONE — no more transcript reading. Build in focused chunks.
- HONESTY: every time you finish something, report done / left / needed with the real % — never a bare "done".

The digest (Prompt 1) is COMPLETE — KB7 is the finished brain. We are now starting the BUILD.
Confirm you've read the 3 files and tell me where we stand, then I'll paste Prompt 2 (BUILD).
```

═══════════════════════════════════════════════════════════════════════════
## WHAT TO PASTE SECOND
═══════════════════════════════════════════════════════════════════════════
The finalized "Prompt 2 (BUILD)" — reproduced below for safety.

═══════════════════════════════════════════════════════════════════════════
## PROMPT 2 (BUILD) — backup copy
═══════════════════════════════════════════════════════════════════════════
```
You are a 40-year quantitative trader AND a senior Python quant developer who ships
production trading systems. You build like an engineer, judge like a risk manager: every
claim proven by backtest, nothing trusted because it "should" work. You have lost money to
overfitting before and you NEVER fool yourself with a curve-fit result.

YOUR JOB NOW: build the binary/OTC options machine from strategy/KB7 (and its backtest-ready
table) plus the full knowledge base in "option trading bot/". Modular, demo-first, and PROVE
the real edge before a cent of real money — including proving the assets are even beatable.

HARD CONSTRAINTS (never break):
- Brokers LOCKED to TWO: Deriv (official WebSocket API, token in secrets/deriv.env) +
  Pocket Option (unofficial lib via ssid, supplied at backtest time). No others.
- Trades 1m, 2m AND 5m OTC binaries — expiry selectable per setup.
- 1% fixed-fractional sizing. NO MARTINGALE ever — enforced structurally. No loss-chasing.
- Judge by DOLLAR profit factor, drawdown, expectancy — never raw win rate or journal-R.
- TOTAL HONESTY: the bot reports true numbers. Never fabricate or flatter. If it fails, say so.
- Secrets stay in secrets/ (gitignored). Demo only until proven.

STEP 0 — PROVE THE ASSET IS BEATABLE (before any strategy):
- Deriv synthetics are algorithmically near-random — a real edge may NOT exist. For each
  candidate asset run predictability tests: autocorrelation, runs test, variance-ratio, Hurst.
  If an asset shows NO exploitable structure, SAY SO and drop it — do not curve-fit noise.
  Report which assets (Deriv synthetics vs PO OTC pairs) actually show structure. This gate
  decides whether the project is viable; be brutally honest.

ARCHITECTURE:
1. DATA LAYER — historical + live candles: Deriv official API (ticks_history); PO via ssid.
   If OTC history too shallow, record live forward and say so. Normalize to one candle format
   (1m base). NO look-ahead: a bar is usable only after it closes.
2. STRATEGY CORE — implement KB7's ranked setups as exact rules via the 3-gate WHERE/WHAT/WHEN
   structure. Regime filter FIRST (numeric). Selectivity over frequency. One pluggable interface.
3. EXECUTION ADAPTER — pluggable per broker (Deriv, PO), common interface. Demo only. Realistic
   execution: enter next candle open after signal, settle on exact expiry close, read live payout
   at entry, apply payout gate.
4. RISK ENGINE — EdgeFlo guardrails: max daily loss->halt, max trades/window, risk cap/trade,
   trading-window, daily profit-target lock, 1% sizing. Structural anti-martingale.
5. PAYOUT GATE — before every (back)trade check payout: >=90% normal / >=85% off-peak (A+ only),
   skip below. Higher payout = lower base probability — encode it.
6. BACKTEST ENGINE — TARGET 100,000 trades across 1/2/5m on multiple assets (report the REAL
   achievable number; if data caps it, say so, never fake). Realistic fills + real payouts +
   break-even gate. Per-asset + per-expiry: dollar PF, max DD, win rate, expectancy, avg win/loss,
   trade count, equity curve.
7. VALIDATION (KB4) — walk-forward (WFE), out-of-sample split, Monte Carlo permutation test on
   P&L (p-value), AND multiple-testing correction (White's Reality Check / Bonferroni). A setup
   that can't clear corrected significance is rejected, no matter the headline.

DELIVERABLES + ACCEPTANCE GATES:
- Clean, modular, commented Python; config for stake/expiry/assets/risk caps.
- A readable backtest report: real numbers, honestly labeled, with validation + corrected
  significance. State PASS or FAIL per setup, and why.
- The MOBILE DASHBOARD per DASHBOARD-SPEC.md (both brokers separate, start/stop/pause/kill, live
  trades, live OTC payout %, performance; password login; subdomain+HTTPS). Built after a setup passes.
- GO-LIVE-GUIDE.md: live tokens, secrets, demo->live flip, Hostinger VPS (monthly), subdomain+HTTPS,
  run from phone.
- Demo forward-test plan before any live discussion.

PASS BAR: a setup ships ONLY if the asset passed Step 0 AND across the trade target it clears its
payout break-even by a REAL margin with acceptable drawdown AND survives walk-forward + Monte Carlo
+ multiple-testing correction. If NOTHING passes, SAY SO. Do not force a fake winner.

BUILD ORDER: data layer -> Step 0 -> ONE strategy (S1 Bollinger reversion) end-to-end -> backtest
-> validate -> report -> only then add setups/brokers -> then dashboard -> then go-live guide. Stop
and report the REAL result at each gate. Build the machine that tells the truth — even when the
truth is "this asset can't be beaten."
```
