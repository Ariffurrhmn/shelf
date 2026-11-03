#!/usr/bin/env python3
"""Build the Shelf gallery into site/.

Minimal v0: no validation and no thumbnails yet (both planned). It reads the
`shelf-meta` JSON block of each artifacts/<slug>/index.html, skips drafts,
copies each artifact folder into site/<slug>/, and writes site/index.html.
Standard library only.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
SITE = ROOT / "site"
META_RE = re.compile(
    r'<script[^>]*id=["\']shelf-meta["\'][^>]*>(.*?)</script>', re.S | re.I
)
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REQUIRED = ("title", "description", "created", "tool", "kind")


def read_meta(index: Path) -> dict:
    match = META_RE.search(index.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("no shelf-meta block")
    meta = json.loads(match.group(1))
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    return meta


def collect() -> list[dict]:
    items, errors = [], []
    if ARTIFACTS.is_dir():
        for folder in sorted(p for p in ARTIFACTS.iterdir() if p.is_dir()):
            index = folder / "index.html"
            if not index.is_file():
                continue
            try:
                if not SLUG_RE.match(folder.name):
                    raise ValueError("slug must be lowercase letters, digits, hyphens")
                meta = read_meta(index)
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{folder.name}: {exc}")
                continue
            if meta.get("draft"):
                continue
            items.append({"slug": folder.name, "dir": folder, **meta})
    if errors:
        sys.exit("Build failed:\n  " + "\n  ".join(errors))
    return sorted(items, key=lambda i: i["created"], reverse=True)


def card(item: dict) -> str:
    e = html.escape
    tags = "".join(f"<span>{e(t)}</span>" for t in item.get("tags", []))
    return (
        f'<a class="card" href="{e(item["slug"])}/">'
        f'<span class="kind">{e(item["kind"])}</span>'
        f'<h2>{e(item["title"])}</h2><p>{e(item["description"])}</p>'
        f'<div class="meta">{e(item["created"])} · {e(item["tool"])}</div>'
        f'<div class="tags">{tags}</div></a>'
    )


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shelf</title>
<meta name="description" content="A personal shelf for small HTML apps, tools, and presentations.">
<style>
:root{--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--card:#fff;--line:#e7e5e4;--accent:#c2410c}
@media (prefers-color-scheme:dark){:root{--bg:#161412;--fg:#f5f5f4;--muted:#a8a29e;--card:#1f1c1a;--line:#33302d;--accent:#fb923c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:960px;margin:0 auto;padding:48px 16px}
h1{font-size:2.2rem;margin:0 0 4px}
.lead{color:var(--muted);margin:0 0 32px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;color:inherit;text-decoration:none}
.card:hover,.card:focus-visible{border-color:var(--accent)}
.card h2{font-size:1.1rem;margin:6px 0}
.card p{margin:0 0 12px;color:var(--muted);font-size:.95rem}
.kind{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);font-weight:600}
.meta{font-size:.8rem;color:var(--muted)}
.tags span{display:inline-block;margin:8px 6px 0 0;padding:1px 8px;border:1px solid var(--line);border-radius:999px;font-size:.75rem;color:var(--muted)}
.empty{border:1px dashed var(--line);border-radius:12px;padding:32px;text-align:center;color:var(--muted)}
footer{margin-top:40px;font-size:.85rem;color:var(--muted)}
footer a{color:inherit}
</style>
</head>
<body>
<main>
<h1>📚 Shelf</h1>
<p class="lead">A personal shelf for small HTML apps, tools, and presentations.</p>
{body}
<footer><a href="https://github.com/ariffurrhmn/shelf">Source on GitHub</a></footer>
</main>
</body>
</html>
"""


def main() -> None:
    items = collect()
    if SITE.exists():
        for child in SITE.iterdir():
            if child.name == ".gitkeep":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    SITE.mkdir(exist_ok=True)
    for item in items:
        shutil.copytree(item["dir"], SITE / item["slug"])
    if items:
        body = '<div class="grid">' + "".join(card(i) for i in items) + "</div>"
    else:
        body = '<div class="empty">Nothing on the shelf yet. Artifacts will appear here.</div>'
    (SITE / "index.html").write_text(PAGE.replace("{body}", body), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {len(items)} artifact(s) into {SITE.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
