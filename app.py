#!/usr/bin/env python3
"""
noctua key auth API
-------------------
POST /v1/auth          { "key", "hwid", "app" } -> { ok, days_left, msg }
POST /v1/admin/create  Header X-Admin-Token + { days, note, count }
POST /v1/admin/revoke  Header X-Admin-Token + { key }
GET  /v1/admin/list    Header X-Admin-Token
GET  /health
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import string
import time
from contextlib import closing
from pathlib import Path

from flask import Flask, jsonify, request

APP_NAME = "noctua"
DB_PATH = Path(os.environ.get("KEYS_DB", Path(__file__).with_name("keys.db")))
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "CHANGE_ME_ADMIN_TOKEN")
# опционально: только этот app-id принимает лоадер
APP_ID = os.environ.get("APP_ID", "noctua-gta")

app = Flask(__name__)


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(db()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS keys (
                key TEXT PRIMARY KEY,
                hwid TEXT,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                banned INTEGER NOT NULL DEFAULT 0,
                note TEXT,
                last_seen INTEGER,
                use_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def gen_key() -> str:
    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "-".join(parts)


def normalize_key(k: str) -> str:
    k = (k or "").strip().upper().replace(" ", "")
    k = re.sub(r"[^A-Z0-9\-]", "", k)
    return k


def require_admin() -> bool:
    tok = request.headers.get("X-Admin-Token", "")
    return tok and secrets.compare_digest(tok, ADMIN_TOKEN)


@app.get("/health")
def health():
    return jsonify(ok=True, app=APP_NAME, ts=int(time.time()))


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
    with closing(db()) as conn:
        row = conn.execute("SELECT * FROM keys WHERE key=?", (key,)).fetchone()
        if not row:
            return jsonify(ok=False, msg="invalid"), 401
        if int(row["banned"]) != 0:
            return jsonify(ok=False, msg="banned"), 403
        if int(row["expires_at"]) != 0 and int(row["expires_at"]) < now:
            return jsonify(ok=False, msg="expired"), 403

        bound = row["hwid"] or ""
        if bound and bound != hwid:
            return jsonify(ok=False, msg="hwid mismatch"), 403
        if not bound:
            conn.execute(
                "UPDATE keys SET hwid=?, last_seen=?, use_count=use_count+1 WHERE key=?",
                (hwid, now, key),
            )
        else:
            conn.execute(
                "UPDATE keys SET last_seen=?, use_count=use_count+1 WHERE key=?",
                (now, key),
            )
        conn.commit()

        exp = int(row["expires_at"])
        days_left = -1 if exp == 0 else max(0, (exp - now) // 86400)
        # token — на будущее (сессия), сейчас просто подпись ответа
        nonce = secrets.token_hex(8)
        sig = hashlib.sha256(f"{key}|{hwid}|{nonce}|{APP_ID}".encode()).hexdigest()[:32]
        return jsonify(
            ok=True,
            days_left=days_left,
            msg="ok",
            nonce=nonce,
            sig=sig,
        )


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
    with closing(db()) as conn:
        for _ in range(count):
            for _try in range(20):
                k = gen_key()
                try:
                    conn.execute(
                        "INSERT INTO keys(key, hwid, created_at, expires_at, banned, note, last_seen, use_count)"
                        " VALUES(?,?,?,?,0,?,NULL,0)",
                        (k, "", now, expires, note),
                    )
                    created.append(k)
                    break
                except sqlite3.IntegrityError:
                    continue
        conn.commit()
    return jsonify(ok=True, keys=created, days=days, expires_at=expires)


@app.post("/v1/admin/revoke")
def admin_revoke():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    key = normalize_key(str(data.get("key", "")))
    with closing(db()) as conn:
        cur = conn.execute("UPDATE keys SET banned=1 WHERE key=?", (key,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify(ok=False, msg="not found"), 404
    return jsonify(ok=True)


@app.post("/v1/admin/reset_hwid")
def admin_reset_hwid():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    key = normalize_key(str(data.get("key", "")))
    with closing(db()) as conn:
        cur = conn.execute("UPDATE keys SET hwid='' WHERE key=?", (key,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify(ok=False, msg="not found"), 404
    return jsonify(ok=True)


@app.get("/v1/admin/list")
def admin_list():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT key, hwid, created_at, expires_at, banned, note, last_seen, use_count "
            "FROM keys ORDER BY created_at DESC LIMIT 500"
        ).fetchall()
    return jsonify(ok=True, keys=[dict(r) for r in rows])


init_db()

if __name__ == "__main__":
    # локальный тест: python app.py
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
