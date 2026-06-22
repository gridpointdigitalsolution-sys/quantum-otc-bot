"""Central config — stake, expiry, assets, risk caps. Single source of tunables.

Everything tunable lives here so backtest, live engine, and dashboard share one truth.
Risk numbers ported verbatim from KB7 RISK GOVERNOR (EdgeFlo blueprint).
"""
from __future__ import annotations
from dataclasses import dataclass, field


# ── Expiries we trade (seconds). User requirement: 1m AND 2m AND 5m. ──
EXPIRIES_SEC = (60, 120, 300)

# ── Candle base granularity (seconds). 1m base; higher expiries are multiples. ──
BASE_GRANULARITY_SEC = 60


@dataclass(frozen=True)
class RiskConfig:
    """RISK GOVERNOR — tuned to POCKET OPTION REALITY (user-corrected S-PO).

    POCKET OPTION HARD FACT: minimum stake = $1.00. There is no $0.50 / 0.5% — sub-$1
    is impossible. So we size in DOLLARS, flat $1 per trade on a small account, stepping
    up only as balance grows. (% is just bookkeeping; the broker floor is $1.)

    TRADE COUNT: volume comes from BREADTH (many pairs each taking their few REAL setups),
    never from forcing one pair into noise. Session model (morning/afternoon/evening):
    each session has a trade quota; if a session takes `session_loss_cooldown` losses it
    PAUSES for `session_cooldown_minutes`, then resumes the rest of that session's quota.
    Daily $-loss cap is the real seatbelt for the $150."""
    # ---- sizing (PO $1 floor) ----
    min_stake_usd: float = 1.0             # PO minimum — cannot go lower
    stake_usd: float = 1.0                 # flat stake on small account ($150 start)
    stake_pct_of_balance: float = 0.0      # 0 = use flat stake_usd; >0 = % once acct grows
    # ---- session windows (UTC hour ranges): morning / afternoon / evening ----
    session_windows: tuple = ((0, 8), (8, 16), (16, 24))
    max_trades_per_session: int = 15       # quota per window -> up to ~45/day across 3
    max_trades_per_day: int = 40           # daily ceiling
    max_trades_per_pair_per_session: int = 3  # one pair can't dominate a session
    # ---- session loss-cooldown (NOT a full-day halt) ----
    session_loss_cooldown: int = 5         # losses within a session -> pause that session
    session_cooldown_minutes: int = 90     # ~1-2h pause, then resume the session quota
    stop_after_consec_losses: int = 5      # 5 in a row -> pause current session
    cooldown_after_loss_bars: int = 1      # brief anti-tilt gap between trades
    # ---- daily seatbelt: ONLY loss is capped. PROFIT IS UNLIMITED (user S-PO). ----
    # No upside halt — if the edge keeps firing, the bot keeps banking. Binary, not forex.
    max_daily_loss_pct: float = 6.0        # ~$9 on $150 -> HALT day (the ONLY daily halt)
    daily_profit_target_pct: float = 1e9   # DISABLED — never stop on profit
    max_concurrent_exposure_pct: float = 8.0
    min_sample_before_live: int = 100      # Rule of 100
    # legacy aliases (backtest engine reads these; map to flat-$ model)
    risk_per_trade_pct: float = 1.0
    risk_per_trade_pct_aplus: float = 1.0
    risk_per_trade_pct_a: float = 1.0


@dataclass(frozen=True)
class PayoutGate:
    """Live payout floor — hard PRE-TRADE filter (PO-target-assets.md, user-locked).
    Higher payout = lower base probability; required WR rises as payout falls."""
    floor_normal: float = 0.90             # break-even WR 52.63%
    floor_offpeak_aplus: float = 0.85      # A+ only; break-even WR 54.05%
    # below 0.85 -> NEVER trade (auto-skip)

    @staticmethod
    def breakeven_wr(payout_frac: float) -> float:
        """Break-even win rate for a fixed-payout binary: 1/(1+payout)."""
        return 1.0 / (1.0 + payout_frac)


@dataclass(frozen=True)
class BotConfig:
    starting_balance: float = 150.0        # real starting capital ($150 borrowed)
    risk: RiskConfig = field(default_factory=RiskConfig)
    payout: PayoutGate = field(default_factory=PayoutGate)
    expiries_sec: tuple = EXPIRIES_SEC
    base_granularity_sec: int = BASE_GRANULARITY_SEC
    # Deriv synthetic candidates for Step 0 (24/7, no market-hours gap).
    deriv_step0_symbols: tuple = (
        "R_10", "R_25", "R_50", "R_75", "R_100",      # Volatility indices
        "1HZ10V", "1HZ50V", "1HZ100V",                # 1-second volatility
        "stpRNG",                                      # Step index
        "BOOM500", "CRASH500",                         # Boom/Crash (asymmetric)
    )


CONFIG = BotConfig()
