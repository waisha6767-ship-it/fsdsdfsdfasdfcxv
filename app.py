#!/usr/bin/env python3
"""
noctua key auth API (Redis)
---------------------------
POST /v1/auth          { "key", "hwid", "app" } -> { ok, days_left, msg }
POST /v1/admin/create  Header X-Admin-Token + { days, note, count }
POST /v1/admin/revoke  Header X-Admin-Token + { key }
POST /v1/admin/reset_hwid
GET  /v1/admin/list
GET  /health

Env:
  REDIS_URL     redis://... или rediss://... (Upstash)
  ADMIN_TOKEN   секрет админки
  APP_ID        noctua-gta
"""

import hashlib
import os
import re
import secrets
import string
import time
from typing import Any, Dict, Optional

import redis
from flask import Flask, jsonify, render_template, request

APP_NAME = "noctua"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "CHANGE_ME_ADMIN_TOKEN")
APP_ID = os.environ.get("APP_ID", "noctua-gta")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

KEY_PREFIX = "noctua:key:"
KEY_INDEX = "noctua:keys"

app = Flask(__name__)

_r = None  # type: Optional[redis.Redis]


def r():
    # type: () -> redis.Redis
    global _r
    if _r is None:
        _r = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _r


def kname(key):
    return KEY_PREFIX + key


def gen_key():
    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "-".join(parts)


def normalize_key(k):
    k = (k or "").strip().upper().replace(" ", "")
    return re.sub(r"[^A-Z0-9\-]", "", k)


def require_admin():
    tok = request.headers.get("X-Admin-Token", "")
    return bool(tok) and secrets.compare_digest(tok, ADMIN_TOKEN)


def get_key_row(key):
    # type: (str) -> Optional[Dict[str, Any]]
    data = r().hgetall(kname(key))
    if not data:
        return None
    data["key"] = key
    return data


@app.get("/")
def root():
    return render_template("admin.html")


@app.get("/admin")
def admin_page():
    return render_template("admin.html")


@app.get("/health")
def health():
    try:
        pong = r().ping()
    except Exception as e:
        return jsonify(ok=False, redis=False, err=str(e)), 503
    return jsonify(ok=True, app=APP_NAME, redis=bool(pong), ts=int(time.time()))


@app.post("/v1/auth")
def auth():
    data = request.get_json(silent=True) or {}
    key = normalize_key(str(data.get("key", "")))
    hwid = str(data.get("hwid", "")).strip()[:128]
    app_id = str(data.get("app", "")).strip()

    if app_id and app_id != APP_ID:
        return jsonify(ok=False, msg="bad app"), 403
    if not re.fullmatch(r"[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}", key):
        return jsonify(ok=False, msg="bad key"), 400
    if len(hwid) < 8:
        return jsonify(ok=False, msg="bad hwid"), 400

    now = int(time.time())
    try:
        row = get_key_row(key)
    except Exception:
        return jsonify(ok=False, msg="redis down"), 503

    if not row:
        return jsonify(ok=False, msg="invalid"), 401
    if int(row.get("banned", "0") or 0) != 0:
        return jsonify(ok=False, msg="banned"), 403

    exp = int(row.get("expires_at", "0") or 0)
    if exp != 0 and exp < now:
        return jsonify(ok=False, msg="expired"), 403

    bound = row.get("hwid") or ""
    if bound and bound != hwid:
        return jsonify(ok=False, msg="hwid mismatch"), 403

    pipe = r().pipeline()
    hk = kname(key)
    if not bound:
        pipe.hset(hk, mapping={"hwid": hwid, "last_seen": str(now)})
    else:
        pipe.hset(hk, "last_seen", str(now))
    pipe.hincrby(hk, "use_count", 1)
    pipe.execute()

    days_left = -1 if exp == 0 else max(0, (exp - now) // 86400)
    nonce = secrets.token_hex(8)
    sig = hashlib.sha256(f"{key}|{hwid}|{nonce}|{APP_ID}".encode()).hexdigest()[:32]
    return jsonify(ok=True, days_left=days_left, msg="ok", nonce=nonce, sig=sig)


@app.post("/v1/admin/create")
def admin_create():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    days = int(data.get("days", 30))
    note = str(data.get("note", ""))[:120]
    count = int(data.get("count", 1))
    count = max(1, min(count, 50))
    now = int(time.time())
    expires = 0 if days <= 0 else now + days * 86400

    created = []
    try:
        rd = r()
        for _ in range(count):
            for _try in range(20):
                k = gen_key()
                hk = kname(k)
                # NX — не перезаписываем существующий
                ok = rd.hsetnx(hk, "created_at", str(now))
                if not ok:
                    continue
                rd.hset(
                    hk,
                    mapping={
                        "hwid": "",
                        "expires_at": str(expires),
                        "banned": "0",
                        "note": note,
                        "last_seen": "",
                        "use_count": "0",
                    },
                )
                rd.sadd(KEY_INDEX, k)
                created.append(k)
                break
    except Exception as e:
        return jsonify(ok=False, msg=f"redis: {e}"), 503

    return jsonify(ok=True, keys=created, days=days, expires_at=expires)


@app.post("/v1/admin/revoke")
def admin_revoke():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    key = normalize_key(str(data.get("key", "")))
    try:
        if not r().exists(kname(key)):
            return jsonify(ok=False, msg="not found"), 404
        r().hset(kname(key), "banned", "1")
    except Exception as e:
        return jsonify(ok=False, msg=f"redis: {e}"), 503
    return jsonify(ok=True)


@app.post("/v1/admin/reset_hwid")
def admin_reset_hwid():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    key = normalize_key(str(data.get("key", "")))
    try:
        if not r().exists(kname(key)):
            return jsonify(ok=False, msg="not found"), 404
        r().hset(kname(key), "hwid", "")
    except Exception as e:
        return jsonify(ok=False, msg=f"redis: {e}"), 503
    return jsonify(ok=True)


@app.get("/v1/admin/list")
def admin_list():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    out = []
    try:
        keys = list(r().smembers(KEY_INDEX))
        keys.sort(reverse=True)
        for k in keys[:500]:
            row = get_key_row(k)
            if row:
                out.append(row)
        out.sort(key=lambda x: int(x.get("created_at") or 0), reverse=True)
    except Exception as e:
        return jsonify(ok=False, msg=f"redis: {e}"), 503
    return jsonify(ok=True, keys=out)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
