"""LIVE / DEMO trading engine for Pocket Option (ssid-driven, fully automatic).

Reads the validated basket (data/research/basket_po.json), runs each pair's strategy on LIVE
candles, enforces the risk governor (session windows, $1 stake, -6% daily loss halt, profit
UNCAPPED, session loss-cooldown, per-pair caps), places trades (CALL=buy / PUT=sell), settles
via check_win, and writes a live status JSON the dashboard reads.

NO look-ahead: signal taken on the last CLOSED candle only. NO martingale: stake is fixed $.
Demo until proven. Honest accounting: every trade logged with real settle result.
"""
from __future__ import annotations
import asyncio, json, os, time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta

import numpy as np

from .config import CONFIG
from .registry import build_strategy
from .data.po_source import load_ssid
from . import push

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_PATH = os.path.join(PROJ, "data", "live_status.json")
TRADES_LOG = os.path.join(PROJ, "data", "live_trades.jsonl")
BASKET_PATH = os.path.join(PROJ, "data", "research", "basket_po.json")


@dataclass
class EngineState:
    running: bool = False
    connected: bool = False
    ssid_ok: bool = False
    balance: float = 0.0
    start_balance: float = 0.0
    day: str = ""
    day_pnl: float = 0.0
    day_trades: int = 0
    wins: int = 0
    losses: int = 0
    session: str = ""
    session_trades: int = 0
    session_losses: int = 0
    consec_losses: int = 0
    halted_day: bool = False
    cooldown_until: float = 0.0
    open_trades: int = 0
    open_positions: list = field(default_factory=list)   # live positions w/ settle time
    last_msg: str = ""
    mode: str = "auto"                    # "auto" = bot trades · "manual" = signals only
    pairs: list = field(default_factory=list)
    pair_status: list = field(default_factory=list)   # live payout + tradeable per pair
    recent: list = field(default_factory=list)   # last N settled trades
    signals: list = field(default_factory=list)  # last N suggested actions (BUY/SELL)

    def win_rate(self):
        n = self.wins + self.losses
        return (self.wins / n) if n else 0.0


class LiveEngine:
    def __init__(self, ssid: str, cfg=CONFIG, tz_offset_hours: int = 1, demo: bool = True):
        self.ssid = ssid
        self.cfg = cfg
        self.tz = tz_offset_hours          # Nigeria = +1
        self.demo = demo
        self.s = EngineState()
        self.api = None
        self.specs = []                    # (asset, strategy, expiry_sec)
        self._stop = False
        self._seen_bar = {}                # asset -> last evaluated closed-bar epoch
        self._payouts = {}                 # asset -> live payout % (refreshed each loop)
        self._pair_sess = {}               # (session, asset) -> trades opened this session

    # ---------- setup ----------
    def load_basket(self):
        if not os.path.exists(BASKET_PATH):
            self.s.last_msg = "no basket yet (run optimizer)"; return
        basket = json.load(open(BASKET_PATH, encoding="utf-8"))
        self.specs = []
        for b in basket:
            params = b.get("params", {})
            strat = build_strategy(b["setup"], int(b["expiry"]), params)
            wr = float(b.get("wr", 0.55))
            # min payout (fraction) for THIS pair's WR to beat breakeven + a SAFETY margin.
            # need payout p s.t. WR > 1/(1+p)  ->  p > (1-WR)/WR. +0.05 = only clearly-profitable.
            # also enforce a universal hard floor of 0.77 (user-set: never trade below 77%,
            # even on a high-WR pair). Per-pair minimum is stricter for low-WR pairs (-> 82%).
            min_pay = max(0.77, (1.0 - wr) / wr + 0.05)
            self.specs.append((b["asset"], strat, int(b["expiry"]), wr, min_pay))
        self.s.pairs = [{"asset": b["asset"], "setup": b["setup"], "expiry": b["expiry"],
                         "wr_bt": b.get("wr")} for b in basket]

    def _load_history(self):
        """Restore today's trades/counters from the log so restarts don't lose them."""
        if not os.path.exists(TRADES_LOG):
            return
        today = self._now_local().strftime("%Y-%m-%d")
        recent = []; wins = losses = 0; pnl = 0.0
        try:
            for line in open(TRADES_LOG, encoding="utf-8"):
                r = json.loads(line)
                if r.get("day") != today:
                    continue
                recent.append(r)
                if r.get("win"): wins += 1
                else: losses += 1
                pnl += float(r.get("profit", 0))
        except Exception:
            return
        if recent:
            self.s.recent = list(reversed(recent))[:25]
            self.s.wins = wins; self.s.losses = losses
            self.s.day_trades = wins + losses; self.s.day_pnl = round(pnl, 2)

    # ---------- time / session ----------
    def _now_local(self):
        return datetime.now(timezone.utc) + timedelta(hours=self.tz)

    def _session_of(self, dt):
        h = dt.hour
        for i, (a, b) in enumerate(self.cfg.risk.session_windows):
            if a <= h < b:
                return ["morning", "afternoon", "evening"][min(i, 2)]
        return "evening"

    def _roll_periods(self, dt):
        day = dt.strftime("%Y-%m-%d")
        if day != self.s.day:
            self.s.day = day; self.s.start_balance = self.s.balance
            self.s.day_pnl = 0.0; self.s.day_trades = 0
            self.s.halted_day = False
        sess = self._session_of(dt)
        if sess != self.s.session:
            self.s.session = sess; self.s.session_trades = 0
            self.s.session_losses = 0; self.s.cooldown_until = 0.0
            self._pair_sess = {}            # reset per-pair-per-session counters

    # ---------- governor ----------
    def _can_trade(self, asset):
        r = self.cfg.risk
        if self.s.halted_day:
            return False, "day halted (loss cap)"
        if self.s.day_pnl <= -(r.max_daily_loss_pct / 100.0) * self.s.start_balance:
            self.s.halted_day = True; return False, "day loss cap hit"
        if time.time() < self.s.cooldown_until:
            return False, "session cooldown"
        if self.s.session_trades >= r.max_trades_per_session:
            return False, "session quota full"
        if self.s.day_trades >= r.max_trades_per_day:
            return False, "daily quota full"
        if self._pair_sess.get((self.s.session, asset), 0) >= r.max_trades_per_pair_per_session:
            return False, "pair session cap"
        if self.s.open_positions and any(p["asset"] == asset for p in self.s.open_positions):
            return False, "pair already in trade"
        if self.s.consec_losses >= r.stop_after_consec_losses:
            self.s.cooldown_until = time.time() + r.session_cooldown_minutes * 60
            self.s.consec_losses = 0
            return False, "consec-loss cooldown"
        return True, "ok"

    def _stake(self):
        r = self.cfg.risk
        if r.stake_pct_of_balance > 0:
            return max(r.min_stake_usd, round(self.s.balance * r.stake_pct_of_balance / 100.0, 2))
        return max(r.min_stake_usd, r.stake_usd)

    # ---------- trade lifecycle ----------
    async def _settle(self, trade_id, asset, direction, stake, expiry):
        try:
            res = await self.api.check_win(trade_id, timeout_seconds=expiry + 30)
        except Exception:
            # retry once before giving up
            try:
                await asyncio.sleep(2)
                res = await self.api.check_win(trade_id, timeout_seconds=30)
            except Exception as e:
                # cannot confirm -> clean up + record as LOSS (money was risked; be conservative)
                self.s.open_trades = max(0, self.s.open_trades - 1)
                self.s.open_positions = [p for p in self.s.open_positions if p["id"] != trade_id]
                self.s.losses += 1; self.s.consec_losses += 1
                self.s.last_msg = f"settle err {asset} (recorded LOSS): {repr(e)[:30]}"
                rec = {"day": self.s.day, "t": self._now_local().strftime("%H:%M:%S"),
                       "asset": asset, "dir": direction, "stake": stake, "profit": -float(stake),
                       "win": False, "bal": round(self.s.balance, 2)}
                self.s.recent = ([rec] + self.s.recent)[:25]
                with open(TRADES_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
                self._write_status(); return
        # robust parse: check_win may return dict(profit/result) or a number or a string
        profit = 0.0; win = False
        if isinstance(res, dict):
            if res.get("profit") is not None:
                try: profit = float(res["profit"])
                except Exception: profit = 0.0
            rstr = str(res.get("result", res.get("status", ""))).lower()
            if rstr in ("win", "won", "true"): win = True
            elif rstr in ("loss", "lose", "lost", "false"): win = False
            else: win = profit > 0
            if res.get("profit") is None:
                profit = round(stake * 0.85, 2) if win else -float(stake)
        elif isinstance(res, (int, float)):
            profit = float(res); win = profit > 0
        elif isinstance(res, str):
            win = res.lower() in ("win", "won", "true"); profit = round(stake*0.85, 2) if win else -float(stake)
        else:
            win = False; profit = -float(stake)
        self.s.last_msg = f"SETTLED {asset} {'WIN' if win else 'LOSS'} {profit:+.2f}"
        self.s.open_trades = max(0, self.s.open_trades - 1)
        self.s.open_positions = [p for p in self.s.open_positions if p["id"] != trade_id]
        self.s.day_pnl += profit
        self.s.balance += profit
        # NOTE: day_trades/session_trades counted at OPEN (see _scan_asset), not here.
        if win:
            self.s.wins += 1; self.s.consec_losses = 0
        else:
            self.s.losses += 1; self.s.consec_losses += 1
            self.s.session_losses += 1
            if self.s.session_losses >= self.cfg.risk.session_loss_cooldown:
                self.s.cooldown_until = time.time() + self.cfg.risk.session_cooldown_minutes * 60
        rec = {"day": self.s.day, "t": self._now_local().strftime("%H:%M:%S"),
               "asset": asset, "dir": direction, "stake": stake,
               "profit": round(profit, 2), "win": win, "bal": round(self.s.balance, 2)}
        self.s.recent = ([rec] + self.s.recent)[:25]
        with open(TRADES_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        self._write_status()

    async def _scan_asset(self, asset, strat, expiry, wr, min_pay):
        # per-pair LIVE payout gate: skip if current payout makes the edge negative
        pay = self._payouts.get(asset)
        if pay is not None and (pay / 100.0) < min_pay:
            return
        try:
            rows = await self.api.get_candles(asset, self.cfg.base_granularity_sec, 200 * 60)
        except Exception as e:
            self.s.last_msg = f"candles err {asset}: {repr(e)[:30]}"; return
        if not rows or len(rows) < strat.warmup() + 3:
            return
        rows = sorted(rows, key=lambda r: int(r["timestamp"]))
        # drop the still-forming current bar -> last element is the last CLOSED bar
        closed = rows[:-1]
        last_epoch = int(closed[-1]["timestamp"])
        if self._seen_bar.get(asset) == last_epoch:
            return                                   # already evaluated this bar
        self._seen_bar[asset] = last_epoch
        o = np.array([float(r["open"]) for r in closed])
        h = np.array([float(r["high"]) for r in closed])
        l = np.array([float(r["low"]) for r in closed])
        c = np.array([float(r["close"]) for r in closed])
        strat.precompute(o, h, l, c)
        sig = strat.signal_at(len(c) - 1)
        if sig is None:
            return
        action = "BUY" if sig.direction == "CALL" else "SELL"
        ok, why = self._can_trade(asset)
        # record the SIGNAL regardless (manual-trade feed + audit of what bot saw)
        sigrec = {"t": self._now_local().strftime("%H:%M:%S"), "ts": time.time(),
                  "asset": asset,
                  "action": action, "expiry": expiry, "reason": sig.reason,
                  "acted": ok, "note": "placed" if ok else why}
        self.s.signals = ([sigrec] + self.s.signals)[:25]
        # MANUAL mode: surface the signal + alert, but the bot places NOTHING
        if self.s.mode == "manual":
            sigrec["acted"] = False; sigrec["note"] = "manual mode — trade by hand"
            self.s.last_msg = f"SIGNAL {action} {asset} {expiry}s (manual mode)"
            self._write_status()
            return
        if not ok:
            self.s.last_msg = f"SIGNAL {action} {asset} (skipped: {why})"
            self._write_status()
            return
        stake = self._stake()
        try:
            if sig.direction == "CALL":
                tid, _ = await self.api.buy(asset, stake, expiry)
            else:
                tid, _ = await self.api.sell(asset, stake, expiry)
        except Exception as e:
            self.s.last_msg = f"order err {asset}: {repr(e)[:40]}"
            sigrec["acted"] = False; sigrec["note"] = "order error"
            return
        # COUNT AT OPEN (prevents over-trading past caps)
        self.s.day_trades += 1
        self.s.session_trades += 1
        self._pair_sess[(self.s.session, asset)] = self._pair_sess.get((self.s.session, asset), 0) + 1
        self.s.open_trades += 1
        self.s.open_positions.append({"id": tid, "asset": asset, "dir": sig.direction,
                                      "stake": stake, "expiry": expiry,
                                      "settles": time.time() + expiry})
        self.s.last_msg = f"OPENED {action} {asset} ${stake} {expiry}s ({sig.reason})"
        # PHONE PUSH: trade is now LIVE / in play — alert subscribed phones even if app closed.
        # Fully wrapped + off-thread so a push failure can NEVER affect trading.
        try:
            mins = expiry / 60.0
            dur = f"{mins:g} min" if expiry % 60 == 0 else f"{expiry}s"
            title = ("⚡ LIVE BUY: " if action == "BUY" else "⚡ LIVE SELL: ") + asset
            body = f"{action} {asset} · {dur} · ${stake} · in play now"
            asyncio.get_event_loop().run_in_executor(None, push.send_all, title, body, "/", "live-" + str(tid))
        except Exception:
            pass
        asyncio.create_task(self._settle(tid, asset, sig.direction, stake, expiry))

    # ---------- main loop ----------
    async def run(self):
        from BinaryOptionsToolsV2 import PocketOptionAsync
        self.load_basket()
        self.api = PocketOptionAsync(self.ssid)
        await asyncio.sleep(4)
        try:
            self.s.balance = float(await self.api.balance())
            self.s.start_balance = self.s.balance
            self.s.connected = True; self.s.ssid_ok = True
        except Exception as e:
            self.s.last_msg = f"connect fail: {repr(e)[:50]}"; self._write_status(); return
        self.s.running = True
        self.s.day = self._now_local().strftime("%Y-%m-%d")
        self._load_history()          # restore today's trades across restarts
        self._write_status()
        while not self._stop:
            self._roll_periods(self._now_local())
            try:
                self._payouts = await self.api.payout()      # refresh live payouts each loop
            except Exception:
                pass
            try:
                self.s.balance = float(await self.api.balance())   # LIVE balance each loop
            except Exception:
                pass
            self.s.pair_status = []
            open_assets = {p["asset"] for p in self.s.open_positions}
            for asset, strat, expiry, wr, min_pay in self.specs:
                pay = self._payouts.get(asset)
                tradeable = pay is not None and (pay / 100.0) >= min_pay
                self.s.pair_status.append({
                    "asset": asset, "expiry": expiry, "payout": pay,
                    "min_payout": round(min_pay * 100),
                    "wr_bt": round(wr * 100, 1), "tradeable": tradeable,
                    "in_trade": asset in open_assets})
            for asset, strat, expiry, wr, min_pay in self.specs:
                if self._stop:
                    break
                await self._scan_asset(asset, strat, expiry, wr, min_pay)
                await asyncio.sleep(0.3)
            self._write_status()
            await asyncio.sleep(5)            # re-scan cadence
        self.s.running = False
        try:
            await self.api.shutdown()
        except Exception:
            pass
        self._write_status()

    def stop(self):
        self._stop = True

    def set_mode(self, mode: str):
        self.s.mode = "manual" if mode == "manual" else "auto"
        self.s.last_msg = f"mode -> {self.s.mode}"
        self._write_status()

    def _write_status(self):
        d = asdict(self.s)
        d["win_rate"] = round(self.s.win_rate(), 4)
        d["updated"] = self._now_local().strftime("%Y-%m-%d %H:%M:%S")
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
