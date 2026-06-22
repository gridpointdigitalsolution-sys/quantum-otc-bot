# QUANTUM OTC BINARY BOT — MASTER HANDOVER (single source of truth)
_Last updated: 2026-06-23 (overnight build complete + deployed live)_

> Read this FIRST. It covers everything: what was done, what was kept and where, what is
> ready, what is live, and what's left. Honesty rule: every number here is from a real
> backtest/forward run — never fabricated. Judge by DOLLAR profit factor / drawdown, never
> raw win rate alone.

═══════════════════════════════════════════════════════════════════
## 1. WHAT THIS IS
═══════════════════════════════════════════════════════════════════
A Python binary/OTC options trading bot for **Pocket Option** (24/7 OTC pairs), with a live
web dashboard. Trades 1-5 min binaries, $1 fixed stake, NO martingale. Separate from the TITAN
forex EAs — never touches them. User's real capital: **$150** (borrowed), survival money.

═══════════════════════════════════════════════════════════════════
## 2. THE JOURNEY (what was tried + the honest outcomes)
═══════════════════════════════════════════════════════════════════
- **Deriv = RULED OUT for binary (proven, do not retry).** Tested all 46 24/7 synthetics ×
  13 strategies × 4 expiries. The binary-tradeable ones (Volatility/Jump/Step) are engineered
  ~random (best ~55% = noise). The ones WITH a real edge (Range Break RB100/RB200 fade ~64%,
  Boom/Crash drift 90%+) are **multiplier/accumulator only — NO Rise/Fall binary** (checked
  contracts_for). So untradeable as binary. Deriv is the house; its binaries can't be beaten.
- **Pocket Option = the platform.** Real-market OTC pairs, real binaries, 92% max payout.
  History depth ~31 days of 1-min (broker cap) via get_candles_advanced pagination.
- Tested ALL 112 PO OTC assets (currencies + stocks + crypto). Stocks/crypto OTC = NO stable
  edge (don't mean-revert). Only currency-OTC pairs produced walk-forward-stable edges.

═══════════════════════════════════════════════════════════════════
## 3. THE STRATEGY (what won + why)
═══════════════════════════════════════════════════════════════════
**Family: mean-reversion (rsi@lvl).** Binary needs a HIGH hit-rate (every loss = -100%), so the
right family is fading extremes in RANGES — NOT trend-following (trend setups S10/S11 all failed
~51%, confirmed). Setup `RsiAtLevel`:
- ENTRY: RSI(14) >= ob (PUT) or <= os (CALL) **AND** price within tol×ATR of the 20-bar
  support/resistance level **AND** RSI turning back. Enter next bar, settle at expiry.
- The S/R-level gate is the selectivity lever that lifts win rate (plain RSI alone = ~54%).
- ADX trend-avoidance gate (use_adx): skip when ADX >= adx_max (don't fade a strong trend).
  Adopted only where it helped (re-validated per pair).
- No look-ahead (audited): signal on CLOSED bar, enter next open, settle at exact expiry.

═══════════════════════════════════════════════════════════════════
## 4. THE FINAL BASKET — 6 PAIRS (live, walk-forward-stable, 92% payout, be 52.1%)
═══════════════════════════════════════════════════════════════════
| Pair | Expiry | WR | PF | Max DD | Filter | Min payout to trade |
|------|--------|-----|-----|--------|--------|---------------------|
| NGNUSD_otc | 5m | 60.8% | 1.42 | 6.4% | baseline | 77% |
| NZDJPY_otc | 3m | 59.5% | 1.32 | 5.1% | ADX-40 | 82% |
| BHDCNY_otc | 5m | 59.2% | 1.31 | 7.4% | baseline | 77% |
| USDPHP_otc | 2m | 58.2% | 1.27 | 6.3% | baseline | 77% |
| USDCAD_otc | 2m | 57.4% | 1.24 | 7.0% | ADX-40 | 82% |
| OMRCNY_otc | 3m | 57.1% | 1.22 | 8.1% | ADX-35 | 80% |

- Each pair's expiry = the ONLY profitable one (verified 1/2/3/5m; 1m loses on all).
- 3 exotics (NGNUSD/BHDCNY/OMRCNY) = best WR but PO-generated-feed risk. 3 liquid-ish
  (NZDJPY/USDCAD/USDPHP) = more trustworthy. ALL passed 2-of-3 walk-forward time segments.
- HONEST: edges are THIN (~57-61%), proven on 1 month. **Live forward test is the real proof.**
- Per-pair payout minimum = (1-WR)/WR + 5% margin, hard floor 77%. Bot trades a pair ONLY when
  its live payout clears its minimum (so it never takes a losing-payout trade).
- Params stored in `data/research/basket_po.json` (the live engine reads this exactly).
- DROPPED: EURHUF (one sub-breakeven period), all stocks/crypto OTC (no edge).

═══════════════════════════════════════════════════════════════════
## 5. RISK GOVERNOR (config.py) — tuned to PO reality
═══════════════════════════════════════════════════════════════════
- Stake: **flat $1** (PO minimum; NO sub-$1, NO martingale — structural).
- Sessions: 3/day (morning/afternoon/evening, UTC+1) × up to 15 trades = ~45/day cap.
- Per-pair-per-session cap: 3 (no single pair dominates). No stacking >1 position per pair.
- Daily loss cap: **-6%** (~-$9 on $150) -> HALT day. **Profit UNCAPPED** (never stop on a win).
- Session cooldown: 5 losses in a session -> pause ~90 min -> resume that session.
- Trade counts enforced at OPEN (not settle) so caps can't be blown past.
- starting_balance = 150.

═══════════════════════════════════════════════════════════════════
## 6. WHERE EVERYTHING LIVES
═══════════════════════════════════════════════════════════════════
**Local code:** `F:\Quantum growth materials\Trading Bot Creation Research\option trading bot\`
- `bot/config.py` — all tunables + risk governor.
- `bot/live_engine.py` — live trading engine (governor, live balance, open-positions,
  per-pair payout gate, signals feed, AUTO/MANUAL mode, history persist, robust settle).
- `bot/registry.py` — maps basket entries -> strategy objects (no backtest/live drift).
- `bot/strategy/` — s3_sweep.py (RsiAtLevel + SweepReversal), ensemble.py (Stoch/Triple/
  Williams/BandRev), confluence.py, s4_trend.py (S10/S11), s1_bollinger.py, fade.py, momentum.py, s2_rsi.py.
- `bot/backtest.py` — payout-capped, no-look-ahead backtester.
- `bot/data/` — candles.py, deriv_source.py, po_source.py.
- `dashboard/server.py` — FastAPI (/, /ping, /status, /basket, /start, /stop, /mode;
  PIN gate; AUTO-RESUME after reboot).
- `dashboard/dashboard.html` — mobile-responsive UI (PIN screen, balance/PL/WR, 3-state pair
  status waiting(grey)/READY(yellow)/IN-TRADE(green), open positions countdown, recent trades,
  Live Signals manual-backup feed + TAKE NOW banner, sound + voice + push notifications, AUTO/MANUAL).
- `scripts/` — fetch_po.py, sweep_po.py, optimize_po.py, finalize_basket.py, revalidate_filters.py,
  scan_new_fast.py, test_kb7.py, validate_po.py, etc.
- `strategy/KB1-9 + KB7-distilled-playbook.md` — the digested brain (16 books + ~6000 videos).
- `data/research/basket_po.json` — THE LIVE 6-PAIR BASKET (committed).
- `secrets/` — GITIGNORED. po.env (dev ssid), pin.txt (dashboard PIN), active.json (saved live session).
- `data/raw_po/`, `books/`, `transcripts*/` — local only, gitignored (huge).

**GitHub:** `github.com/gridpointdigitalsolution-sys/quantum-otc-bot` (PRIVATE). Code + basket
only (no secrets, no data). gh account: gridpointdigitalsolution-sys.

**VPS:** Hostinger, **IP 187.77.176.95**, Ubuntu 24.04, `ssh root@187.77.176.95`.
- Code at `/opt/otc-bot`, venv `.venv`, systemd service `otc-bot` (always-on, Restart=always).
- nginx reverse proxy + certbot HTTPS. Firewall: 8000, OpenSSH, Nginx Full.
- **LIVE at: https://bot.churchillbracknell.com** (DNS A record bot -> 187.77.176.95).
- PIN file: `/opt/otc-bot/secrets/pin.txt` (user-set, 6-digit; never in repo).

═══════════════════════════════════════════════════════════════════
## 7. WHAT'S DONE / LIVE (as of 2026-06-23 night)
═══════════════════════════════════════════════════════════════════
- [x] Strategy researched, built, backtested, walk-forward validated -> 6-pair basket.
- [x] Live engine + dashboard built, all bugs audited+fixed, settle proven on real trades.
- [x] Deployed to VPS, HTTPS live, PIN-secured, mobile-responsive.
- [x] AUTO/MANUAL toggle, signals feed, TAKE NOW banner, sound+voice+push notifications.
- [x] Per-pair live payout gate (only trades good payouts).
- [x] AUTO-RESUME after reboot/crash (ssid persisted to secrets/active.json; server reloads on startup).
- [x] GitHub private repo; deploy = git pull + systemctl restart otc-bot.

═══════════════════════════════════════════════════════════════════
## 8. HOW TO OPERATE
═══════════════════════════════════════════════════════════════════
- **Start/restart:** laptop -> PO -> F12 -> Network -> WS -> Messages -> filter "auth" -> copy
  the GREEN `42["auth",{...}]` frame (NOT the red 451 reply) -> open dashboard -> enter PIN ->
  paste ssid -> Start. Then close laptop; bot runs on VPS.
- **Monitor:** open https://bot.churchillbracknell.com on phone, enter PIN.
- **ssid lifetime:** valid hours-to-days; survives browser refresh + laptop off (VPS holds it) +
  VPS reboot (auto-resume). Only PO session EXPIRY needs a fresh paste. Don't log out of PO.
- **Update code:** locally edit -> git push -> on VPS: `cd /opt/otc-bot && git pull &&
  systemctl restart otc-bot`. (Repo is private; flip public for the pull or set a deploy key.)
- **Set/change PIN:** on VPS `echo "NEWPIN" > /opt/otc-bot/secrets/pin.txt && systemctl restart otc-bot`.

═══════════════════════════════════════════════════════════════════
## 9. WHAT'S LEFT / NEXT
═══════════════════════════════════════════════════════════════════
1. **Overnight demo forward test running** -> tomorrow: read the LIVE win rate per pair, compare
   to backtest. If it holds above each pair's breakeven -> fund real $150 ($1 stakes). If a pair
   underperforms live -> drop it.
2. **Expiry-exact payout** (optional refine): dashboard payout is currently the asset's API value
   (~3-5% off the on-screen per-expiry figure; real fills always use PO's true rate). To match the
   screen exactly needs digging PO raw websocket per-expiry payout — uncertain effort, do carefully
   tomorrow, NOT during a live run.
3. **Deploy-key on VPS** so private-repo `git pull` works without flipping public each update.
4. Optional: more pairs if PO adds 24/7 OTC currencies; periodic re-validation as data grows.

═══════════════════════════════════════════════════════════════════
## 9b. RELIABILITY / NO-STALE-DATA RULES (lessons locked in — do NOT regress)
═══════════════════════════════════════════════════════════════════
These were real bugs that caused "stale/cached" displays. All FIXED — keep them this way:
1. **Truthful /status** — `/status` returns live engine state from `_engine["obj"].s.running`,
   NOT the on-disk status file. On restart with no live engine it reports "not running" (never a
   leftover running:true). Bug was: dashboard read a stale live_status.json after a restart and
   showed "live" when nothing ran. NEVER report running from the file alone.
2. **No browser caching** — server sends `Cache-Control: no-store, no-cache, must-revalidate` +
   Pragma/Expires on EVERY response (middleware in server.py); client fetches use
   `cache:'no-store'`. So a code/UI/data update is ALWAYS fresh — no old cached dashboard/JS/numbers.
   If you ever see "old version", it's NOT cache (that's killed) — check the VPS actually pulled
   (`cd /opt/otc-bot && git log -1`) and restarted.
3. **Auto-resume** — ssid saved to secrets/active.json on Start; server reloads it on startup, so
   reboot/crash auto-reconnects. /stop clears it (intentional stop doesn't auto-resume).
4. **Verify "really live"** — Balance shows a real number + pairs show live payouts = genuinely
   running. "running" with null balance / empty pairs = check the engine.
5. **Deploy correctness** — update = local edit -> git push -> VPS `git pull && systemctl restart
   otc-bot`. Confirm with `git log -1` on the VPS. No browser cache can mask a real deploy now.

═══════════════════════════════════════════════════════════════════
## 10. HONEST CAVEATS (never hide these)
═══════════════════════════════════════════════════════════════════
- Edges are THIN (57-61% WR) on 1 month of data. Real proof = live forward test.
- 3 of 6 pairs are exotic (PO-generated feed) — edge could shift; liquid pairs safer.
- PO library = unofficial (ssid websocket). Works, but against strict ToS; low ban risk if
  human-like (our governor enforces that). Real-world risk on PO = withdrawal friction; test
  withdrawals small+early before trusting size.
- Off-peak payouts drop below pair minimums -> bot correctly WAITS (few/no trades) -> not a bug.
