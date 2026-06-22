"""BACKTEST ENGINE — payout-capped, realistic-fill binary backtester.

Realism (KB7 ENGINEERING REQUIREMENTS):
- Signal on CLOSED bar i -> ENTER at bar i+1 OPEN (strike = that open price).
- Settle on the EXACT expiry close: n_bars = expiry_sec / granularity; settle price =
  close of bar (entry_idx + n_bars - 1).
- Binary payoff: CALL wins if settle > strike; PUT wins if settle < strike. TIE = LOSS
  (conservative; PO loses ties).
- PAYOUT CAP: win = +payout*stake, loss = -stake (-100%). Break-even WR = 1/(1+payout).
- RISK: 1% fixed-fractional of CURRENT balance = stake (loss is the whole stake, so stake
  IS the risk). STRUCTURAL anti-martingale — stake only ever tracks balance, never a streak.
- RISK GOVERNOR (per UTC day): max trades/day, max daily loss -> halt, daily profit target
  -> halt, consecutive-loss halt, cooldown bars after a loss.
- Payout gate: a trade is only taken if payout >= floor (A+ may use off-peak floor).

We judge by DOLLAR profit factor / max drawdown / expectancy — never raw win rate.
Payout here is an ASSUMED flat value for the backtest (real live payout applied at trade
time by the live engine). Report is run at several payouts to show sensitivity.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np

from .config import CONFIG
from .strategy.base import Strategy


@dataclass
class Trade:
    entry_epoch: int
    direction: str
    quality: str
    strike: float
    settle: float
    expiry_sec: int
    stake: float
    pnl: float
    win: bool
    balance_after: float


@dataclass
class BacktestResult:
    asset: str
    expiry_sec: int
    payout: float
    n_trades: int
    wins: int
    win_rate: float
    breakeven_wr: float
    edge_vs_breakeven: float      # win_rate - breakeven_wr (the thing that matters)
    dollar_pf: float
    expectancy: float             # $ per trade
    avg_win: float
    avg_loss: float
    max_drawdown_pct: float
    final_balance: float
    return_pct: float
    skipped_payout: int
    skipped_governor: int
    equity_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)

    def summary_line(self) -> str:
        verdict = "PASS" if self.passes() else "FAIL"
        return (f"{self.asset:12} {self.expiry_sec:4d}s payout={self.payout:.0%} "
                f"n={self.n_trades:5d} WR={self.win_rate:5.1%} (be={self.breakeven_wr:.1%} "
                f"edge={self.edge_vs_breakeven:+.1%}) PF={self.dollar_pf:4.2f} "
                f"exp=${self.expectancy:+.3f} DD={self.max_drawdown_pct:4.1f}% "
                f"ret={self.return_pct:+.1f}% -> {verdict}")

    def passes(self, min_edge=0.03, min_pf=1.10, max_dd=25.0, min_trades=100) -> bool:
        """Headline PASS bar (pre-validation): clears break-even by a real margin,
        positive dollar PF, acceptable DD, enough trades. Validation (walk-forward +
        Monte Carlo + multiple-testing) is the FINAL gate, applied separately."""
        return (self.n_trades >= min_trades and self.edge_vs_breakeven >= min_edge
                and self.dollar_pf >= min_pf and self.max_drawdown_pct <= max_dd)


def _utc_day(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")


def run_backtest(asset: str, epoch, o, h, l, c, granularity_sec: int,
                 strategy: Strategy, payout: float = 0.90,
                 cfg=CONFIG, off_peak_floor=None) -> BacktestResult:
    """Run one strategy on one asset@expiry. Arrays are numpy float64."""
    epoch = np.asarray(epoch, dtype=np.int64)
    o, h, l, c = (np.asarray(x, dtype=np.float64) for x in (o, h, l, c))
    n = len(c)
    strategy.precompute(o, h, l, c)
    n_bars = strategy.expiry_sec // granularity_sec  # bars to expiry
    if n_bars < 1:
        n_bars = 1

    risk = cfg.risk
    gate = cfg.payout
    floor_normal = gate.floor_normal
    floor_off = off_peak_floor if off_peak_floor is not None else gate.floor_offpeak_aplus

    balance = cfg.starting_balance
    peak = balance
    max_dd = 0.0
    equity = [balance]
    trades: list[Trade] = []
    wins = 0
    skipped_payout = 0
    skipped_governor = 0

    # per-day governor state
    day = None
    day_start_balance = balance
    day_trades = 0
    halted_today = False
    consec_losses = 0
    cooldown_until = -1

    warm = strategy.warmup()
    i = warm
    # last bar that can be SIGNALLED: need i+1 entry and i+1+n_bars-1 settle to exist
    last_signal_bar = n - 1 - n_bars - 1
    while i <= last_signal_bar:
        d = _utc_day(int(epoch[i]))
        if d != day:
            day = d
            day_start_balance = balance
            day_trades = 0
            halted_today = False
            # consec_losses persists across days (session discipline); reset on new day is
            # also defensible — we keep it rolling but the daily halt covers the worst tilt.

        sig = strategy.signal_at(i)
        if sig is None:
            i += 1
            continue

        # ── RISK GOVERNOR pre-trade checks ──
        if halted_today:
            skipped_governor += 1
            i += 1
            continue
        if day_trades >= risk.max_trades_per_day:
            skipped_governor += 1
            i += 1
            continue
        if consec_losses >= risk.stop_after_consec_losses:
            halted_today = True
            skipped_governor += 1
            i += 1
            continue
        if i < cooldown_until:
            skipped_governor += 1
            i += 1
            continue
        # daily loss / profit halts
        day_pnl_pct = (balance - day_start_balance) / day_start_balance * 100.0
        if day_pnl_pct <= -risk.max_daily_loss_pct:
            halted_today = True
            skipped_governor += 1
            i += 1
            continue
        if day_pnl_pct >= risk.daily_profit_target_pct:
            halted_today = True
            skipped_governor += 1
            i += 1
            continue

        # ── PAYOUT GATE ──
        floor = floor_off if sig.quality == "A+" else floor_normal
        if payout < floor:
            skipped_payout += 1
            i += 1
            continue

        # ── SIZING (structural anti-martingale: stake = fixed % of CURRENT balance) ──
        risk_pct = (risk.risk_per_trade_pct_aplus if sig.quality == "A+"
                    else risk.risk_per_trade_pct_a)
        stake = balance * risk_pct / 100.0
        if stake <= 0:
            break

        # ── EXECUTE: enter next open, settle at expiry close ──
        entry_idx = i + 1
        settle_idx = entry_idx + n_bars - 1
        strike = o[entry_idx]
        settle = c[settle_idx]
        if sig.direction == "CALL":
            win = settle > strike
        else:
            win = settle < strike

        pnl = payout * stake if win else -stake
        balance += pnl
        if win:
            wins += 1
            consec_losses = 0
        else:
            consec_losses += 1
            cooldown_until = i + 1 + risk.cooldown_after_loss_bars

        day_trades += 1
        trades.append(Trade(int(epoch[entry_idx]), sig.direction, sig.quality,
                            strike, settle, sig.expiry_sec, stake, pnl, win, balance))
        equity.append(balance)
        peak = max(peak, balance)
        dd = (peak - balance) / peak * 100.0
        max_dd = max(max_dd, dd)

        # advance past the settle bar so trades don't overlap on the same setup
        i = settle_idx + 1

    n_tr = len(trades)
    gross_win = sum(t.pnl for t in trades if t.win)
    gross_loss = -sum(t.pnl for t in trades if not t.win)
    pf = gross_win / gross_loss if gross_loss > 0 else (np.inf if gross_win > 0 else 0.0)
    wr = wins / n_tr if n_tr else 0.0
    be = 1.0 / (1.0 + payout)
    avg_win = (gross_win / wins) if wins else 0.0
    n_loss = n_tr - wins
    avg_loss = (gross_loss / n_loss) if n_loss else 0.0
    expectancy = (balance - cfg.starting_balance) / n_tr if n_tr else 0.0

    return BacktestResult(
        asset=asset, expiry_sec=strategy.expiry_sec, payout=payout,
        n_trades=n_tr, wins=wins, win_rate=wr, breakeven_wr=be,
        edge_vs_breakeven=wr - be, dollar_pf=float(pf), expectancy=expectancy,
        avg_win=avg_win, avg_loss=avg_loss, max_drawdown_pct=max_dd,
        final_balance=balance, return_pct=(balance / cfg.starting_balance - 1) * 100.0,
        skipped_payout=skipped_payout, skipped_governor=skipped_governor,
        equity_curve=equity, trades=trades,
    )
