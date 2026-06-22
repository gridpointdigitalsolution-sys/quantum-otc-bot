# KB9 — Broker verification (live web research, 2026-06-20)

Source: 2 research agents fact-checking a Grok-generated broker list. Trader = Nigeria,
wants a Python bot placing **1m / 2m / 5m OTC binary** trades. Automation = dealbreaker.
Verdicts are honest; unverifiable items marked "unverified". No promises.

## CORE TRUTH
Every binary broker here EXCEPT Deriv (and Dukascopy's FIX) has **NO official retail
trading API**. Every "Python lib" below is an **unofficial reverse-engineered WebSocket**
that violates broker ToS, can break without notice, and risks account ban / frozen
withdrawal. Build on the safe core first; treat the rest as experimental, small-capital.

## LOCKED DECISION (2026-06-20, user explicit) — BUILD FOR THESE TWO ONLY
| Broker | Why |
|---|---|
| **Deriv** | OFFICIAL supported WebSocket API + 24/7 synthetic indices. Regulated-tier, reliable payouts. Demo token stored. Gold standard. |
| **Pocket Option** | User already uses it. Working unofficial libs (`pocketoptionapi` / BinaryOptionsToolsV2). 92% OTC, $1 min. |

**Quotex + IQ Option = CUT.** User does NOT want withdrawal/ban risk from unregulated
offshore brokers. Quotex had real withdrawal-block complaints; IQ "study-only" + offshore.
Do NOT add them. Only revisit if the user explicitly asks later. Two brokers is plenty.

## AVOID (no credible automation and/or unregulated/scam-flag)
| Broker | Reason |
|---|---|
| **Capitalcore** | "IFSA" regulator is FAKE (not in IOSCO/any register). No automation lib. AVOID. |
| **CloseOption** | Unregulated, 2.1 ForexPeaceArmy, withdrawal gating. No Python lib. AVOID. |
| **Binomo** | Persistent scam flags + country bans. No maintained lib. AVOID. |
| **Expert Option** | Low trust, no credible maintained lib. AVOID for bots. |
| **Olymp Trade** | Real (Vanuatu VFSC) but name abused in Nigerian "double your money" FB scams; only paid/2Captcha-fragile libs. Not worth it for a bot. |
| **Nadex** | ONLY top-tier regulated (CFTC) name — but Nigerians NOT eligible. Blocked. |
| **Dukascopy** | Legit Swiss FINMA bank, real official FIX API — but binaries are FX-hours contracts, NOT 24/7 OTC synthetic. Wrong product. NG-binary eligibility unverified. |

## GROK AFFIRM / CORRECT
- TRUE: Quotex real, ~$1, high payout, good PO alternative, automatable.
- TRUE: IQ Option real, 60s expiries, automatable (unofficial).
- MISLEADING: Capitalcore "Open API" — no usable retail trading API found; regulator fake. Grok oversold it.
- HALF-TRUE: Olymp Trade / CloseOption "some bot compatibility via signals" — not real programmatic trade placement. Not bot-grade.
- TRUE: Nadex regulated / Dukascopy FIX API — but neither fits Nigeria + 24/7 OTC.

## BUILD DECISION
- Engine target: **Deriv (official API) + Pocket Option ONLY**. No Quotex, no IQ, no others.
- Bot must support **1m AND 2m AND 5m** expiries (user requirement) — expiry chosen per
  setup (half-life from KB3), broker-configurable.
- Multi-broker = one strategy core, pluggable execution adapter per broker.
- Libs to evaluate when building: Deriv official `python-deriv-api`; PO `BinaryOptionsToolsV2`/`pocketoptionapi`.

## SECURITY
All broker session tokens / passwords -> `secrets/` (gitignored). Demo first, always.
Live trading only after backtest proves edge. No martingale. 1% fixed-fractional.
