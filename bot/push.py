"""Web Push (VAPID) — sends a lock-screen notification to subscribed phones when a trade
goes LIVE, even if the app is closed.

Design:
- VAPID keypair auto-generated once into secrets/vapid.json (gitignored). No Google/Firebase
  account needed — standard Web Push with VAPID works on Android Chrome PWAs out of the box.
- Phone subscriptions stored in secrets/push_subs.json (gitignored).
- Everything heavy (cryptography, pywebpush) is imported lazily and wrapped, so importing this
  module — or a missing dependency — can NEVER crash the trading engine. Push failing just
  means no phone alert; trading continues untouched.
"""
from __future__ import annotations
import os, json, base64, threading

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJ = os.path.dirname(_HERE)
_SECRETS = os.path.join(_PROJ, "secrets")
VAPID_PATH = os.path.join(_SECRETS, "vapid.json")
SUBS_PATH = os.path.join(_SECRETS, "push_subs.json")
CLAIM_SUB = "mailto:cbnotion02@gmail.com"

_lock = threading.Lock()


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _gen_vapid() -> dict:
    """Create a fresh VAPID keypair. private = PKCS8 PEM (for pywebpush); public = the
    base64url uncompressed point the browser needs as applicationServerKey."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_point = priv.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return {"private_pem": priv_pem, "public_key": _b64u(pub_point)}


def get_vapid() -> dict | None:
    """Load the keypair, creating + persisting it on first use. None if crypto unavailable."""
    try:
        with _lock:
            if os.path.exists(VAPID_PATH):
                return json.load(open(VAPID_PATH, encoding="utf-8"))
            os.makedirs(_SECRETS, exist_ok=True)
            v = _gen_vapid()
            json.dump(v, open(VAPID_PATH, "w", encoding="utf-8"))
            return v
    except Exception:
        return None


def get_public_key() -> str | None:
    v = get_vapid()
    return v["public_key"] if v else None


def load_subs() -> list:
    try:
        if os.path.exists(SUBS_PATH):
            return json.load(open(SUBS_PATH, encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_subs(subs: list):
    try:
        os.makedirs(_SECRETS, exist_ok=True)
        json.dump(subs, open(SUBS_PATH, "w", encoding="utf-8"))
    except Exception:
        pass


def add_sub(sub: dict) -> bool:
    """Register a phone. De-dupes on endpoint."""
    try:
        ep = sub.get("endpoint")
        if not ep:
            return False
        with _lock:
            subs = load_subs()
            if not any(s.get("endpoint") == ep for s in subs):
                subs.append(sub)
                _save_subs(subs)
        return True
    except Exception:
        return False


def send_all(title: str, body: str, url: str = "/", tag: str = "otc-trade"):
    """Send a push to every subscribed phone. Blocking (run in an executor). Drops dead subs.
    Wrapped end-to-end — any failure is swallowed so trading is never affected."""
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        return  # dependency not installed yet -> silently skip
    v = get_vapid()
    if not v:
        return
    subs = load_subs()
    if not subs:
        return
    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    dead = []
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=v["private_pem"],
                vapid_claims={"sub": CLAIM_SUB},
                ttl=120,
            )
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                dead.append(sub.get("endpoint"))
        except Exception:
            pass
    if dead:
        with _lock:
            subs = [s for s in load_subs() if s.get("endpoint") not in dead]
            _save_subs(subs)
