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
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
import uvicorn

from bot.live_engine import LiveEngine, STATUS_PATH, BASKET_PATH
from bot import push

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ACTIVE = os.path.join(PROJ, "secrets", "active.json")   # persisted session (gitignored)
app = FastAPI(title="Quantum OTC Bot")
_engine = {"obj": None, "task": None}


@app.middleware("http")
async def _no_cache(request, call_next):
    # NEVER cache: dashboard + data are always fresh (no stale UI / stale numbers, ever)
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


def _save_active(ssid, tz, demo):
    try:
        os.makedirs(os.path.dirname(ACTIVE), exist_ok=True)
        json.dump({"ssid": ssid, "tz": tz, "demo": demo}, open(ACTIVE, "w"))
    except Exception:
        pass


def _clear_active():
    try:
        os.remove(ACTIVE)
    except Exception:
        pass


def _spawn(ssid, tz, demo):
    eng = LiveEngine(ssid, tz_offset_hours=tz, demo=demo)
    _engine["obj"] = eng
    _engine["task"] = asyncio.create_task(eng.run())


@app.on_event("startup")
async def _resume():
    # AUTO-RESUME after reboot/crash: if a session was saved, reconnect automatically.
    if os.path.exists(ACTIVE):
        try:
            d = json.load(open(ACTIVE))
            _spawn(d["ssid"], int(d.get("tz", 1)), bool(d.get("demo", True)))
        except Exception:
            pass


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


# ── PWA + Web Push ────────────────────────────────────────────────────────────
@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(HERE, "manifest.json"), media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    # served from root so it controls the whole app scope
    return FileResponse(os.path.join(HERE, "sw.js"), media_type="application/javascript")


@app.get("/icon-192.png")
def icon192():
    return FileResponse(os.path.join(HERE, "icon-192.png"), media_type="image/png")


@app.get("/icon-512.png")
def icon512():
    return FileResponse(os.path.join(HERE, "icon-512.png"), media_type="image/png")


@app.get("/vapid")
def vapid():
    # public key is meant to be public — the browser needs it to subscribe
    return {"key": push.get_public_key()}


@app.post("/subscribe")
async def subscribe(req: Request):
    if not _auth(req):
        return _deny()
    try:
        sub = await req.json()
    except Exception:
        return {"ok": False, "msg": "bad subscription"}
    ok = push.add_sub(sub)
    return {"ok": ok}


@app.get("/status")
def status(req: Request):
    if not _auth(req):
        return _deny()
    eng = _engine["obj"]
    # TRUTHFUL: only report "running" if an engine is actually alive (ignore stale status file)
    if eng is None or not eng.s.running:
        return JSONResponse({"running": False, "connected": False,
                             "last_msg": "not running — paste ssid + Start",
                             "pairs": [], "pair_status": [], "open_positions": [],
                             "recent": [], "signals": [], "balance": None,
                             "day_pnl": 0, "win_rate": 0, "day_trades": 0,
                             "wins": 0, "losses": 0, "open_trades": 0,
                             "session": "-", "session_trades": 0, "consec_losses": 0,
                             "mode": "auto"})
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
    _save_active(ssid, tz, demo)      # persist so it auto-resumes after reboot/crash
    _spawn(ssid, tz, demo)
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
    _clear_active()                   # intentional stop -> don't auto-resume
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
