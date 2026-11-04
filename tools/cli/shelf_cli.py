#!/usr/bin/env python3
"""shelf: add, check and preview artifacts. Standard library only (Python 3.9+).

    shelf add my-app.html            import a generated HTML file as a new artifact
    shelf validate [slug ...]        check artifacts against spec/SPEC.md
    shelf list                       show the collection
    shelf preview [slug]             build the site and serve it locally (--raw: no build)
    shelf rename OLD NEW             rename an artifact without breaking its links
    shelf links [--compare REF]      show short links; check none disappeared since REF
    shelf doctor                     check the local setup
    shelf prompt                     print the instructions to give an AI assistant

Nothing here pushes to GitHub or deploys. Publishing is a git push you do yourself.
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import unicodedata
import webbrowser
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "validate"))
sys.path.insert(0, str(REPO / "tools" / "build"))
import shelf_validate as sv  # noqa: E402
import shortlinks  # noqa: E402

ARTIFACTS = REPO / "artifacts"
MAX_SOURCE_BYTES = 5_000_000
KNOWN_TOOLS = {
    "claude": "Claude", "chatgpt": "ChatGPT", "gpt": "ChatGPT", "gemini": "Gemini", "copilot": "Copilot",
    "cursor": "Cursor", "v0": "v0", "human": "Handwritten", "manual": "Handwritten",
}
META_BLOCK_RE = re.compile(
    r'(<script\b[^>]*\bid\s*=\s*["\']shelf-meta["\'][^>]*>)(.*?)(</script\s*>)', re.I | re.S
)


class ShelfError(Exception):
    """A problem the user can fix; printed without a traceback."""


# --------------------------------------------------------------------------
# helpers (pure, unit-tested)
# --------------------------------------------------------------------------


def slugify(text: str, max_len: int = 48) -> str:
    """'Focus Timer!' -> 'focus-timer'. Always matches the slug rules or returns ''."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:max_len].strip("-")
    return text if sv.SLUG_RE.match(text or "-") else ""


def unique_slug(base: str, taken: set[str]) -> str:
    """`base`, or `base-2`, `base-3`... the first one not in `taken`."""
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def normalize_tool(tool: str) -> str:
    return KNOWN_TOOLS.get(tool.strip().lower(), tool.strip())


def split_list(value: str | None) -> list[str]:
    return [p.strip() for p in (value or "").split(",") if p.strip()]


def safe_child(parent: Path, name: str) -> Path:
    """`parent/name`, refusing anything that would land outside `parent`."""
    target = (parent / name).resolve()
    try:
        target.relative_to(parent.resolve())
    except ValueError:
        raise ShelfError(f"{name!r} would be written outside {parent}.") from None
    if target == parent.resolve():
        raise ShelfError("Empty artifact name.")
    return target


class _Info(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1 = ""
        self.description = ""
        self._in: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("name") or "").lower() == "description":
            self.description = (a.get("content") or "").strip()
        elif tag in ("title", "h1") and not getattr(self, tag):
            self._in = tag

    def handle_endtag(self, tag):
        if tag == self._in:
            self._in = None

    def handle_data(self, data):
        if self._in:
            setattr(self, self._in, getattr(self, self._in) + data)


def page_info(html: str) -> dict:
    """Title, description and any existing shelf-meta block of an HTML file."""
    p = _Info()
    try:
        p.feed(html)
        p.close()
    except Exception:  # noqa: BLE001 - lenient on purpose; the validator reports real problems
        pass
    existing: dict = {}
    if m := META_BLOCK_RE.search(html):
        try:
            data = json.loads(m.group(2))
            if isinstance(data, dict):
                existing = data
        except json.JSONDecodeError:
            pass
    return {
        "title": " ".join((p.title or p.h1).split()),
        "description": " ".join(p.description.split()),
        "meta": existing,
    }


def meta_json(meta: dict) -> str:
    """Readable JSON that cannot close its own <script> tag."""
    return json.dumps(meta, indent=2, ensure_ascii=False).replace("<", "\\u003c")


def upsert_meta_block(html: str, meta: dict) -> str:
    """Replace the shelf-meta block, or add one at the end of <head>."""
    block_body = "\n" + meta_json(meta) + "\n"
    if META_BLOCK_RE.search(html):
        return META_BLOCK_RE.sub(lambda m: m.group(1) + block_body + m.group(3), html, count=1)
    tag = f'<script type="application/json" id="shelf-meta">{block_body}</script>\n'
    import pwa  # noqa: PLC0415 - shared head parser

    offset = pwa.head_end_offset(html)
    if offset is None:
        raise ShelfError("The file has no <head> section to put the metadata in. Add <head></head> first, or ask the AI to include one.")
    return html[:offset] + tag + html[offset:]


def fix_basics(html: str) -> str:
    """Add the two things AI output most often forgets: lang and viewport."""
    if not re.search(r"<html\b[^>]*\blang\s*=", html, re.I):
        html = re.sub(r"<html\b", '<html lang="en"', html, count=1, flags=re.I)
    if not re.search(r'<meta\b[^>]*name\s*=\s*["\']viewport["\']', html, re.I):
        html = re.sub(
            r"(<head\b[^>]*>)",
            r'\1\n<meta name="viewport" content="width=device-width, initial-scale=1">',
            html, count=1, flags=re.I,
        )
    return html


def detect_behaviour(html: str) -> dict:
    """What the page appears to use, so the author can declare it honestly."""
    storage = [label for pat, label in sv.STORAGE_PATTERNS if pat.search(html) and label != "service workers"]
    network = [label for pat, label in sv.NETWORK_PATTERNS if pat.search(html)]
    return {"storage": storage, "network": network}


# --------------------------------------------------------------------------
# prompting
# --------------------------------------------------------------------------


class Prompter:
    def __init__(self, interactive: bool) -> None:
        self.interactive = interactive

    def ask(self, question: str, default: str | None = None) -> str | None:
        if not self.interactive:
            return default
        suffix = f" [{default}]" if default else ""
        try:
            answer = input(f"{question}{suffix}: ").strip()
        except EOFError:
            answer = ""
        return answer or default

    def confirm(self, question: str, default: bool = True) -> bool:
        if not self.interactive:
            return False  # never decide for the author when nobody is there to ask
        hint = "Y/n" if default else "y/N"
        try:
            answer = input(f"{question} [{hint}]: ").strip().lower()
        except EOFError:
            answer = ""
        return default if not answer else answer.startswith("y")


# --------------------------------------------------------------------------
# add
# --------------------------------------------------------------------------


def _read_source(src: Path) -> tuple[Path, str]:
    """Return (kind-specific root, html) for a file or a folder that has index.html."""
    if not src.exists():
        raise ShelfError(f"{src} does not exist.")
    entry = src / "index.html" if src.is_dir() else src
    if src.is_dir() and not entry.is_file():
        raise ShelfError(f"{src} is a folder, but it has no index.html.")
    if entry.suffix.lower() not in (".html", ".htm"):
        raise ShelfError(f"{entry.name} is not an HTML file (.html or .htm).")
    if entry.stat().st_size > MAX_SOURCE_BYTES:
        raise ShelfError(f"{entry.name} is larger than {MAX_SOURCE_BYTES // 1_000_000} MB; Shelf artifacts are meant to be small.")
    try:
        html = entry.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ShelfError(f"{entry.name} is not UTF-8 text. Save it as UTF-8 and try again.") from None
    if not re.search(r"<\s*(html|head|body|!doctype)", html, re.I):
        raise ShelfError(f"{entry.name} does not look like an HTML document (no <html>, <head> or <body>).")
    return src, html


def _copy_tree(src: Path, dest: Path) -> None:
    """Copy an artifact folder, skipping dotfiles and refusing symlinks that leave it."""
    root = src.resolve()
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if p.is_symlink():
            try:
                p.resolve().relative_to(root)
            except ValueError:
                raise ShelfError(f"{rel} is a symbolic link that points outside the folder.") from None
        target = dest / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def existing_slugs(artifacts: Path) -> set[str]:
    """Every address under artifacts/<name>/ that is taken: folders and aliases."""
    taken: set[str] = set()
    for r in sv.validate_all(artifacts):
        taken.add(r.slug)
        aliases = (r.metadata or {}).get("aliases")
        if isinstance(aliases, list):
            taken.update(a for a in aliases if isinstance(a, str))
    return taken


def cmd_add(args: argparse.Namespace) -> int:
    artifacts = Path(args.artifacts_dir)
    p = Prompter(interactive=sys.stdin.isatty() and not args.yes)
    src, html = _read_source(Path(args.source))
    info = page_info(html)
    taken = existing_slugs(artifacts)

    # --- metadata: flags beat the file's own block beats what we can infer
    base = dict(info["meta"])
    title = args.title or base.get("title") or p.ask("Title", info["title"] or Path(args.source).stem.replace("-", " ").replace("_", " ").title())
    if not title:
        raise ShelfError("A title is required. Pass --title.")
    explicit_slug = args.slug is not None
    slug = args.slug or slugify(title) or slugify(Path(args.source).stem)
    if not slug or not sv.SLUG_RE.match(slug):
        raise ShelfError(f"{(args.slug or title)!r} cannot be turned into a valid slug. Pass --slug with lowercase letters, digits and hyphens.")
    dest = safe_child(artifacts, slug)
    old_meta: dict = {}
    if slug in taken:
        if args.force and dest.is_dir():
            old = sv.validate_artifact(dest)
            old_meta = old.metadata or {}
        elif explicit_slug or not p.interactive and not args.auto_suffix:
            hint = " Use --force to replace it (a backup is kept), or pick another --slug." if dest.exists() else " It is an old address of another artifact (see its aliases)."
            raise ShelfError(f"The slug {slug!r} is already taken.{hint}")
        else:
            new = unique_slug(slug, taken)
            print(f"note: {slug!r} is taken; using {new!r}.")
            slug, dest = new, safe_child(artifacts, new)

    kind = args.kind or base.get("kind") or p.ask(f"Category ({', '.join(sv.KINDS)})", "app")
    description = args.description or base.get("description") or p.ask("One-line description", info["description"] or None)
    tool = args.tool or base.get("tool") or p.ask("Built with (e.g. Claude, ChatGPT)", os.environ.get("SHELF_TOOL"))
    missing = [n for n, v in (("--description", description), ("--tool", tool)) if not v]
    if missing:
        raise ShelfError(f"Missing {' and '.join(missing)}. Pass them as flags (or run in a terminal to be asked).")

    meta: dict = {
        "title": title.strip(),
        "description": " ".join(str(description).split()),
        "created": args.created or old_meta.get("created") or base.get("created") or dt.date.today().isoformat(),
        "tool": normalize_tool(str(tool)),
        "kind": kind,
    }
    tags = split_list(args.tags) if args.tags is not None else base.get("tags", [])
    optional = {
        "tags": tags,
        "status": args.status or base.get("status"),
        "storage": args.storage or base.get("storage"),
        "network": split_list(args.network) if args.network is not None else base.get("network"),
        "install": True if args.install else base.get("install"),
        "featured": True if args.featured else base.get("featured", old_meta.get("featured")),
        "why": args.why or base.get("why"),
        "notes": args.notes or base.get("notes"),
        "source": args.source_url or base.get("source"),
        "short": args.short or base.get("short") or old_meta.get("short"),
        "aliases": base.get("aliases") or old_meta.get("aliases"),
        "color": base.get("color"),
        "draft": True if args.draft else base.get("draft"),
    }
    meta.update({k: v for k, v in optional.items() if v not in (None, [], "")})
    if args.thumbnail:
        img = Path(args.thumbnail)
        if not img.is_file() or img.suffix.lower() not in sv.THUMBNAIL_SUFFIXES:
            raise ShelfError(f"--thumbnail must be an existing {'/'.join(sv.THUMBNAIL_SUFFIXES)} file.")
        meta["thumbnail"] = "thumbnail" + img.suffix.lower()
    # keep any other fields the file already had (unknown ones too: they are only warnings)
    for k, v in base.items():
        meta.setdefault(k, v)

    # --- declare what the page uses, interactively, before validation complains
    use = detect_behaviour(html)
    if "storage" not in meta and use["storage"] and p.confirm(f"The page uses {', '.join(use['storage'])}. Declare storage: local?", True):
        meta["storage"] = "local"
    if "network" not in meta and use["network"]:
        answer = p.ask(f"The page uses {', '.join(use['network'])}. Domains it contacts, comma separated (blank for none)")
        if answer:
            meta["network"] = split_list(answer)

    # --- stage in a hidden folder next to the artifacts so a failure leaves nothing behind
    artifacts.mkdir(parents=True, exist_ok=True)
    stage_root = Path(tempfile.mkdtemp(prefix=".shelf-add-", dir=artifacts))
    try:
        staged = stage_root / slug
        staged.mkdir()
        if src.is_dir():
            _copy_tree(src, staged)
        html_out = fix_basics(html) if args.fix else html
        (staged / "index.html").write_text(upsert_meta_block(html_out, meta), encoding="utf-8")
        if args.thumbnail:
            shutil.copy2(args.thumbnail, staged / meta["thumbnail"])

        result = sv.validate_artifact(staged)
        print(sv._format([result], color=sys.stdout.isatty()))
        if not result.ok:
            print(_hints(result), file=sys.stderr)
            print(f"\nNothing was added. Fix the errors above and run the command again.", file=sys.stderr)
            return 1

        # links: code and address collisions with everything already published
        _check_links(artifacts, slug, result, replacing=dest.name if dest.exists() else None)

        short = meta.get("short") or shortlinks.auto_code(slug)
        base_url = shortlinks.base_url() or shortlinks.DEFAULT_BASE_URL
        if args.dry_run:
            print(f"\nDry run: nothing written. Would create {dest.relative_to(REPO) if dest.is_relative_to(REPO) else dest}")
            print(f"metadata:\n{json.dumps(meta, indent=2, ensure_ascii=False)}")
            print(f"short link: {base_url}{short}")
            return 0

        if dest.exists():
            backup = _backup(dest)
            shutil.rmtree(dest)
            print(f"note: replaced the existing artifact; a backup is in {backup}")
        os.replace(staged, dest)  # same filesystem, so this is one atomic step
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)

    rel = dest.relative_to(REPO) if dest.is_relative_to(REPO) else dest
    print(f"\nAdded {rel}/index.html")
    print(f"  short link:  {base_url}{short}  (after publishing)")
    print(f"  full link:   {base_url}artifacts/{slug}/")
    print("  thumbnail:   " + ("your image" if args.thumbnail else "generated automatically by the build (cached)"))
    print("\nNext steps")
    print(f"  1. python shelf preview {slug}     # look at it in the full gallery")
    print(f"  2. git add artifacts/{slug} && git commit -m \"Add {meta['title']}\"")
    print("  3. git push                          # the workflow validates, builds and deploys")
    return 0


def _backup(dest: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = dest.parent.parent / ".shelf-cache" / "backups" / f"{dest.name}-{stamp}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(dest, target)
    return target


def _hints(result: sv.Result) -> str:
    """Plain-language next step for the errors people hit most when importing AI output."""
    tips = {
        "HTML-LANG": 'Add lang="en" to <html>, or re-run with --fix.',
        "HTML-VIEWPORT": "Add the viewport meta tag, or re-run with --fix.",
        "STORAGE": "The page uses browser storage: re-run with --storage local.",
        "NETWORK": "The page makes network requests: re-run with --network api.example.com (the domains it contacts).",
        "DEPENDENCY": "Use a pinned CDN URL (x.y.z) or copy the library into the artifact folder.",
    }
    seen = []
    for i in result.errors:
        for prefix, tip in tips.items():
            if i.code.startswith(prefix) and tip not in seen:
                seen.append(tip)
    return ("\nHints:\n  - " + "\n  - ".join(seen)) if seen else ""


def _check_links(artifacts: Path, slug: str, result: sv.Result, replacing: str | None) -> None:
    others = [r for r in sv.validate_all(artifacts) if r.slug != replacing and r.slug != slug and not r.slug.startswith(".")]
    published = [(r.slug, r.metadata) for r in others if r.metadata and not r.draft]
    if not result.draft:
        published.append((slug, result.metadata))
    try:
        shortlinks.plan_links(published, shortlinks.load_links())
    except shortlinks.ShortLinkError as exc:
        raise ShelfError("\n".join(exc.problems)) from None
    clash = sv.crosscheck([*others, result])
    if clash:
        raise ShelfError("\n".join(clash))


# --------------------------------------------------------------------------
# validate / list / links / rename
# --------------------------------------------------------------------------


def _targets(artifacts: Path, slugs: list[str]) -> list[Path]:
    if not slugs:
        return sv.discover(artifacts)
    paths = []
    for s in slugs:
        path = safe_child(artifacts, s)
        if not path.is_dir():
            raise ShelfError(f"No artifact named {s!r}. Run `shelf list` to see what exists.")
        paths.append(path)
    return paths


def cmd_validate(args: argparse.Namespace) -> int:
    paths = [str(p) for p in _targets(Path(args.artifacts_dir), args.slugs)] if args.slugs else ["--artifacts-dir", str(args.artifacts_dir)]
    flags = [f for f, on in (("--json", args.json), ("--strict", args.strict)) if on]
    return sv.main([*paths, *flags])


def cmd_list(args: argparse.Namespace) -> int:
    results = sv.validate_all(Path(args.artifacts_dir))
    plan = None
    published = [(r.slug, r.metadata) for r in results if r.metadata and not r.draft and r.ok]
    try:
        plan = shortlinks.plan_links(published, shortlinks.load_links())
    except shortlinks.ShortLinkError:
        pass
    rows = []
    for r in results:
        m = r.metadata or {}
        rows.append({
            "slug": r.slug, "title": m.get("title"), "kind": m.get("kind"), "status": m.get("status"),
            "created": m.get("created"), "short": (plan.artifacts.get(r.slug) if plan else None),
            "featured": m.get("featured") is True, "draft": r.draft, "install": m.get("install") is True, "ok": r.ok,
        })
    rows.sort(key=lambda x: (x["created"] or "", x["slug"]), reverse=True)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("No artifacts yet. Add one with: shelf add my-app.html")
        return 0
    cols = [("SLUG", "slug"), ("KIND", "kind"), ("STATUS", "status"), ("CREATED", "created"), ("SHORT", "short")]
    widths = [max(len(h), *(len(str(r[k] or "-")) for r in rows)) for h, k in cols]
    print("  ".join(h.ljust(w) for (h, _), w in zip(cols, widths)) + "  FLAGS")
    for r in rows:
        flags = [f for f, on in (("featured", r["featured"]), ("draft", r["draft"]), ("installable", r["install"]), ("INVALID", not r["ok"])) if on]
        print("  ".join(str(r[k] or "-").ljust(w) for (_, k), w in zip(cols, widths)) + "  " + ", ".join(flags))
    print(f"\n{len(rows)} artifact(s), {sum(1 for r in rows if r['featured'])} featured, {sum(1 for r in rows if r['draft'])} draft.")
    return 0


def git(*cmd: str, check: bool = True) -> str:
    try:
        done = subprocess.run(["git", *cmd], cwd=REPO, capture_output=True, text=True, check=check)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise ShelfError(f"git {' '.join(cmd)} failed: {detail.strip()}") from None
    return done.stdout


def published_at(ref: str) -> dict[str, dict]:
    """slug -> metadata for artifacts that were published (non-draft) at git ref."""
    out: dict[str, dict] = {}
    for line in git("ls-tree", "--name-only", f"{ref}:artifacts").splitlines():
        slug = line.strip()
        if not sv.SLUG_RE.match(slug):
            continue
        try:
            text = git("show", f"{ref}:artifacts/{slug}/index.html")
        except ShelfError:
            continue
        meta = page_info(text)["meta"]
        if meta and meta.get("draft") is not True:
            out[slug] = meta
    return out


def links_that_would_break(before: dict[str, dict], results: list[sv.Result], extra_links: dict[str, str]) -> list[str]:
    """Addresses and short codes published in `before` that no longer resolve now."""
    live_names, live_codes = set(), set(extra_links)
    for r in results:
        if r.draft or r.metadata is None:
            continue
        live_names.add(r.slug)
        live_names.update(a for a in r.metadata.get("aliases", []) if isinstance(a, str))
        live_codes.add(r.metadata.get("short") or shortlinks.auto_code(r.slug))
    problems = []
    for slug, meta in sorted(before.items()):
        if slug not in live_names:
            problems.append(f"artifacts/{slug}/ was published but is gone. Add it to the `aliases` of the artifact that replaced it (shelf rename does this), or remove it on purpose.")
        code = meta.get("short") or shortlinks.auto_code(slug)
        if code not in live_codes:
            problems.append(f"short link /{code} (from {slug!r}) no longer exists. Set \"short\": \"{code}\" on the artifact that replaced it.")
    return problems


def cmd_links(args: argparse.Namespace) -> int:
    results = sv.validate_all(Path(args.artifacts_dir))
    base = shortlinks.base_url() or shortlinks.DEFAULT_BASE_URL
    try:
        extra = shortlinks.load_links()
        plan = shortlinks.plan_links([(r.slug, r.metadata) for r in results if r.metadata and not r.draft], extra)
    except shortlinks.ShortLinkError as exc:
        raise ShelfError("\n".join(exc.problems)) from None
    titles = {r.slug: (r.metadata or {}).get("title", r.slug) for r in results}
    print(shortlinks.format_table(shortlinks.describe(plan, titles, base)))
    if args.compare:
        problems = links_that_would_break(published_at(args.compare), results, extra)
        if problems:
            print(f"\nPermanent links that would break compared with {args.compare}:", file=sys.stderr)
            for pr in problems:
                print(f"  - {pr}", file=sys.stderr)
            return 1
        print(f"\nAll links published at {args.compare} still resolve.")
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    artifacts = Path(args.artifacts_dir)
    old, new = args.old, args.new
    if not sv.SLUG_RE.match(new):
        raise ShelfError(f"{new!r} is not a valid slug (lowercase letters, digits, single hyphens).")
    src, dest = safe_child(artifacts, old), safe_child(artifacts, new)
    if not src.is_dir():
        raise ShelfError(f"No artifact named {old!r}.")
    if new in existing_slugs(artifacts):
        raise ShelfError(f"{new!r} is already taken (as a folder or as an old address).")
    text = (src / "index.html").read_text(encoding="utf-8")
    meta = page_info(text)["meta"]
    if not meta:
        raise ShelfError(f"{old}/index.html has no readable shelf-meta block; fix it with `shelf validate {old}` first.")
    published = meta.get("draft") is not True
    if published:
        meta["aliases"] = [*meta.get("aliases", []), old]
        if not meta.get("short"):  # the automatic code is derived from the slug, so pin the old one
            meta["short"] = shortlinks.auto_code(old)
    print(f"{old} -> {new}")
    if published:
        print(f"  keeps artifacts/{old}/ working (alias) and the short link /{meta['short']}")
    else:
        print("  draft: nothing was public, so no redirect is needed")
    if args.dry_run:
        print("Dry run: nothing changed.")
        return 0
    new_text = upsert_meta_block(text, meta)
    (src / "index.html").write_text(new_text, encoding="utf-8")
    os.replace(src, dest)
    result = sv.validate_artifact(dest)
    print(sv._format([result], color=False))
    return 0 if result.ok else 1


# --------------------------------------------------------------------------
# preview
# --------------------------------------------------------------------------


class _Handler(http.server.SimpleHTTPRequestHandler):
    prefix = ""

    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if self.prefix:
            if path == self.prefix:
                path = "/"
            elif path.startswith(self.prefix + "/"):
                path = path[len(self.prefix):]
            else:
                path = "/__outside_prefix__"
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *a):  # quiet unless something fails
        if a and str(a[1]).startswith(("4", "5")):
            super().log_message(fmt, *a)


def serve_directory(directory: Path, port: int, prefix: str = "") -> socketserver.TCPServer:
    handler = type("Handler", (_Handler,), {"prefix": prefix.rstrip("/")})
    socketserver.TCPServer.allow_reuse_address = True
    return socketserver.ThreadingTCPServer(("127.0.0.1", port), functools.partial(handler, directory=str(directory)))


def _site_is_stale(site: Path, artifacts: Path) -> bool:
    manifest = site / "artifacts.json"
    if not manifest.is_file():
        return True
    built = manifest.stat().st_mtime
    newest = max((p.stat().st_mtime for p in artifacts.rglob("*") if p.is_file()), default=0)
    return newest > built


def cmd_preview(args: argparse.Namespace) -> int:
    artifacts = Path(args.artifacts_dir)
    prefix = ("/" + args.base.strip("/")) if args.base.strip("/") else ""
    if args.slug:
        _targets(artifacts, [args.slug])
    if args.raw:
        root, path = artifacts, f"/{args.slug}/" if args.slug else "/"
        print("Raw preview: serving the files as they are, without the gallery, CSP or PWA files.")
    else:
        site = REPO / "site"
        if args.build or _site_is_stale(site, artifacts):
            cmd = [sys.executable, str(REPO / "tools" / "build" / "build.py")]
            if not args.thumbnails:
                cmd.append("--no-thumbnails")
            print("Building the site (use --raw for an instant preview of one artifact)...")
            if subprocess.run(cmd, cwd=REPO).returncode != 0:
                raise ShelfError("The build failed; see the errors above.")
        root = site
        path = f"/artifacts/{args.slug}/" if args.slug else "/"
    try:
        server = serve_directory(root, args.port, prefix)
    except OSError as exc:
        raise ShelfError(f"Cannot listen on port {args.port}: {exc.strerror}. Try --port {args.port + 1}.") from None
    url = f"http://127.0.0.1:{args.port}{prefix}{path}"
    print(f"\nServing {root.relative_to(REPO) if root.is_relative_to(REPO) else root} at {url}\nPress Ctrl+C to stop.")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


# --------------------------------------------------------------------------
# doctor / prompt
# --------------------------------------------------------------------------


def doctor_checks(artifacts: Path) -> list[tuple[str, str, str]]:
    """(status, name, detail) with status ok | warn | fail."""
    rows: list[tuple[str, str, str]] = []
    add = lambda s, n, d="": rows.append((s, n, d))  # noqa: E731

    v = sys.version_info
    add("ok" if v >= (3, 9) else "fail", "Python 3.9+", f"{v.major}.{v.minor}.{v.micro}")
    node = shutil.which("node")
    if node:
        ver = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
        major = int(re.match(r"v(\d+)", ver).group(1)) if re.match(r"v(\d+)", ver) else 0
        add("ok" if major >= 18 else "warn", "Node.js 18+ (gallery, thumbnails)", ver)
    else:
        add("warn", "Node.js 18+ (gallery, thumbnails)", "not found: the gallery cannot be built locally; validation and `shelf add` still work")
    add("ok" if (REPO / "gallery" / "node_modules").is_dir() else "warn", "Gallery dependencies", "installed" if (REPO / "gallery" / "node_modules").is_dir() else "run: cd gallery && npm ci")
    pw = REPO / "tools" / "build" / "node_modules" / "playwright"
    add("ok" if pw.is_dir() else "warn", "Thumbnail tooling (Playwright)", "installed" if pw.is_dir() else "run: cd tools/build && npm ci && npx playwright install chromium (thumbnails are optional)")
    try:
        git("rev-parse", "--is-inside-work-tree")
        remote = git("remote", "get-url", "origin", check=False).strip()
        add("ok" if remote else "warn", "Git remote", remote or "no `origin` remote: nothing to push to yet")
    except ShelfError:
        add("warn", "Git repository", "not a git repository")

    results = sv.validate_all(artifacts)
    bad = [r.slug for r in results if not r.ok]
    warned = sum(len(r.warnings) for r in results)
    add("fail" if bad else "ok", "Artifacts validate", f"{len(results) - len(bad)}/{len(results)} pass" + (f"; failing: {', '.join(bad)}" if bad else "") + (f"; {warned} warning(s)" if warned else ""))
    clash = sv.crosscheck(results)
    add("fail" if clash else "ok", "Slugs and aliases unique", "; ".join(clash) if clash else "no clashes")
    try:
        plan = shortlinks.plan_links([(r.slug, r.metadata) for r in results if r.metadata and not r.draft and r.ok], shortlinks.load_links())
        add("ok", "Short links", f"{len(plan.codes())} code(s), no clashes")
    except shortlinks.ShortLinkError as exc:
        add("fail", "Short links", "; ".join(exc.problems))
    site = REPO / "site"
    if site.is_dir():
        add("warn" if _site_is_stale(site, artifacts) else "ok", "Local build (site/)", "out of date: run `shelf preview --build`" if _site_is_stale(site, artifacts) else "up to date")
    else:
        add("ok", "Local build (site/)", "not built yet (`shelf preview` builds it)")
    return rows


def cmd_doctor(args: argparse.Namespace) -> int:
    rows = doctor_checks(Path(args.artifacts_dir))
    icon = {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}
    for status, name, detail in rows:
        print(f"[{icon[status]}] {name}" + (f": {detail}" if detail else ""))
    fails = sum(1 for s, *_ in rows if s == "fail")
    warns = sum(1 for s, *_ in rows if s == "warn")
    print(f"\n{fails} problem(s), {warns} warning(s).")
    return 1 if fails else 0


def prompt_text() -> str:
    text = (REPO / "spec" / "PROMPT.md").read_text(encoding="utf-8")
    m = re.search(r"````text\n(.*?)\n````", text, re.S)
    if not m:
        raise ShelfError("spec/PROMPT.md has no ````text block.")
    return m.group(1)


def cmd_prompt(args: argparse.Namespace) -> int:
    print(prompt_text())
    return 0


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="shelf", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--artifacts-dir", default=str(ARTIFACTS), help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="command", required=True, metavar="command")

    a = sub.add_parser("add", help="import an HTML file (or a folder with index.html) as a new artifact")
    a.add_argument("source", help="path to the HTML file or folder")
    a.add_argument("--title")
    a.add_argument("--slug", help="folder name; default: derived from the title")
    a.add_argument("--description", help="one line, 200 characters at most")
    a.add_argument("--kind", "--category", dest="kind", choices=sv.KINDS)
    a.add_argument("--tool", help="what built it, e.g. claude, chatgpt")
    a.add_argument("--tags", help="comma separated")
    a.add_argument("--status", choices=sv.STATUS_VALUES)
    a.add_argument("--storage", choices=sv.STORAGE_VALUES)
    a.add_argument("--network", help="comma separated domains the page contacts")
    a.add_argument("--created", help="YYYY-MM-DD (default: today)")
    a.add_argument("--why", help="why you made it")
    a.add_argument("--notes")
    a.add_argument("--source-url", help="link to the conversation or repository it came from")
    a.add_argument("--short", help="your own short-link code")
    a.add_argument("--thumbnail", help="use this image as the thumbnail instead of a screenshot")
    a.add_argument("--install", action="store_true", help="make it installable as an offline app")
    a.add_argument("--featured", action="store_true")
    a.add_argument("--draft", action="store_true", help="keep it off the public site for now")
    a.add_argument("--fix", action="store_true", help='add a missing lang attribute and viewport meta tag')
    a.add_argument("--force", action="store_true", help="replace an existing artifact with this slug (a backup is kept)")
    a.add_argument("--auto-suffix", action="store_true", help="when the derived slug is taken, use slug-2 instead of failing")
    a.add_argument("--dry-run", action="store_true", help="validate and show what would happen; write nothing")
    a.add_argument("-y", "--yes", action="store_true", help="never ask questions")
    a.set_defaults(func=cmd_add)

    v = sub.add_parser("validate", help="check artifacts against the spec")
    v.add_argument("slugs", nargs="*")
    v.add_argument("--json", action="store_true")
    v.add_argument("--strict", action="store_true", help="treat warnings as errors")
    v.set_defaults(func=cmd_validate)

    ls = sub.add_parser("list", help="show every artifact")
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list)

    pv = sub.add_parser("preview", help="build the site and serve it locally")
    pv.add_argument("slug", nargs="?")
    pv.add_argument("--port", type=int, default=8000)
    pv.add_argument("--base", default="/shelf", help="URL prefix to mimic GitHub Pages (default /shelf; use / for none)")
    pv.add_argument("--build", action="store_true", help="rebuild even if the site looks current")
    pv.add_argument("--thumbnails", action="store_true", help="also generate thumbnails (needs Playwright)")
    pv.add_argument("--raw", action="store_true", help="serve artifacts/ directly: instant, no build")
    pv.add_argument("--open", action="store_true", help="open a browser")
    pv.set_defaults(func=cmd_preview)

    rn = sub.add_parser("rename", help="rename an artifact and keep its old links working")
    rn.add_argument("old")
    rn.add_argument("new")
    rn.add_argument("--dry-run", action="store_true")
    rn.set_defaults(func=cmd_rename)

    lk = sub.add_parser("links", help="list short links; --compare REF checks nothing published at REF disappeared")
    lk.add_argument("--compare", metavar="REF", help="a git ref such as origin/main")
    lk.set_defaults(func=cmd_links)

    sub.add_parser("doctor", help="check the local setup").set_defaults(func=cmd_doctor)
    sub.add_parser("prompt", help="print the instructions to give an AI assistant").set_defaults(func=cmd_prompt)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ShelfError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ncancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
