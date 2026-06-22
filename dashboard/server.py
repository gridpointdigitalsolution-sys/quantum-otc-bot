"""Dashboard server — FastAPI. Serves the UI, takes the ssid, runs the LiveEngine in the
background, exposes live status. Run:  python -m dashboard.server   (then open the URL).

Works on laptop (localhost) or a VPS (bind 0.0.0.0 + subdomain). Same code either way.
"""
from __future__ import annotations
import asyncio, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from bot.live_engine import LiveEngine, STATUS_PATH, BASKET_PATH

HERE = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="Quantum OTC Bot")
_engine = {"obj": None, "task": None}


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "dashboard.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/status")
def status():
    if os.path.exists(STATUS_PATH):
        return JSONResponse(json.load(open(STATUS_PATH, encoding="utf-8")))
    return JSONResponse({"running": False, "last_msg": "idle"})


@app.get("/basket")
def basket():
    if os.path.exists(BASKET_PATH):
        return JSONResponse(json.load(open(BASKET_PATH, encoding="utf-8")))
    return JSONResponse([])


@app.post("/start")
async def start(req: Request):
    body = await req.json()
    ssid = (body.get("ssid") or "").strip()
    tz = int(body.get("tz_offset", 1))
    demo = bool(body.get("demo", True))
    if not ssid:
        return {"ok": False, "msg": "paste the ssid (the green 42[\"auth\"...] frame)"}
    if _engine["obj"] and _engine["obj"].s.running:
        return {"ok": False, "msg": "already running — stop first"}
    eng = LiveEngine(ssid, tz_offset_hours=tz, demo=demo)
    _engine["obj"] = eng
    _engine["task"] = asyncio.create_task(eng.run())
    return {"ok": True, "msg": "engine starting…"}


@app.post("/mode")
async def mode(req: Request):
    body = await req.json()
    m = body.get("mode", "auto")
    if _engine["obj"]:
        _engine["obj"].set_mode(m)
        return {"ok": True, "mode": _engine["obj"].s.mode}
    return {"ok": False, "msg": "engine not running"}


@app.post("/stop")
async def stop():
    if _engine["obj"]:
        _engine["obj"].stop()
        return {"ok": True, "msg": "stopping…"}
    return {"ok": False, "msg": "not running"}


def main():
    host = os.environ.get("BOT_HOST", "127.0.0.1")
    port = int(os.environ.get("BOT_PORT", "8000"))
    print(f"\n  Quantum OTC Bot dashboard -> http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
