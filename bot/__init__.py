"""Binary/OTC options bot — package root.

Build order (per Prompt 2): data layer -> Step 0 predictability -> ONE strategy
end-to-end -> backtest -> validate -> report -> add setups -> dashboard -> go-live.

Hard rules baked in everywhere:
- Brokers LOCKED: Deriv (official WS) + Pocket Option (ssid) ONLY.
- 1m/2m/5m OTC binaries. 1% fixed-fractional. NO MARTINGALE (structural).
- Judge by DOLLAR profit factor / drawdown / expectancy, never raw win rate.
- Payout-cap in every backtest: win=+payout%, loss=-100%. Skip below payout floor.
- No look-ahead: a bar is usable only after it closes.
"""
__version__ = "0.1.0"
