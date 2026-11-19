#!/usr/bin/env python3
"""Read the JAC Google Sheets and write the cockpit's data files.

All sheets are shared by link, so their CSV export can be read without a login.
Writes data/orbat.json and data/sheets.json. Standard library only.

    python3 scripts/fetch_sheets.py
"""
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SHEETS = {
    # ORBAT and Course Tracker - JAC, tab "Input": one row per member, all courses
    "orbat": ("1ALQxRZgGtflI0tm2lSOu5JJpt8fazxEu-Of3Q0TRANk", "1323797389"),
    # Unit Attendance, tab JAC: per flight / night grid that the 2ICs fill in
    "ua": ("13GOwG_tfkFuXcJt1tMu4f8RNaGRAvTpKhBbYcAqGZzA", "290771582"),
    # Unit roster "ORBAT 2.0": Unit Attendance takes its names and ranks from here
    "roster": ("1GRENwxiY7DC5fLbue12XAeLsa_wsnKCOy3vvGzcY_Ok", "1766701879"),
    # Logistics, tab "Requested Logistics"
    "logi": ("17yeIDGcKKAs13syNLe6sg5K-bp4pAMTe-urv2u-vutk", "0"),
}


def fetch(key):
    sheet_id, gid = SHEETS[key]
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8"))))


def cell(rows, i, j):
    try:
        return rows[i][j].strip()
    except IndexError:
        return ""


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


# ---------- ORBAT and course tracker ----------
def parse_orbat(rows):
    header = [squash(h) for h in rows[1]]
    courses = header[9:]
    people, sq, fl = [], "", ""
    for r in rows[3:]:
        if cell([r], 0, 0):
            sq, fl = squash(r[0]), ""
        if cell([r], 0, 1):
            fl = squash(r[1])
        if not cell([r], 0, 2):
            continue
        uid = re.search(r"user-(\d+)", cell([r], 0, 6))
        done = [c for c, v in zip(courses, r[9:]) if v == "Complete" and c != "Wings Achieved"]
        wings = cell([r], 0, 9 + courses.index("Wings Achieved")) if "Wings Achieved" in courses else ""
        people.append({
            "sq": sq, "fl": fl,
            "name": cell([r], 0, 5) or cell([r], 0, 2),
            "rank": cell([r], 0, 4).rstrip("."),
            "pos": cell([r], 0, 8),
            "uid": uid.group(1) if uid else None,
            "done": done,
            "wings": wings if re.match(r"\d", wings) else None,
        })
    return {"courses": [c for c in courses if c != "Wings Achieved"], "people": people}


# ---------- Unit Attendance, JAC tab ----------
# Each block has three groups side by side (columns 1, 9, 17): name column, then up to five date columns.
UA_BLOCKS = {
    "No.18 Sqn": ["18A", "18B", "18C"],
    "No.662 Sqn": ["662-Sat", "662-Sun", "662-Wed"],
    "ALIC Sqn": ["ALIC-Sat", "ALIC-Sun", "ALIC-Wed"],
}


def parse_ua(rows, today):
    year = today[:4]
    sections, future = {}, []
    for hr, row in enumerate(rows):
        first = cell(rows, hr, 1)
        keys = next((v for k, v in UA_BLOCKS.items() if first.startswith(k)), None)
        if not keys:
            continue
        for g, key in zip([1, 9, 17], keys):
            dates = []
            for c in range(g + 1, g + 6):
                m = re.match(r"(\d\d)/(\d\d)", cell(rows, hr, c))
                dates.append(f"{year}-{m.group(2)}-{m.group(1)}" if m else None)
            cols = {d: 0 for d in dates if d}
            members, r = 0, hr + 1
            while r < len(rows) and cell(rows, r, g) != "Total present":
                name = cell(rows, r, g)
                if name:
                    members += 1
                    for k, d in enumerate(dates):
                        v = cell(rows, r, g + 1 + k)
                        if d and v:
                            cols[d] += 1
                            if d > today:
                                future.append({"who": name, "sec": key, "date": d, "value": v})
                r += 1
            sections[key] = {"members": members, "cols": cols}
    hq = {f"Week {k + 1}": [cell(rows, 2, 10 + k), cell(rows, 3, 10 + k)] for k in range(5)}
    return {"sections": sections, "future": future, "hq": hq}


# ---------- Unit roster, ORBAT 2.0 (JAC blocks) ----------
def split_rank(raw):
    m = re.match(r"^(.*?)\.?\s+([A-Z]\.\s.*)$", raw)
    return (m.group(1).strip().rstrip("."), squash(m.group(2))) if m else ("", raw)


def parse_roster(rows):
    out = []

    def find(label):
        for i, r in enumerate(rows):
            for j, c in enumerate(r):
                if c.strip().startswith(label):
                    return i, j
        raise SystemExit(f"Roster block not found: {label}")

    def block(label, unit, n=6):
        i, j = find(label)
        for r in range(i + 1, i + 1 + n):
            raw = cell(rows, r, j + 1)
            if raw and raw != "CAPPED":
                rank, name = split_rank(raw)
                out.append({"unit": unit, "slot": cell(rows, r, j), "rank": rank, "name": name})

    block("No. 18 A Flight", "18A")
    block("No. 18 B Flight", "18B")
    block("No. 18 C Flight", "18C")
    block("No. 662", "662")
    block("Air Land Integration Cell", "ALIC")
    i, j = find("JAC HQ")
    for r in range(i + 1, i + 3):
        raw = cell(rows, r, j + 1)
        if raw:
            rank, name = split_rank(raw)
            out.append({"unit": "HQ", "slot": cell(rows, r, j), "rank": rank, "name": name})
    return out


# ---------- Requested Logistics ----------
def to_iso(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s.strip())
    if not m:
        return None
    y = m.group(3)
    y = "20" + y if len(y) == 2 else y
    return f"{y}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"


def parse_logi(rows):
    out = []
    for r in rows[2:]:
        if not r or not r[0].strip() or not any(x.strip() for x in r[1:]):
            continue
        g = lambda k: cell([r], 0, k)
        out.append({"ref": g(0), "rec": to_iso(g(1)), "req": g(2), "ship": g(3), "from": g(6), "to": g(7),
                    "type": g(8), "eta": to_iso(g(9)), "coy": g(10), "link": g(11), "flight": g(12),
                    "status": g(13), "notes": g(14)})
    return out


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA.mkdir(exist_ok=True)
    orbat = parse_orbat(fetch("orbat"))
    sheets = {"ua": parse_ua(fetch("ua"), today), "roster": parse_roster(fetch("roster")), "logi": parse_logi(fetch("logi")),
              "read": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    for name, obj in [("orbat.json", orbat), ("sheets.json", sheets)]:
        text = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        if "</" in text:
            sys.exit(f"{name}: data contains '</', refusing to inline it into a page")
        (DATA / name).write_text(text, encoding="utf-8")
    print(f"{len(orbat['people'])} members, {len(sheets['ua']['sections'])} attendance sections, "
          f"{len(sheets['roster'])} roster slots, {len(sheets['logi'])} logistics orders")


if __name__ == "__main__":
    main()
