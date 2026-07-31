#!/usr/bin/env python3
"""noctua key auth — single file (admin HTML embedded). No templates/ folder."""

ADMIN_HTML = '<!DOCTYPE html>\n<html lang="ru">\n<head>\n  <meta charset="utf-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1" />\n  <title>noctua admin</title>\n  <style>\n    :root {\n      --bg: #101012;\n      --panel: #18181c;\n      --line: #3a3420;\n      --gold: #d0ae48;\n      --gold2: #e8c45a;\n      --text: #ece8dc;\n      --muted: #8a8578;\n      --ok: #5ecf7a;\n      --bad: #e05555;\n    }\n    * { box-sizing: border-box; }\n    body {\n      margin: 0;\n      font: 14px/1.45 "Segoe UI", system-ui, sans-serif;\n      background: radial-gradient(1200px 600px at 10% -10%, #2a2414 0%, var(--bg) 55%);\n      color: var(--text);\n      min-height: 100vh;\n    }\n    .wrap { max-width: 980px; margin: 0 auto; padding: 28px 18px 60px; }\n    h1 { margin: 0 0 4px; font-size: 22px; color: var(--gold); letter-spacing: .04em; }\n    .sub { color: var(--muted); margin-bottom: 22px; }\n    .card {\n      background: var(--panel);\n      border: 1px solid var(--line);\n      border-radius: 10px;\n      padding: 16px 18px;\n      margin-bottom: 14px;\n    }\n    label { display: block; color: var(--muted); font-size: 12px; margin: 8px 0 4px; }\n    input, select, button, textarea {\n      font: inherit; border-radius: 6px; border: 1px solid #333;\n      background: #121214; color: var(--text); padding: 9px 11px;\n    }\n    input, select { width: 100%; }\n    .row { display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 10px; align-items: end; }\n    @media (max-width: 720px) { .row { grid-template-columns: 1fr 1fr; } }\n    button {\n      cursor: pointer; background: #2a2414; border-color: var(--gold);\n      color: var(--gold2); font-weight: 600; white-space: nowrap;\n    }\n    button:hover { background: #3a3018; }\n    button.danger { border-color: var(--bad); color: #ff8e8e; background: #2a1515; }\n    button.ghost { border-color: #444; color: var(--muted); }\n    .status { min-height: 1.2em; color: var(--muted); margin: 8px 0; }\n    .status.ok { color: var(--ok); }\n    .status.err { color: var(--bad); }\n    table { width: 100%; border-collapse: collapse; font-size: 13px; }\n    th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #2a2a30; vertical-align: top; }\n    th { color: var(--muted); font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }\n    code { font-family: Consolas, monospace; color: var(--gold2); }\n    .badge { display: inline-block; padding: 2px 7px; border-radius: 999px; font-size: 11px; }\n    .badge.on { background: #163222; color: var(--ok); }\n    .badge.off { background: #3a1a1a; color: #ff8e8e; }\n    .actions { display: flex; gap: 6px; flex-wrap: wrap; }\n    .login-box { max-width: 420px; margin: 80px auto; }\n    .hidden { display: none !important; }\n    .created { background: #1c1a10; border: 1px dashed var(--line); padding: 10px; border-radius: 8px; margin-top: 10px; }\n    .created code { display: block; margin: 4px 0; user-select: all; }\n  </style>\n</head>\n<body>\n  <div class="wrap">\n    <div id="loginView" class="login-box card">\n      <h1>noctua</h1>\n      <div class="sub">admin panel</div>\n      <label>Admin token</label>\n      <input id="tokenInput" type="password" placeholder="ADMIN_TOKEN с Render" autocomplete="off" />\n      <div style="margin-top:12px; display:flex; gap:8px;">\n        <button id="loginBtn">Войти</button>\n      </div>\n      <div id="loginStatus" class="status"></div>\n    </div>\n\n    <div id="appView" class="hidden">\n      <div style="display:flex; justify-content:space-between; align-items:baseline; gap:12px;">\n        <div>\n          <h1>noctua admin</h1>\n          <div class="sub">ключи · Redis</div>\n        </div>\n        <button class="ghost" id="logoutBtn">Выйти</button>\n      </div>\n\n      <div class="card">\n        <div style="font-weight:600; margin-bottom:6px; color:var(--gold);">Создать ключи</div>\n        <div class="row">\n          <div>\n            <label>Дней (0 = forever)</label>\n            <input id="days" type="number" value="30" min="0" />\n          </div>\n          <div>\n            <label>Количество</label>\n            <input id="count" type="number" value="1" min="1" max="50" />\n          </div>\n          <div>\n            <label>Note</label>\n            <input id="note" type="text" placeholder="friend1" />\n          </div>\n          <div>\n            <label>&nbsp;</label>\n            <button id="createBtn">Создать</button>\n          </div>\n        </div>\n        <div id="createStatus" class="status"></div>\n        <div id="createdBox" class="created hidden"></div>\n      </div>\n\n      <div class="card">\n        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">\n          <div style="font-weight:600; color:var(--gold);">Ключи</div>\n          <button class="ghost" id="refreshBtn">Обновить</button>\n        </div>\n        <div id="listStatus" class="status"></div>\n        <div style="overflow-x:auto;">\n          <table>\n            <thead>\n              <tr>\n                <th>Key</th>\n                <th>Status</th>\n                <th>HWID</th>\n                <th>Expires</th>\n                <th>Note</th>\n                <th>Uses</th>\n                <th></th>\n              </tr>\n            </thead>\n            <tbody id="tbody"></tbody>\n          </table>\n        </div>\n      </div>\n    </div>\n  </div>\n\n  <script>\n    const $ = (id) => document.getElementById(id);\n    const tokenKey = "noctua_admin_token";\n\n    function token() { return sessionStorage.getItem(tokenKey) || ""; }\n    function setToken(t) { sessionStorage.setItem(tokenKey, t); }\n    function clearToken() { sessionStorage.removeItem(tokenKey); }\n\n    async function api(path, opts = {}) {\n      const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});\n      headers["X-Admin-Token"] = token();\n      const res = await fetch(path, { ...opts, headers });\n      let data = {};\n      try { data = await res.json(); } catch (_) {}\n      return { res, data };\n    }\n\n    function fmtTs(v) {\n      const n = parseInt(v || "0", 10);\n      if (!n) return "—";\n      return new Date(n * 1000).toLocaleString();\n    }\n\n    function expiresLabel(row) {\n      const exp = parseInt(row.expires_at || "0", 10);\n      if (!exp) return "forever";\n      const now = Math.floor(Date.now() / 1000);\n      if (exp < now) return "expired";\n      const days = Math.ceil((exp - now) / 86400);\n      return days + "d · " + fmtTs(exp);\n    }\n\n    function showApp(on) {\n      $("loginView").classList.toggle("hidden", on);\n      $("appView").classList.toggle("hidden", !on);\n    }\n\n    async function login() {\n      const t = $("tokenInput").value.trim();\n      if (!t) { $("loginStatus").textContent = "введи token"; $("loginStatus").className = "status err"; return; }\n      setToken(t);\n      const { res, data } = await api("/v1/admin/list");\n      if (!res.ok || !data.ok) {\n        clearToken();\n        $("loginStatus").textContent = "неверный token или redis";\n        $("loginStatus").className = "status err";\n        return;\n      }\n      showApp(true);\n      renderList(data.keys || []);\n    }\n\n    function renderList(keys) {\n      const tb = $("tbody");\n      tb.innerHTML = "";\n      if (!keys.length) {\n        tb.innerHTML = "<tr><td colspan=\'7\' style=\'color:var(--muted)\'>пусто</td></tr>";\n        return;\n      }\n      for (const row of keys) {\n        const banned = String(row.banned || "0") !== "0";\n        const tr = document.createElement("tr");\n        tr.innerHTML = `\n          <td><code>${row.key || ""}</code></td>\n          <td><span class="badge ${banned ? "off" : "on"}">${banned ? "banned" : "active"}</span></td>\n          <td style="max-width:140px; overflow:hidden; text-overflow:ellipsis;">${row.hwid || "—"}</td>\n          <td>${expiresLabel(row)}</td>\n          <td>${row.note || ""}</td>\n          <td>${row.use_count || 0}</td>\n          <td class="actions">\n            <button data-act="copy" data-key="${row.key}">Copy</button>\n            <button data-act="hwid" data-key="${row.key}">Reset HWID</button>\n            <button class="danger" data-act="ban" data-key="${row.key}" ${banned ? "disabled" : ""}>Ban</button>\n          </td>`;\n        tb.appendChild(tr);\n      }\n    }\n\n    async function refresh() {\n      $("listStatus").textContent = "loading...";\n      $("listStatus").className = "status";\n      const { res, data } = await api("/v1/admin/list");\n      if (!res.ok || !data.ok) {\n        $("listStatus").textContent = data.msg || "error";\n        $("listStatus").className = "status err";\n        if (res.status === 401) { clearToken(); showApp(false); }\n        return;\n      }\n      $("listStatus").textContent = (data.keys || []).length + " keys";\n      $("listStatus").className = "status ok";\n      renderList(data.keys || []);\n    }\n\n    async function createKeys() {\n      const days = parseInt($("days").value || "30", 10);\n      const count = parseInt($("count").value || "1", 10);\n      const note = $("note").value || "";\n      $("createStatus").textContent = "creating...";\n      $("createStatus").className = "status";\n      $("createdBox").classList.add("hidden");\n      const { res, data } = await api("/v1/admin/create", {\n        method: "POST",\n        body: JSON.stringify({ days, count, note }),\n      });\n      if (!res.ok || !data.ok) {\n        $("createStatus").textContent = data.msg || "failed";\n        $("createStatus").className = "status err";\n        return;\n      }\n      const keys = data.keys || [];\n      $("createStatus").textContent = "ok: " + keys.length;\n      $("createStatus").className = "status ok";\n      const box = $("createdBox");\n      box.classList.remove("hidden");\n      box.innerHTML = "<div style=\'color:var(--muted);margin-bottom:6px\'>новые ключи (клик = выделить):</div>" +\n        keys.map(k => `<code>${k}</code>`).join("");\n      refresh();\n    }\n\n    $("loginBtn").onclick = login;\n    $("tokenInput").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });\n    $("logoutBtn").onclick = () => { clearToken(); showApp(false); };\n    $("refreshBtn").onclick = refresh;\n    $("createBtn").onclick = createKeys;\n\n    $("tbody").addEventListener("click", async (e) => {\n      const btn = e.target.closest("button");\n      if (!btn) return;\n      const act = btn.dataset.act;\n      const key = btn.dataset.key;\n      if (act === "copy") {\n        navigator.clipboard.writeText(key);\n        $("listStatus").textContent = "copied";\n        $("listStatus").className = "status ok";\n        return;\n      }\n      if (act === "hwid") {\n        const { res, data } = await api("/v1/admin/reset_hwid", { method: "POST", body: JSON.stringify({ key }) });\n        $("listStatus").textContent = res.ok && data.ok ? "hwid reset" : (data.msg || "fail");\n        $("listStatus").className = res.ok && data.ok ? "status ok" : "status err";\n        refresh();\n      }\n      if (act === "ban") {\n        if (!confirm("Ban " + key + "?")) return;\n        const { res, data } = await api("/v1/admin/revoke", { method: "POST", body: JSON.stringify({ key }) });\n        $("listStatus").textContent = res.ok && data.ok ? "banned" : (data.msg || "fail");\n        $("listStatus").className = res.ok && data.ok ? "status ok" : "status err";\n        refresh();\n      }\n    });\n\n    if (token()) {\n      showApp(true);\n      refresh();\n    }\n  </script>\n</body>\n</html>\n'

import hashlib
import os
import re
import secrets
import string
import time
from typing import Any, Dict, Optional

import redis
from flask import Flask, Response, jsonify, request

APP_NAME = "noctua"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "CHANGE_ME_ADMIN_TOKEN")
APP_ID = os.environ.get("APP_ID", "noctua-gta")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

KEY_PREFIX = "noctua:key:"
KEY_INDEX = "noctua:keys"

app = Flask(__name__)

_r = None  # type: Optional[redis.Redis]


def r():
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
    data = r().hgetall(kname(key))
    if not data:
        return None
    data["key"] = key
    return data


def _admin_response():
    return Response(ADMIN_HTML, mimetype="text/html; charset=utf-8")


@app.get("/")
def root():
    return _admin_response()


@app.get("/admin")
def admin_page():
    return _admin_response()


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
        return jsonify(ok=False, msg="redis: %s" % e), 503

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
        return jsonify(ok=False, msg="redis: %s" % e), 503
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
        return jsonify(ok=False, msg="redis: %s" % e), 503
    return jsonify(ok=True)


@app.get("/v1/admin/list")
def admin_list():
    if not require_admin():
        return jsonify(ok=False, msg="unauthorized"), 401
    out = []
    try:
        keys = list(r().smembers(KEY_INDEX))
        for k in keys[:500]:
            row = get_key_row(k)
            if row:
                out.append(row)
        out.sort(key=lambda x: int(x.get("created_at") or 0), reverse=True)
    except Exception as e:
        return jsonify(ok=False, msg="redis: %s" % e), 503
    return jsonify(ok=True, keys=out)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
