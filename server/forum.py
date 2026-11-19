"""Link a Google account to a forum profile without the forum password.

The member picks themselves from the ORBAT, puts a short one-time code into their forum signature
(on the forum, where they are already logged in), and we read their public profile page to find it.
Profiles on 4thib.co.uk are visible without logging in.
"""
from __future__ import annotations

import html
import re
import secrets

import httpx

FORUM = "https://4thib.co.uk"
UA = "JAC-Cockpit/1.0 (profile check)"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code() -> str:
    return "JAC-" + "".join(secrets.choice(ALPHABET) for _ in range(5))


async def profile_contains(uid: str, code: str) -> tuple[bool, str]:
    """Return (found, display name) for the public profile of forum user `uid`."""
    if not uid.isdigit():
        return False, ""
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=20, follow_redirects=True) as c:
        r = await c.get(f"{FORUM}/member.php", params={"action": "profile", "uid": uid}, headers={"Cache-Control": "no-cache"})
    if r.status_code != 200:
        return False, ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", r.text))
    title = re.search(r"<title>[^<]*?Profile of ([^<]+)</title>", r.text)
    return code in text, (title.group(1).strip() if title else "")
