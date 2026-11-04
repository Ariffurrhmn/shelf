#!/usr/bin/env python3
"""Build the Shelf site.

Pipeline:
  1. validate every artifact (fails the build on errors)
  2. build the gallery UI (gallery/, Vite) into the output directory
  3. copy published (non-draft) artifacts into <out>/artifacts/<slug>/, add a
     Content-Security-Policy that enforces each artifact's declared network
     (harden.py), and add PWA files to those with "install": true
  4. generate thumbnails (best effort, Playwright, cached by content hash)
  5. write a redirect page per short link, with Open Graph tags, plus a redirect
     for every alias (old slug) so renamed artifacts keep their links
  6. write <out>/artifacts.json, robots.txt, sitemap.xml, .nojekyll and an optional CNAME

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
import harden  # noqa: E402
import pwa  # noqa: E402
import seo  # noqa: E402

DEFAULT_REPO_URL = "https://github.com/ariffurrhmn/shelf"
THUMB_CACHE = Path(os.environ.get("SHELF_CACHE_DIR") or REPO / ".shelf-cache") / "thumbnails"


def make_entry(slug: str, meta: dict, thumb: dict | None, short: str | None = None) -> dict:
    """Normalise validated metadata into one manifest entry.

    `thumb` is {"src", "small", "width", "height"} from the thumbnail step, or None.
    Optional metadata is carried over only when present, so the gallery can
    tell "not set" from "set to the default"."""
    install = meta.get("install") is True
    entry = {
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
        "why": meta.get("why"),
        "status": meta.get("status"),
        "featured": meta.get("featured") is True,
        "updated": meta.get("updated"),
        "source": meta.get("source"),
        "aliases": list(meta.get("aliases", [])),
        "url": f"artifacts/{slug}/",
        "short": short,
        "thumbnail": thumb["src"] if thumb else None,
        "thumbnailSmall": thumb["small"] if thumb else None,
        "thumbnailWidth": thumb["width"] if thumb else None,
        "thumbnailHeight": thumb["height"] if thumb else None,
        "install": install,
        "icon": f"artifacts/{slug}/icon-192.png" if install else None,
        "color": (meta.get("color") or pwa.default_color(slug)) if install else None,
    }
    return entry


def build_manifest(
    results: list[sv.Result],
    thumbs: dict[str, dict] | None,
    repo_url: str | None,
    shorts: dict[str, str] | None = None,
) -> dict:
    thumbs = thumbs or {}
    shorts = shorts or {}
    entries = [
        make_entry(r.slug, r.metadata, thumbs.get(r.slug), shorts.get(r.slug))
        for r in results
        if r.ok and not r.draft and r.metadata
    ]
    entries.sort(key=lambda e: (e["created"], e["title"].lower()), reverse=True)
    manifest = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "artifacts": entries}
    if repo_url:
        manifest["repo"] = repo_url
    return manifest


def share_markup(r: sv.Result, entry: dict, base: str) -> str:
    """Open Graph tags for one artifact's short-link page."""
    image = entry["thumbnail"] or seo.SITE_IMAGE
    code = entry["short"] or entry["slug"]
    return seo.share_tags(
        title=entry["title"],
        description=entry["description"],
        url=seo.absolute(base, code + "/"),
        image=seo.absolute(base, image),
    )


def thumbnail_jobs(published: list[sv.Result]) -> dict:
    hosts = list(sv.ALLOWED_CDN_HOSTS) + list(sv.ALLOWED_FONT_HOSTS)
    return {
        "cache": str(THUMB_CACHE),
        "items": [
            {
                "slug": r.slug,
                "override": (r.metadata or {}).get("thumbnail"),
                "allowHosts": hosts + list((r.metadata or {}).get("network", [])),
            }
            for r in published
        ],
    }


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
    collisions = sv.crosscheck(results)
    for problem in collisions:
        print(f"error: {problem}", file=sys.stderr)
    if collisions or any(not r.ok for r in results) or (args.strict and any(r.warnings for r in results)):
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
    for r in published:
        harden.harden_artifact(dest_root / r.slug, r.metadata)
    print(f"Added a Content-Security-Policy to {len(published)} artifact(s)")
    installable = [r for r in published if r.metadata and r.metadata.get("install") is True]
    for r in installable:
        try:
            pwa.make_installable(dest_root / r.slug, r.slug, r.metadata)
        except pwa.PwaError as exc:
            print(f"\nBuild stopped: {r.slug} cannot be made installable: {exc}", file=sys.stderr)
            return 1
    if installable:
        print(f"Made {len(installable)} artifact(s) installable: {', '.join(r.slug for r in installable)}")

    # 4. thumbnails
    thumbs: dict[str, dict] = {}
    if published and not args.no_thumbnails and shutil.which("node"):
        build_tools = REPO / "tools" / "build"
        if args.install and not (build_tools / "node_modules").exists():
            run(["npm", "ci"], build_tools)
        jobs_file = out / ".thumbnail-jobs.json"
        jobs_file.write_text(json.dumps(thumbnail_jobs(published)), encoding="utf-8")
        try:
            rc = run(["node", "thumbnails.cjs", str(out), str(jobs_file)], build_tools, check=False)
        finally:
            jobs_file.unlink(missing_ok=True)
        index = out / "thumbnails" / "index.json"
        if rc != 0:
            print("warning: thumbnails were skipped; the gallery will show placeholders.", file=sys.stderr)
        if index.is_file():
            thumbs = json.loads(index.read_text(encoding="utf-8"))
            index.unlink()

    # 5. manifest, short links and aliases (after the gallery build, which empties the output folder)
    base = shortlinks.base_url()
    site_base = base or shortlinks.DEFAULT_BASE_URL
    gh = os.environ.get("GITHUB_REPOSITORY")
    repo_url = f"https://github.com/{gh}" if gh else DEFAULT_REPO_URL
    manifest = build_manifest(published, thumbs, repo_url, plan.artifacts)
    entries = {e["slug"]: e for e in manifest["artifacts"]}
    share = {r.slug: share_markup(r, entries[r.slug], site_base) for r in published if r.slug in entries}
    try:
        count = shortlinks.write_redirects(out, plan, share)
        alias_map = {alias: e["slug"] for e in manifest["artifacts"] for alias in e["aliases"]}
        n_alias = shortlinks.write_alias_redirects(out, alias_map)
    except shortlinks.ShortLinkError as exc:
        print("\n".join(f"error: {p}" for p in exc.problems), file=sys.stderr)
        return 1
    rows = shortlinks.describe(plan, {r.slug: r.metadata["title"] for r in published}, base)
    print(f"\nWrote {count} short link(s) and {n_alias} alias redirect(s):\n{shortlinks.format_table(rows)}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and rows:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(shortlinks.format_markdown(rows))

    # 6. hosting and SEO files
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (out / "artifacts.json").write_text(text, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "robots.txt").write_text(seo.robots_txt(site_base), encoding="utf-8")
    (out / "sitemap.xml").write_text(seo.sitemap_xml(site_base, manifest["artifacts"]), encoding="utf-8")
    for name in ("index.html", "404.html"):
        page = out / name
        if page.is_file():
            text = seo.inject_site_urls(page.read_text(encoding="utf-8"), site_base)
            if name == "index.html":
                text = seo.inject_gallery_csp(text)
            page.write_text(text, encoding="utf-8")
    if os.environ.get("SHELF_CNAME"):
        (out / "CNAME").write_text(os.environ["SHELF_CNAME"].strip() + "\n", encoding="utf-8")
    if (gallery / "public").is_dir():  # lets `npm run dev` show real data
        (gallery / "public" / "artifacts.json").write_text(text, encoding="utf-8")

    print(f"\nBuilt {len(manifest['artifacts'])} artifact(s) into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
