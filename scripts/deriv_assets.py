"""
Pull Deriv's tradeable asset universe from the PUBLIC API (no auth token needed for the
asset LIST). Writes deriv_assets.json + a markdown reference. Uses public app_id 1089.

This is a reference-builder for the digest/build phase. LIVE payouts (per-contract returns)
require a price proposal per symbol at trade time -- noted, not pulled here.

Run: python scripts/deriv_assets.py
"""
import asyncio, json, os, sys

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(OUT_DIR)
WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"


async def main():
    try:
        import websockets
    except ImportError:
        print("MISSING websockets lib -> run: python -m pip install websockets")
        sys.exit(1)

    async with websockets.connect(WS_URL) as ws:
        # full asset list, basic product (covers synthetics + forex + commodities + indices)
        await ws.send(json.dumps({"active_symbols": "full", "product_type": "basic"}))
        resp = json.loads(await ws.recv())

    syms = resp.get("active_symbols", [])
    if not syms:
        print("No symbols returned. Raw:", json.dumps(resp)[:400])
        sys.exit(2)

    with open(os.path.join(PROJ, "deriv_assets.json"), "w", encoding="utf-8") as f:
        json.dump(syms, f, indent=2)

    by_market = {}
    for s in syms:
        m = s.get("market_display_name", s.get("market", "?"))
        sub = s.get("submarket_display_name", s.get("submarket", "?"))
        by_market.setdefault(m, {}).setdefault(sub, []).append(s)

    lines = ["# DERIV ASSET REFERENCE (pulled from public API, app_id 1089)",
             "", f"Total tradeable symbols: {len(syms)}",
             "NOTE: live payout/return per contract requires a price proposal at trade time",
             "(varies by duration + barrier). This lists the ASSET UNIVERSE only.", ""]
    for m in sorted(by_market):
        lines.append(f"## {m}")
        for sub in sorted(by_market[m]):
            items = by_market[m][sub]
            lines.append(f"### {sub} ({len(items)})")
            for s in sorted(items, key=lambda x: x.get("display_name", "")):
                openflag = "open" if s.get("exchange_is_open") else "closed"
                lines.append(f"- {s.get('display_name')}  `{s.get('symbol')}`  ({openflag}, pip {s.get('pip')})")
            lines.append("")
    with open(os.path.join(PROJ, "DERIV-ASSETS-REFERENCE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"OK: {len(syms)} symbols across {len(by_market)} markets")
    for m in sorted(by_market):
        n = sum(len(v) for v in by_market[m].values())
        print(f"  {n:4d}  {m}")


if __name__ == "__main__":
    asyncio.run(main())
