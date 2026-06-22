# DASHBOARD SPEC — Options Bot Control Center (locked 2026-06-20)

User requirement, verbatim intent: ONE professional, mobile-friendly dashboard that
integrates + monitors BOTH brokers (Deriv + Pocket Option) from one screen — see balances
separately, start/stop/pause, see everything he'd see on the broker, and live OTC payout %.
Must be controllable + monitorable from his PHONE, 24/7, securely.

## ACCESS
- Served by the bot itself (not localhost-only). Reachable via subdomain + HTTPS,
  e.g. `https://bot.getquantumedgeai.com` (free subdomain off his existing domain -> VPS IP).
- **Password-protected login** (his own dashboard password — separate from broker tokens).
- Mobile-responsive (phone-first layout). Works on cell data, anywhere.

## TOP BAR — both accounts, SEPARATE
| Deriv | Pocket Option |
|---|---|
| account balance (live) | account balance (live) |
| demo/live mode badge | demo/live mode badge |
| connection status (green/red) | connection status (green/red) |
| today P&L ($ / %) | today P&L ($ / %) |

## GLOBAL CONTROLS (big, obvious, phone-tappable)
- **START** — bot begins trading per strategy
- **STOP / KILL** — halts all new trades instantly (panic button)
- **PAUSE / RESUME** — temporary hold
- Per-broker toggle: run Deriv only, PO only, or both
- Risk display: current 1% stake size, daily-loss-limit status, trades-used-this-window

## LIVE TRADE PANEL (what he'd see on the broker)
- Open trades: asset, direction (CALL/PUT), stake, expiry countdown, entry price
- Closed trades (history): result (win/loss), payout $, time
- Per-broker filter

## OTC ASSET / PAYOUT PANEL
- List of tradeable OTC assets per broker with **live payout %** (e.g. AUD/CAD OTC 92%)
- Highlight which clear the break-even gate (>=90%)
- Show which assets the bot is currently watching/eligible
- NOTE (honesty): Deriv payouts come from its OFFICIAL API (reliable). PO payouts come from
  the unofficial ssid feed — display them, but mark as broker-reported, may lag.

## PERFORMANCE PANEL
- Win rate, profit factor (DOLLAR), expectancy, max drawdown, trade count
- Per broker + combined
- Equity curve chart

## SECURITY (non-negotiable)
- HTTPS only. Login password. Broker tokens NEVER shown in the UI (stay in secrets/ on server).
- Optional IP allowlist. Session timeout. Kill-switch always reachable.

## BUILD NOTES
- Backend = the Python bot (FastAPI/Flask serving the dashboard + websocket for live updates).
- Frontend = clean mobile-first web UI (dark theme OK to match brand).
- Demo-first: dashboard works identically on demo; flip to live = same UI, live tokens.
- This is a LATER deliverable: built after KB7 digest + engine + 5,000-trade backtest pass.
- Pair with `GO-LIVE-GUIDE.md` (how to get live tokens, deploy to Hostinger VPS month-to-month,
  point subdomain, enable HTTPS, log in from phone).
