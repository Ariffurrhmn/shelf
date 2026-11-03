#!/usr/bin/env python3
"""Build the Shelf site.

Pipeline:
  1. validate every artifact (fails the build on errors)
  2. build the gallery UI (gallery/, Vite) into the output directory
  3. copy published (non-draft) artifacts into <out>/artifacts/<slug>/
  4. generate thumbnails (best effort, Playwright)
  5. write a redirect page per short link (see shortlinks.py)
  6. write <out>/artifacts.json, .nojekyll and an optional CNAME

Usage:
    python tools/build/build.py
    python tools/build/build.py --no-thumbnails
    python tools/build/build.py --skip-gallery --out /tmp/site   # data only
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "validate"))
import shelf_validate as sv  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shortlinks  # noqa: E402

DEFAULT_REPO_URL = "https://github.com/ariffurrhmn/shelf"


def make_entry(slug: str, meta: dict, has_thumbnail: bool, short: str | None = None) -> dict:
    """Normalise validated metadata into one manifest entry."""
    return {
        "slug": slug,
        "title": meta["title"],
        "description": meta["description"],
        "created": meta["created"],
        "tool": meta["tool"],
        "kind": meta["kind"],
        "tags": list(meta.get("tags", [])),
        "storage": meta.get("storage", "none"),
        "network": list(meta.get("network", [])),
        "notes": meta.get("notes"),
        "url": f"artifacts/{slug}/",
        "short": short,
        "thumbnail": f"thumbnails/{slug}.jpg" if has_thumbnail else None,
    }


def build_manifest(
    results: list[sv.Result], thumbs: set[str], repo_url: str | None, shorts: dict[str, str] | None = None
) -> dict:
    shorts = shorts or {}
    entries = [
        make_entry(r.slug, r.metadata, r.slug in thumbs, shorts.get(r.slug))
        for r in results
        if r.ok and not r.draft and r.metadata
    ]
    entries.sort(key=lambda e: (e["created"], e["title"].lower()), reverse=True)
    manifest = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "artifacts": entries}
    if repo_url:
        manifest["repo"] = repo_url
    return manifest


def run(cmd: list[str], cwd: Path, check: bool = True) -> int:
    print(f"$ {' '.join(cmd)}  (in {cwd.relative_to(REPO) if cwd != REPO else '.'})", flush=True)
    return subprocess.run(cmd, cwd=cwd, check=check).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--artifacts-dir", type=Path, default=REPO / "artifacts")
    ap.add_argument("--out", type=Path, default=REPO / "site")
    ap.add_argument("--links", type=Path, default=shortlinks.LINKS_FILE, help="extra short links (default: links.json)")
    ap.add_argument("--skip-gallery", action="store_true", help="do not run the Vite build (writes data only)")
    ap.add_argument("--no-thumbnails", action="store_true")
    ap.add_argument("--install", action="store_true", help="run npm ci before building (CI uses this)")
    ap.add_argument("--strict", action="store_true", help="treat validator warnings as errors")
    args = ap.parse_args(argv)

    out: Path = args.out.resolve()
    gallery = REPO / "gallery"

    # 1. validate
    results = sv.validate_all(args.artifacts_dir)
    print(sv._format(results, color=sys.stdout.isatty()))
    if any(not r.ok for r in results) or (args.strict and any(r.warnings for r in results)):
        print("\nBuild stopped: fix the validation errors above.", file=sys.stderr)
        return 1
    published = [r for r in results if not r.draft]
    skipped = [r.slug for r in results if r.draft]
    if skipped:
        print(f"Skipping drafts: {', '.join(skipped)}")

    # Short codes are planned before the slow steps so a collision fails fast.
    try:
        plan = shortlinks.plan_links([(r.slug, r.metadata) for r in published], shortlinks.load_links(args.links))
    except shortlinks.ShortLinkError as exc:
        print("\n".join(f"error: {p}" for p in exc.problems), file=sys.stderr)
        print("\nBuild stopped: fix the short link problems above.", file=sys.stderr)
        return 1

    # 2. gallery UI
    if not args.skip_gallery:
        if args.install or not (gallery / "node_modules").exists():
            run(["npm", "ci"], gallery)
        run(["npm", "run", "build"], gallery)  # vite writes ../site and empties it
        if out != (REPO / "site").resolve():
            if out.exists():
                shutil.rmtree(out)
            shutil.copytree(REPO / "site", out)
    else:
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

    # 3. artifacts
    dest_root = out / "artifacts"
    if dest_root.exists():
        shutil.rmtree(dest_root)
    for r in published:
        shutil.copytree(r.path, dest_root / r.slug, ignore=shutil.ignore_patterns(".*", "__pycache__"))
    print(f"Copied {len(published)} artifact(s) to {dest_root}")

    # 4. thumbnails
    thumbs: set[str] = set()
    if published and not args.no_thumbnails and shutil.which("node"):
        slugs = [r.slug for r in published]
        build_tools = REPO / "tools" / "build"
        if args.install and not (build_tools / "node_modules").exists():
            run(["npm", "ci"], build_tools)
        rc = run(["node", "thumbnails.cjs", str(out), *slugs], build_tools, check=False)
        if rc != 0:
            print("warning: thumbnails were skipped; the gallery will show placeholders.", file=sys.stderr)
        thumbs = {p.stem for p in (out / "thumbnails").glob("*.jpg")} if (out / "thumbnails").is_dir() else set()

    # 5. short links (after the gallery build, which empties the output folder)
    try:
        count = shortlinks.write_redirects(out, plan)
    except shortlinks.ShortLinkError as exc:
        print("\n".join(f"error: {p}" for p in exc.problems), file=sys.stderr)
        return 1
    rows = shortlinks.describe(plan, {r.slug: r.metadata["title"] for r in published}, shortlinks.base_url())
    print(f"\nWrote {count} short link(s):\n{shortlinks.format_table(rows)}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and rows:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(shortlinks.format_markdown(rows))

    # 6. manifest and hosting files
    gh = os.environ.get("GITHUB_REPOSITORY")
    repo_url = f"https://github.com/{gh}" if gh else DEFAULT_REPO_URL
    manifest = build_manifest(published, thumbs, repo_url, plan.artifacts)
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (out / "artifacts.json").write_text(text, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    if os.environ.get("SHELF_CNAME"):
        (out / "CNAME").write_text(os.environ["SHELF_CNAME"].strip() + "\n", encoding="utf-8")
    if (gallery / "public").is_dir():  # lets `npm run dev` show real data
        (gallery / "public" / "artifacts.json").write_text(text, encoding="utf-8")

    print(f"\nBuilt {len(manifest['artifacts'])} artifact(s) into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
