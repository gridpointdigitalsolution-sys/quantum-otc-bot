"""
Pull LIVE payout/return % per Deriv asset via the public price-proposal call (no token
needed -- pricing is public). For each open symbol, asks a 5-minute Rise(CALL) + Fall(PUT)
proposal with $1 stake; return% = (payout/stake - 1) * 100. SAME call the dashboard uses.

Run: python scripts/deriv_payouts.py   (after deriv_assets.py)
"""
import asyncio, json as _json, os, sys

OUT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(OUT)
WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
STAKE = 1.0
DURATION = 5
DURATION_UNIT = "m"


async def get_payout(ws, symbol, ctype):
    req = {"proposal": 1, "amount": STAKE, "basis": "stake", "contract_type": ctype,
           "currency": "USD", "duration": DURATION, "duration_unit": DURATION_UNIT,
           "symbol": symbol}
    await ws.send(_json.dumps(req))
    r = _json.loads(await ws.recv())
    if "error" in r:
        return None, r["error"].get("message", "error")
    payout = float(r["proposal"]["payout"])
    return (payout / STAKE - 1.0) * 100.0, None


async def main():
    try:
        import websockets
    except ImportError:
        print("MISSING websockets -> python -m pip install websockets"); sys.exit(1)

    with open(os.path.join(PROJ, "deriv_assets.json"), encoding="utf-8") as f:
        syms = _json.load(f)

    rows = []
    async with websockets.connect(WS_URL) as ws:
        for s in syms:
            sym = s.get("symbol"); name = s.get("display_name")
            market = s.get("market_display_name", "?")
            if not s.get("exchange_is_open"):
                rows.append((market, name, sym, None, None, "closed")); continue
            call_ret, err = await get_payout(ws, sym, "CALL")
            put_ret, _ = await get_payout(ws, sym, "PUT")
            rows.append((market, name, sym, call_ret, put_ret, err or "ok"))
            await asyncio.sleep(0.4)

    rows.sort(key=lambda x: (x[0], -(x[3] if x[3] is not None else -999)))
    lines = ["# DERIV LIVE PAYOUT REFERENCE",
             "(5-min Rise/Fall, $1 stake, public pricing app_id 1089)", "",
             "return% = (payout/stake - 1) x 100. >=90% normal floor, >=85% off-peak floor.",
             "Live values shift; this is a SNAPSHOT. Dashboard pulls this same call in real time.",
             "", "| Market | Asset | Symbol | CALL ret% | PUT ret% | status |",
             "|---|---|---|---|---|---|"]
    for m, name, sym, cr, pr, st in rows:
        crs = f"{cr:.1f}" if cr is not None else "-"
        prs = f"{pr:.1f}" if pr is not None else "-"
        lines.append(f"| {m} | {name} | `{sym}` | {crs} | {prs} | {st} |")
    with open(os.path.join(PROJ, "DERIV-PAYOUTS-REFERENCE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    ok = [r for r in rows if r[3] is not None]
    print(f"OK: priced {len(ok)}/{len(rows)} open symbols")
    for m, name, sym, cr, pr, st in ok[:15]:
        print(f"  {cr:6.1f}%  {name}  ({sym})")


if __name__ == "__main__":
    asyncio.run(main())
