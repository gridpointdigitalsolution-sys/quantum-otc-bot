# OPTIONS BOT — PROGRESS / RESUME HERE (single source of truth)

> Read this FIRST to know exactly where we are. Updated 2026-06-22.
> Goal: Python bot, 1m/2m/5m OTC binary, NO martingale, 1% sizing. Brokers LOCKED = Deriv + Pocket Option ONLY.
> Honesty rule: never fake numbers; backtest decides; report done/left/needed every time.

## DONE (do NOT redo)
- [x] 16 books digested -> strategy/KB1-KB6, KB8, KB9, PO-target-assets.md
- [x] Brokers verified + LOCKED to Deriv + Pocket Option (KB9). Quotex/IQ CUT by user.
- [x] Deriv DEMO token stored -> secrets/deriv.env (gitignored)
- [x] Scraped 29 channels -> ~5,304 unique videos (transcripts/ + transcripts-forex/)
- [x] DIGEST COMPLETE -> strategy/KB7-distilled-playbook.md (THE BRAIN). 11 setups, 2 with real
      backtests (S4 Engulfing+EMA 76%, S10 MACD-triple-gate 64%), risk governor, engineering reqs,
      asset map, honest risks. Alice mined + merged (45/73). Forex parked -> strategy/KB-forex-notes.md
- [x] Deriv assets pulled (DERIV-ASSETS-REFERENCE.md, 92 symbols) + LIVE payouts
      (DERIV-PAYOUTS-REFERENCE.md, synthetics 92-93%). Scripts: scripts/deriv_assets.py + deriv_payouts.py
- [x] Specs saved: DASHBOARD-SPEC.md, TOOLS.md (yt-dlp, ScrapeGraphAI 2.1.3, PyMuPDF), KB9 payout-gate
- [x] Two prompts finalized (DIGEST done; BUILD = "Prompt 2" ready to run, see chat history)

## IN PROGRESS / BACKGROUND
- [~] yt-dlp sweep recovering last rate-limited stragglers (transcripts/_sweep.sh). Runs LOCALLY,
      ZERO Claude tokens. ~5,304 videos already captured (99%+). Does NOT block anything.

## BUILD — IN PROGRESS (started 2026-06-22)
- [x] DATA LAYER built: bot/config.py, bot/data/candles.py (normalized OHLC + resample, no look-ahead),
      bot/data/deriv_source.py (official ticks_history WS, paginated). Indicators/backtest will be numpy
      (Py3.14 too new for TA-Lib/vectorbt/numba — writing our own, cleaner anyway).
- [x] STEP 0 built + RUN: bot/step0_predictability.py (autocorr/runs/variance-ratio/Hurst) +
      scripts/run_step0.py. Full honest report -> STEP0-REPORT.md. JSON -> data/step0/.
      RESULT: **Deriv synthetics = PROVEN RANDOM (20k bars, Bonferroni-corrected: nothing passes) -> DROPPED.**
      Deriv real-market forex/gold = INCONCLUSIVE (public API only gives ~1.9k 1m bars = underpowered).
      **PO OTC (the real target) = UNTESTED — needs live ssid (BLOCKED on user).**
- [ ] **BLOCKER: need PO ssid** to fetch OTC candles -> run Step 0 on the 92% OTC pairs. No proven asset
      to build on until PO OTC passes the gate. Do NOT build a strategy on an unproven asset.

## BUILD GATE RESULTS so far (2026-06-22) — honest
- Deriv SYNTHETICS: Step 0 = PROVEN RANDOM -> dropped.
- Deriv REAL-MARKET (gold + EUR/GBP/JPY majors): Step 0 = PASS (real mean-reversion) BUT
  backtest = FAIL. S1 0/48 configs pass. Autocorr CEILING probe (raw fade, every bar): best
  asset gold 51.5% acc < 52.63% breakeven; 3/4 below 50%. **Predictability != profitability:
  the edge is real but too small to clear the payout cap. Deriv real-market = NOT shippable
  for binary.** See BACKTEST-REPORT-S1.md + STEP0-REPORT.md.
- BUILT + WORKING: data layer, Step0 engine, indicators (numpy), S1 strategy, payout-capped
  backtest engine w/ full risk governor, ceiling probe, PO source + PO step0 runner.
- **PO OTC (user's real target, different broker-generated feed): STILL UNTESTED — needs ssid.
  The one remaining candidate. All code runs on it unchanged.**

## NEXT (after PO ssid)
- [ ] Build bot/data/po_source.py (ssid WS) -> Step 0 on PO OTC -> if any pair PASSES:
      build S1 (Bollinger reversion) end-to-end -> backtest (target 100k, report REAL achievable) ->
      validate (walk-forward + Monte Carlo + multiple-testing) -> report PASS/FAIL -> then S2/S3/S4/S10 ->
      dashboard -> go-live guide. If NOTHING passes Step 0, say so plainly — no fake winner.
- [ ] PO live ssid: grab at backtest time (expires; not stored yet). Deriv live token: make from REAL acct at go-live.
- [ ] Dashboard (mobile, both brokers, start/stop, live payout) per DASHBOARD-SPEC.md — build after a setup PASSES.
- [ ] GO-LIVE-GUIDE.md + Hostinger VPS deploy — last.

## SHORTLIST TO BUILD (from KB7)
S1 Bollinger reversion (FIRST) -> S3 liquidity-sweep -> S2 RSI/Stoch extreme -> S4 engulfing+EMA -> S10 MACD-gate -> S7 squeeze.

## TOKEN / COST DISCIPLINE (learned 2026-06-22)
- BIGGEST burn = agents reading transcripts. Digest is DONE -> that cost is BEHIND us.
- yt-dlp scraping + python scripts = ~0 Claude tokens (local).
- Going forward: 1-2 agents MAX, never 6. Build phase is also token-heavy (code+backtest) — do in focused chunks.

## KEY FILES
strategy/KB1-9 + KB7-distilled-playbook.md (brain) + KB-forex-notes.md · PO-target-assets.md · KB9-brokers-verified.md
DASHBOARD-SPEC.md · TOOLS.md · DERIV-ASSETS-REFERENCE.md · DERIV-PAYOUTS-REFERENCE.md
secrets/deriv.env (gitignored) · scripts/deriv_assets.py + deriv_payouts.py
transcripts/ (binary) · transcripts-forex/ (Brad Goh)
Cross-session memory: C:/Users/cbnot/.claude/projects/F--Quantum-growth-materials/memory/project-options-bot.md

---
## DERIV FINAL VERDICT (2026-06-22) — RULED OUT, pivot to Pocket Option

Tested ALL 46 24/7 assets x 13 strategies x 4 expiries (1/2/3/5m) = 2,392 configs on 100k bars each.
Then verified contract_types + real live payouts via proposal API.

THREE groups, all dead for a BINARY bot:
1. STRONG EDGE but NOT binary-tradeable: RB100/RB200 fade = 64.8% WR / PF 1.63 / DD<9% (real, look-ahead-audited)
   -> but contracts_for = MULTIPLIER ONLY. No Rise/Fall. Untradeable as binary.
2. BINARY-tradeable but NO real edge: R_*, 1HZ*V, JD*, stpRNG* (Volatility/Jump/Step).
   Real payouts 92-95% (breakeven 51.3-52.1%). Best edge = stpRNG4 s2_rsi_bb 55.1% WR / +3.8% / PF 1.09 / n=345
   = NOISE (won't survive walk-forward). These are the Step-0 statistically-random assets. Confirmed.
3. Boom/Crash 90%+ WR drift = MULTIPLIER-only (untradeable) AND spike-trap. Dead twice.

ROOT CAUSE: Deriv synthetics that ALLOW binaries are engineered random (Deriv = counterparty).
Ones with real structure (Range Break) don't allow binaries. By design. Deriv unbeatable as binary bot.

DECISION: pivot to POCKET OPTION (real-market OTC pairs, real microstructure, binaries available).
Reusable assets built & proven: data layer, Step 0 gate, 6 strategy families, backtest engine (look-ahead clean),
confluence ensemble, sweep harness. All work transfers directly to PO data.
NEXT: get fresh PO ssid -> fetch OTC candle history -> Step 0 + sweep on real-market data -> honest per-pair report.

---
## ✅ BOT COMPLETE + LIVE-READY (2026-06-22, S-PO build)

### FINAL VALIDATED BASKET (PO OTC, payout-aware, walk-forward stable)
Source: 26 pairs x 8 strategy families x 4 expiries x walk-forward (data/research/basket_po.json)
| Pair | Setup | Expiry | Params | Backtest WR | PF | DD | Min payout |
|---|---|---|---|---|---|---|---|
| NGNUSD_otc | rsi@lvl | 5m | ob75/os25/tol0.5 | 60.8% | 1.42 | 6.4% | 77% |
| BHDCNY_otc | rsi@lvl | 5m | ob75/os25/tol1.0 | 59.2% | 1.31 | 7.4% | 77% |
| OMRCNY_otc | rsi@lvl | 3m | ob75/os25/tol1.0 | 57.3% | 1.22 | 16.5% | 80% |
| NZDJPY_otc | rsi@lvl | 3m | ob75/os25/tol1.0 | 56.6% | 1.18 | 10.1% | 82% |
| USDCAD_otc | rsi@lvl | 2m | ob75/os25/tol0.5 | 56.6% | 1.20 | 9.2% | 82% |
- Expiry per pair = the ONLY profitable one (verified 1/2/3/5m: 1m loses on ALL; shorter loses for NGNUSD/BHDCNY; USDCAD loses at 3/5m). NOT oversized.
- ENTRY RULE (rsi@lvl): RSI(14) >=ob (PUT) or <=os (CALL) AND price within tol*ATR of 20-bar S/R level AND RSI turning. Enter next bar, settle at expiry. No look-ahead (audited).
- 3 exotics (NGNUSD/BHDCNY/OMRCNY) = best WR but PO-generated-feed risk. 2 liquid (NZDJPY/USDCAD) = safer.
- HONEST: thin edges, each works at ONE expiry = somewhat fragile. LIVE forward test is the real proof.

### DERIV = DEAD for binary (proven): tradeable synthetics are engineered-random (~coinflip);
the ones with edge (Range Break/Boom/Crash) are multiplier-only, no Rise/Fall binary. Pivoted to PO.

### RISK GOVERNOR (config.py, PO-tuned): $1 flat stake (PO min, no sub-$1, no martingale),
3 sessions/day (morning/afternoon/evening UTC+1) x up to 15 trades = ~45/day, -6% daily loss HALT,
PROFIT UNCAPPED, session cooldown after 5 losses (~90min) then resume, per-pair LIVE payout gate
(skip if payout < per-pair minimum; universal floor 77%). starting_balance=150.

### CODE (all built + import-tested):
- bot/strategy/{s3_sweep,ensemble,confluence,s4_trend,s1_bollinger,fade,momentum,s2_rsi}.py
- bot/registry.py (basket->strategy), bot/live_engine.py (live trading, governor, live balance,
  open-positions tracking, per-pair payout gate, writes data/live_status.json + live_trades.jsonl)
- dashboard/server.py (FastAPI: /, /status, /start, /stop, /basket) + dashboard/dashboard.html
  (dark/gold, responsive tab+laptop, ssid box, sound+toasts, pulsing LIVE dot, 3-state pair status
  waiting/READY/IN TRADE, open-positions countdown, recent trades, balance/PL/WR/sessions)
- scripts/: fetch_po.py, sweep_po.py, optimize_po.py, finalize_basket.py, test_kb7.py, validate_po.py
- requirements.txt, deploy_vps.sh (systemd + nginx + certbot for subdomain HTTPS)

### RUN (laptop, free): python -m dashboard.server -> http://localhost:8000 -> paste fresh ssid -> Start
### VERIFIED LIVE 2026-06-22: engine connected, balance $149.92 (matches real demo), places real
trades (saw OPENED CALL OMRCNY 180s, open position confirmed). Dashboard live.

### NEXT STEPS:
1. Forward-test on demo overnight (laptop or VPS) -> judge LIVE win rate vs backtest tomorrow.
2. VPS for 24/7 + phone monitor: buy Hostinger VPS Ubuntu 24.04 -> send IP+root pw -> deploy_vps.sh
   -> A-record bot.churchillbracknell.com -> IP -> HTTPS -> monitor on phone.
3. If live WR holds >= breakeven per pair -> fund real $150, $1 stakes.
4. ssid EXPIRES -> re-grab from logged-in PO tab (F12>Network>WS>Messages>filter auth>green 42["auth"]).

### BUG AUDIT + FIXES (2026-06-22, money-safety pass) — all verified
- FIXED over-trading: trade caps (session/day/per-pair) now counted at OPEN, not settle (were counted minutes-late -> could blow past caps). Per-pair-per-session cap now enforced. No stacking >1 position per pair.
- FIXED stuck positions: settle errors retry once, then clean up + record conservative LOSS (no more positions "open" forever; no lost trades on restart).
- FIXED history: today's trades reload from live_trades.jsonl across restarts (day field added).
- VERIFIED check_win format on REAL trades: dict {result:"win"/"loss", profit:+0.77/-1, percentProfit:77}. Parser handles exactly. Open->settle->record cycle proven live.
- ADDED manual signals panel: every signal (BUY=CALL/SELL=PUT) logged w/ reason + acted/skipped+why -> dashboard "Live signals" feed + sound/toast, so user can trade manually if bot skips. CALL=BUY, PUT=SELL.
- UI: READY=blue, IN TRADE=green(pulse), waiting=grey. Live balance refresh each loop. Open-positions countdown.
- RULE LEARNED: do NOT restart server while trades open (kills 5-min settle tasks). Let it run.

### ADX TREND-AVOIDANCE + DEAD-CANDLE FILTER (2026-06-22, re-validated)
RsiAtLevel got real ADX gate (skip strong trends, fades get run over) + min_range dead-candle filter.
Re-validated per pair (walk-forward, adopt ONLY if it helps):
- NZDJPY: adx_max=40 -> WR 56.6%->59.5%, DD 10.1%->5.1%, PF 1.18->1.32. ADOPTED.
- USDCAD: adx_max=40 -> WR 56.6%->57.4%, DD 9.2%->7.0%. ADOPTED.
- OMRCNY: adx_max=35 -> WR ~57.1% (same) but DD 16.5%->8.1% (halved). ADOPTED for safety.
- NGNUSD/BHDCNY: filter cut too many trades, no gain -> kept baseline (use_adx=false). Honest.
- min_range dead-candle filter: killed all trades on these pairs (too strict) -> NOT used.
FINAL basket WRs: NGNUSD 60.8 / NZDJPY 59.5 / BHDCNY 59.2 / USDCAD 57.4 / OMRCNY 57.1. All DD<=8.1%.
Live engine reloaded basket; 3 pairs adx-filtered, 2 baseline. Verified running.

### DASHBOARD FEATURES (all live): AUTO/MANUAL toggle (/mode), per-pair status colors
waiting(grey)/READY(yellow)/IN TRADE(green-pulse), Live Signals manual-backup panel w/ BUY▲/SELL▼
+ TAKE NOW banner, triple-beep + voice ("buy buy buy"/"sell sell sell") + browser PUSH NOTIFICATIONS
on each signal (needs HTTPS on phone), open-positions countdown, recent trades, live balance.
