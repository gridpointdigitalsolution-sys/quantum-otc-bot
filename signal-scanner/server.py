"""Quantum Signal Scanner — central hub (FastAPI).

SELLABLE SIGNAL-FEED MODEL:
  Your VPS runs MT5 + the proven engines (TITAN/PHOENIX/RONIN/gold) in SIGNAL mode.
  When a setup fires, the Signal EA POSTs the signal here. This hub:
    • stores it (data/signals.json)
    • pushes it to your Telegram channel (paying subscribers)
    • serves a live web dashboard (paying subscribers)
  Subscribers receive signals; they NEVER get the EA. Your edge stays protected.

Run:  python server.py   (binds 127.0.0.1:8100 by default; put nginx/Cloudflare in front)

SECURITY:
  - EA→hub POST is authenticated with SIGNAL_SECRET (env or secrets/signal_secret.txt).
  - Dashboard read can be gated with BOT_PIN (subscriber access placeholder until real billing).
  - Telegram creds live in secrets/ (gitignored), never in the repo.
"""
from __future__ import annotations
import os, json, time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn
import urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SIGNALS_PATH = os.path.join(DATA, "signals.json")
SECRETS = os.path.join(HERE, "secrets")
MAX_SIGNALS = 300

app = FastAPI(title="Quantum Signal Scanner")


def _read(path, default):
    try:
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
    except Exception:
        pass
    return default


def _secret(name, env):
    p = os.path.join(SECRETS, name)
    if os.path.exists(p):
        try:
            return open(p, encoding="utf-8").read().strip()
        except Exception:
            pass
    return os.environ.get(env, "").strip()


SIGNAL_SECRET = _secret("signal_secret.txt", "SIGNAL_SECRET")
PIN = _secret("pin.txt", "BOT_PIN")
TG_TOKEN = _secret("tg_token.txt", "TG_TOKEN")
TG_CHANNEL = _secret("tg_channel.txt", "TG_CHANNEL")   # @channel or numeric chat id


@app.middleware("http")
async def _no_cache(request, call_next):
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


def _auth_read(req: Request) -> bool:
    if not PIN:
        return True
    return req.headers.get("x-pin", "") == PIN


def _tg_push(text: str):
    """Broadcast a signal to the Telegram channel. Fully wrapped — never breaks signal intake."""
    if not (TG_TOKEN and TG_CHANNEL):
        return
    try:
        url = ("https://api.telegram.org/bot" + TG_TOKEN + "/sendMessage?" +
               urllib.parse.urlencode({"chat_id": TG_CHANNEL, "text": text, "parse_mode": "HTML"}))
        urllib.request.urlopen(url, timeout=8)
    except Exception:
        pass


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "dashboard.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/ping")
def ping():
    return {"ok": True, "pin_required": bool(PIN)}


@app.post("/signal")
async def signal(req: Request):
    """Called by the Signal EA when a setup fires. Auth via X-SECRET header or ?secret=."""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "msg": "bad json"}, status_code=400)
    sec = req.headers.get("x-secret", "") or req.query_params.get("secret", "")
    if SIGNAL_SECRET and sec != SIGNAL_SECRET:
        return JSONResponse({"ok": False, "msg": "unauthorized"}, status_code=401)

    now = time.time()
    try:
        valid_secs = int(body.get("valid_secs", 600))
    except Exception:
        valid_secs = 600
    if valid_secs <= 0:
        valid_secs = 600
    sig = {
        "ts": now,                                       # epoch when signal fired (freshness source of truth)
        "t": time.strftime("%Y-%m-%d %H:%M:%S"),
        "valid_secs": valid_secs,                        # entry window length
        "expires_ts": now + valid_secs,                  # epoch when the entry window closes
        "pair": str(body.get("pair", "?")),
        "dir": str(body.get("dir", "?")).upper(),       # BUY / SELL
        "entry": body.get("entry"),
        "sl": body.get("sl"),
        "tp": body.get("tp"),
        "tf": str(body.get("tf", "")),
        "reason": str(body.get("reason", "")),
        "engine": str(body.get("engine", "")),
    }
    os.makedirs(DATA, exist_ok=True)
    sigs = _read(SIGNALS_PATH, [])
    sigs = [sig] + sigs
    sigs = sigs[:MAX_SIGNALS]
    json.dump(sigs, open(SIGNALS_PATH, "w", encoding="utf-8"))

    arrow = "🟢 BUY" if sig["dir"] == "BUY" else "🔴 SELL"
    mins = max(1, round(valid_secs / 60))
    expires_hm = time.strftime("%H:%M", time.localtime(sig["expires_ts"]))
    msg = (f"<b>{arrow} {sig['pair']}</b>  ({sig['tf']})\n"
           f"Entry: <b>{sig['entry']}</b>\n"
           f"Stop loss: {sig['sl']}\n"
           f"Take profit: {sig['tp']}\n"
           f"⏱ <b>Enter within {mins} min</b> — expires {expires_hm}\n"
           f"Reason: {sig['reason']}\n"
           f"<i>Quantum Signal Scanner · {sig['t']}</i>")
    _tg_push(msg)
    return {"ok": True}


@app.get("/signals")
def signals(req: Request):
    if not _auth_read(req):
        return JSONResponse({"ok": False, "auth": False}, status_code=401)
    return JSONResponse(_read(SIGNALS_PATH, []))


def main():
    host = os.environ.get("SIGNAL_HOST", "127.0.0.1")
    port = int(os.environ.get("SIGNAL_PORT", "8100"))
    print(f"\n  Quantum Signal Scanner -> http://{host}:{port}  (PIN {'ON' if PIN else 'off'} · "
          f"Telegram {'ON' if (TG_TOKEN and TG_CHANNEL) else 'off'})\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
