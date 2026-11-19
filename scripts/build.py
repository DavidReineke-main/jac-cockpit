#!/usr/bin/env python3
"""Inline data/*.json into src/cockpit.html and write dist/jac-cockpit.html.

    python3 scripts/fetch_sheets.py && python3 scripts/build.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    page = (ROOT / "src" / "cockpit.html").read_text(encoding="utf-8")
    for marker, name in [("__ORBAT_DATA__", "orbat.json"), ("__SHEETS_DATA__", "sheets.json")]:
        path = ROOT / "data" / name
        if not path.exists():
            raise SystemExit(f"Missing {path}. Run scripts/fetch_sheets.py first")
        if page.count(marker) != 1:
            raise SystemExit(f"Template must contain {marker} exactly once")
        page = page.replace(marker, path.read_text(encoding="utf-8"))
    out = ROOT / "dist" / "jac-cockpit.html"
    out.parent.mkdir(exist_ok=True)
    # The Artifact host adds charset and viewport; a standalone file needs them itself.
    if not page.lstrip().lower().startswith("<!doctype"):
        page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                "</head><body>" + page + "</body></html>")
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
