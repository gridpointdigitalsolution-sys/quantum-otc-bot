"""Dashboard server — FastAPI. Serves the UI, takes the ssid, runs the LiveEngine in the
background, exposes live status. Run:  python -m dashboard.server   (then open the URL).

Works on laptop (localhost) or a VPS (bind 0.0.0.0 + subdomain). Same code either way.

PIN GATE: if secrets/pin.txt (or env BOT_PIN) is set, all data/control endpoints require the
matching PIN in the X-PIN header. The PIN lives ONLY on the server (gitignored) — never in the
repo. If no PIN is configured, the dashboard is open (convenient for first setup / demo).
"""
from __future__ import annotations
import asyncio, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from bot.live_engine import LiveEngine, STATUS_PATH, BASKET_PATH

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
app = FastAPI(title="Quantum OTC Bot")
_engine = {"obj": None, "task": None}


def _load_pin():
    p = os.path.join(PROJ, "secrets", "pin.txt")
    if os.path.exists(p):
        try:
            return open(p, encoding="utf-8").read().strip()
        except Exception:
            pass
    return os.environ.get("BOT_PIN", "").strip()


PIN = _load_pin()


def _auth(req: Request) -> bool:
    if not PIN:
        return True   # no PIN configured -> open
    return req.headers.get("x-pin", "") == PIN


def _deny():
    return JSONResponse({"ok": False, "auth": False, "msg": "PIN required"}, status_code=401)


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "dashboard.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/ping")
def ping():
    # tells the dashboard whether a PIN is needed (no secret leaked)
    return {"pin_required": bool(PIN)}


@app.get("/status")
def status(req: Request):
    if not _auth(req):
        return _deny()
    if os.path.exists(STATUS_PATH):
        return JSONResponse(json.load(open(STATUS_PATH, encoding="utf-8")))
    return JSONResponse({"running": False, "last_msg": "idle"})


@app.get("/basket")
def basket(req: Request):
    if not _auth(req):
        return _deny()
    if os.path.exists(BASKET_PATH):
        return JSONResponse(json.load(open(BASKET_PATH, encoding="utf-8")))
    return JSONResponse([])


@app.post("/start")
async def start(req: Request):
    if not _auth(req):
        return _deny()
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
    if not _auth(req):
        return _deny()
    body = await req.json()
    m = body.get("mode", "auto")
    if _engine["obj"]:
        _engine["obj"].set_mode(m)
        return {"ok": True, "mode": _engine["obj"].s.mode}
    return {"ok": False, "msg": "engine not running"}


@app.post("/stop")
async def stop(req: Request):
    if not _auth(req):
        return _deny()
    if _engine["obj"]:
        _engine["obj"].stop()
        return {"ok": True, "msg": "stopping…"}
    return {"ok": False, "msg": "not running"}


def main():
    host = os.environ.get("BOT_HOST", "127.0.0.1")
    port = int(os.environ.get("BOT_PORT", "8000"))
    print(f"\n  Quantum OTC Bot dashboard -> http://{host}:{port}  (PIN {'ON' if PIN else 'off'})\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
