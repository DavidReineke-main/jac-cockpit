"""JAC Admin Cockpit backend.

- Google sign-in identifies the person; a one-time forum login links the Google account to a forum user id.
- The forum user id is looked up in the ORBAT and Course Tracker to find squadron, flight, rank and post.
  That decides what the person can edit.
- The Google Sheets stay the source of truth. The server reads them (so they can be made private later),
  caches them for a few minutes and hands the CSV to signed-in JAC members. The ORBAT is public.
- Entries (staffing, checklists, settings, cycle, access) live in SQLite on the server.

Run:  uvicorn server.app:app --host 127.0.0.1 --port 8080
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from starlette.middleware.sessions import SessionMiddleware

from .forum import new_code, profile_contains

ROOT = Path(__file__).resolve().parent.parent
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") == "1"
DB_PATH = os.environ.get("DB_PATH", str(ROOT / "data" / "cockpit.db"))
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "300"))
if not SESSION_SECRET:
    raise SystemExit("Set SESSION_SECRET (a long random string) in the environment")

SHEETS = {
    "orbat": ("1ALQxRZgGtflI0tm2lSOu5JJpt8fazxEu-Of3Q0TRANk", "1323797389"),
    "ua": ("13GOwG_tfkFuXcJt1tMu4f8RNaGRAvTpKhBbYcAqGZzA", "290771582"),
    "roster": ("1GRENwxiY7DC5fLbue12XAeLsa_wsnKCOy3vvGzcY_Ok", "1766701879"),
    "logi": ("17yeIDGcKKAs13syNLe6sg5K-bp4pAMTe-urv2u-vutk", "0"),
    "reinsert": ("1UoaMaeLbR8tPd2YKGLoAhHnZkDz2YAPpcvuES6SK5xY", "234200102"),
    "receipt": ("17yeIDGcKKAs13syNLe6sg5K-bp4pAMTe-urv2u-vutk", "739710028"),
    "limits": ("17yeIDGcKKAs13syNLe6sg5K-bp4pAMTe-urv2u-vutk", "1903594608"),
}
PUBLIC_SHEETS = {"orbat"}
ENTRY_TYPES = {"staffing", "check", "setting", "cycle", "roles"}

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, session_cookie="jac_session",
                   max_age=30 * 24 * 3600, same_site="lax", https_only=COOKIE_SECURE)


# ---------- storage ----------
def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("create table if not exists links(google_sub text primary key, email text, forum_uid text, forum_display text, linked_at text)")
    con.execute("create table if not exists entries(id integer primary key, ts text, type text, key text, payload text, author_uid text)")
    return con


# ---------- sheets, cached ----------
_cache: dict[str, tuple[float, str]] = {}


async def sheet_csv(name: str) -> str:
    hit = _cache.get(name)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    sid, gid = SHEETS[name]
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(f"https://docs.google.com/spreadsheets/d/{sid}/export", params={"format": "csv", "gid": gid})
    if r.status_code != 200:
        if hit:
            return hit[1]
        raise HTTPException(502, f"Could not read the {name} sheet")
    _cache[name] = (time.time(), r.text)
    return r.text


def squash(s):
    return re.sub(r"\s+", " ", s or "").strip()


async def people() -> list[dict]:
    rows = list(csv.reader(io.StringIO(await sheet_csv("orbat"))))
    out, sq, fl = [], "", ""
    for r in rows[3:]:
        r = r + [""] * 10
        if r[0].strip():
            sq, fl = squash(r[0]), ""
        if r[1].strip():
            fl = squash(r[1])
        if not r[2].strip():
            continue
        uid = re.search(r"user-(\d+)", r[6])
        out.append({"sq": sq, "fl": fl, "name": r[5].strip() or r[2].strip(), "rank": r[4].strip().rstrip("."),
                    "pos": r[8].strip(), "uid": uid.group(1) if uid else None})
    return out


# ---------- roles from the ORBAT ----------
def base_sq(sq):
    return re.sub(r" (Crew |Pilots )?Reserve$", "", sq)


def flight_code(p):
    m = re.match(r"^([ABC]) Flight", p["fl"] or "")
    return "18" + m.group(1) if m else None


def roles_for(rows: list[dict]) -> list[dict]:
    """One person can hold several rows (e.g. JAC 2IC and a pilot in C Flight)."""
    roles = []
    for p in rows:
        reserve = p["sq"] != base_sq(p["sq"])
        sq = base_sq(p["sq"])
        if p["sq"] == "JAC HQ":
            roles.append({"scope": "all", "title": p["pos"] or "JAC HQ"})
        elif reserve or sq.startswith("ELOA"):
            roles.append({"scope": "self", "title": "Reserve"})
        elif sq == "No. 18":
            fc = flight_code(p)
            if p["pos"] == "In Command":
                roles.append({"scope": "sq:No. 18", "title": "No. 18 Squadron OC"})
            if p["rank"] == "MAcr":
                roles.append({"scope": "sq:No. 18", "title": "No. 18 Squadron 2IC"})
            if p["rank"] in ("Flt Lt", "Fg Off") and fc:
                roles.append({"scope": f"fl:{fc}", "title": f"No. 18 {fc[-1]} Flight IC"})
            if p["rank"] == "FSAcr" and fc:
                roles.append({"scope": f"fl:{fc}", "title": f"No. 18 {fc[-1]} Flight 2IC"})
            if not any(r["scope"] != "self" for r in roles):
                roles.append({"scope": "self", "title": "No. 18 aircrew"})
        elif sq == "No. 662":
            if p["rank"] in ("Lt", "2Lt"):
                roles.append({"scope": "sq:No. 662", "title": "No. 662 Squadron IC"})
            elif p["rank"] == "SSgt":
                roles.append({"scope": "sq:No. 662", "title": "No. 662 Squadron 2IC"})
            elif p["rank"] == "Sgt":
                roles.append({"scope": "sq:No. 662", "title": "No. 662 Flight IC"})
            else:
                roles.append({"scope": "self", "title": "No. 662"})
        elif sq == "ALIC":
            if p["rank"] == "Sgt" or p["pos"] == "In Command":
                roles.append({"scope": "sq:ALIC", "title": "ALIC Squadron IC"})
            elif p["rank"] == "Cpl":
                roles.append({"scope": "sq:ALIC", "title": "ALIC Squadron 2IC"})
            else:
                roles.append({"scope": "self", "title": "ALIC"})
    return roles


def can_edit(roles: list[dict], etype: str, key: str) -> bool:
    scopes = {r["scope"] for r in roles}
    if "all" in scopes:
        return True
    command = [s for s in scopes if s != "self"]
    if etype == "staffing":
        unit = key.split("|")[-1]
        return f"fl:{unit}" in scopes or "sq:No. 18" in scopes
    if etype == "setting":
        if key.startswith("cas|"):
            unit = key.split("|")[1]
            return f"fl:{unit}" in scopes or "sq:No. 18" in scopes
        return "sq:No. 18" in scopes
    if etype == "check":
        return bool(command)
    if etype == "roles":
        return "sq:" + SQ_OF_ROLEKEY.get(key, "?") in scopes
    return False  # cycle: JAC HQ only


SQ_OF_ROLEKEY = {"18": "No. 18", "662": "No. 662", "ALIC": "ALIC"}


async def current(request: Request) -> dict | None:
    s = request.session
    if not s.get("google_sub"):
        return None
    me = {"email": s.get("email"), "name": s.get("gname"), "forum_uid": s.get("forum_uid"), "forum_display": s.get("forum_display")}
    if me["forum_uid"]:
        rows = [p for p in await people() if p["uid"] == me["forum_uid"]]
        me["orbat"] = rows
        me["roles"] = roles_for(rows)
        me["member"] = bool(rows)
    else:
        me["roles"], me["member"] = [], False
    return me


async def require_member(request: Request) -> dict:
    me = await current(request)
    if not me or not me["member"]:
        raise HTTPException(401, "Sign in with Google and the forum first")
    return me


# ---------- auth ----------
@app.get("/api/config")
async def config():
    return {"google_client_id": GOOGLE_CLIENT_ID}


@app.post("/auth/google")
async def auth_google(request: Request):
    body = await request.json()
    try:
        info = id_token.verify_oauth2_token(body.get("credential", ""), google_requests.Request(), GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(401, "Google sign-in could not be verified")
    request.session.update({"google_sub": info["sub"], "email": info.get("email"), "gname": info.get("name")})
    with db() as con:
        row = con.execute("select forum_uid, forum_display from links where google_sub=?", (info["sub"],)).fetchone()
    if row:
        request.session.update({"forum_uid": row[0], "forum_display": row[1]})
    return await current(request)


@app.post("/auth/forum/start")
async def forum_start(request: Request):
    """Step 1 of linking: the member says which forum profile is theirs and gets a one-time code."""
    if not request.session.get("google_sub"):
        raise HTTPException(401, "Sign in with Google first")
    uid = str((await request.json()).get("uid", ""))
    if not uid.isdigit() or not any(p["uid"] == uid for p in await people()):
        raise HTTPException(400, "Pick yourself from the JAC ORBAT")
    code = new_code()
    request.session.update({"link_uid": uid, "link_code": code, "link_exp": time.time() + 3600})
    return {"code": code, "uid": uid, "editsig": "https://4thib.co.uk/usercp.php?action=editsig"}


@app.post("/auth/forum/check")
async def forum_check(request: Request):
    """Step 2: the code must now be in that member's public forum signature."""
    s = request.session
    if not s.get("google_sub") or not s.get("link_code") or time.time() > s.get("link_exp", 0):
        raise HTTPException(400, "Start again: the code has expired")
    found, display = await profile_contains(s["link_uid"], s["link_code"])
    if not found:
        raise HTTPException(404, "The code is not in your forum signature yet. Save the signature, then check again")
    with db() as con:
        con.execute("insert or replace into links values(?,?,?,?,?)",
                    (s["google_sub"], s.get("email"), s["link_uid"], display, datetime.now(timezone.utc).isoformat()))
    s.update({"forum_uid": s["link_uid"], "forum_display": display})
    for k in ("link_uid", "link_code", "link_exp"):
        s.pop(k, None)
    return await current(request)


if os.environ.get("DEV_LOGIN") == "1":
    @app.get("/auth/dev")
    async def dev_login(request: Request, uid: str):
        """Local testing only: act as the forum user `uid`. Never set DEV_LOGIN on the server."""
        request.session.update({"google_sub": "dev-" + uid, "email": "dev@localhost", "gname": "Dev", "forum_uid": uid, "forum_display": ""})
        return await current(request)


@app.get("/api/forum/status")
async def forum_status(request: Request):
    """The forum parts (attendance tracker, LOAs, patrol reports) need a read-only forum account on the server."""
    await require_member(request)
    return {"configured": bool(os.environ.get("FORUM_USER") and os.environ.get("FORUM_PASSWORD"))}


@app.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request):
    return await current(request) or JSONResponse({"signed_in": False}, status_code=401)


# ---------- data ----------
@app.get("/api/sheet/{name}")
async def sheet(name: str, request: Request):
    if name not in SHEETS:
        raise HTTPException(404)
    if name not in PUBLIC_SHEETS:
        await require_member(request)
    return PlainTextResponse(await sheet_csv(name), media_type="text/csv", headers={"Cache-Control": "no-store"})


@app.get("/api/entries")
async def entries(request: Request):
    await require_member(request)
    with db() as con:
        rows = con.execute("select ts, type, key, payload from entries order by id").fetchall()
    return [{"ts": r[0], "type": r[1], "key": r[2], "payload": json.loads(r[3])} for r in rows]


@app.post("/api/entries")
async def add_entry(request: Request):
    me = await require_member(request)
    body = await request.json()
    etype, key, payload = body.get("type"), str(body.get("key", ""))[:100], body.get("payload")
    if etype not in ENTRY_TYPES or not key:
        raise HTTPException(400, "Unknown entry")
    if not can_edit(me["roles"], etype, key):
        raise HTTPException(403, "Your post does not allow this change")
    text = json.dumps(payload)
    if len(text) > 20000:
        raise HTTPException(413, "Entry too large")
    ts = datetime.now(timezone.utc).isoformat()
    with db() as con:
        con.execute("insert into entries(ts, type, key, payload, author_uid) values(?,?,?,?,?)", (ts, etype, key, text, me["forum_uid"]))
    return {"ts": ts}


@app.get("/")
async def index():
    return FileResponse(ROOT / "index.html", headers={"Cache-Control": "no-cache"})
