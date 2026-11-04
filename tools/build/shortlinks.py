#!/usr/bin/env python3
"""Short links for Shelf.

Shelf is static hosting, so there are no server redirects. A short link is a folder:

    site/<code>/index.html   ->   the artifact itself (no redirect, so the address stays short),
                                  or, for links.json entries, a tiny redirect page to any https URL

so https://<host>/<code> opens the artifact. Two kinds of code exist:

  * artifact codes: every published artifact gets one automatically and is served at /<code>/.
    It is a 4-character code derived from the slug (the same slug always gives the same
    code), or the artifact's own `"short"` metadata field when it sets one. The long
    address artifacts/<slug>/ stays alive as a redirect to it.
  * extra links: `links.json` at the repository root maps `"code": "https://..."`
    for any other address, which makes Shelf a general URL shortener.

Usage (prints the short link, so it can go on a slide before you publish):

    python tools/build/shortlinks.py                 # every link
    python tools/build/shortlinks.py pomodoro-timer  # one artifact
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "validate"))
import shelf_validate as sv  # noqa: E402

LINKS_FILE = REPO / "links.json"
DEFAULT_BASE_URL = "https://ariffurrhmn.github.io/shelf/"

# 31 characters: lowercase letters and digits without the look-alikes
# i, l, o, 0 and 1, so a code can be read aloud or typed from a slide.
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
AUTO_LENGTH = 4
MAX_URL_LENGTH = 2000


class ShortLinkError(Exception):
    """One or more short-link problems; `problems` holds readable messages."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass
class Plan:
    """The final code -> destination mapping for one build."""

    artifacts: dict[str, str] = field(default_factory=dict)  # slug -> code
    external: dict[str, str] = field(default_factory=dict)  # code -> URL

    def codes(self) -> list[str]:
        return sorted([*self.artifacts.values(), *self.external])


def auto_code(slug: str, length: int = AUTO_LENGTH) -> str:
    """Stable code for a slug. No state, so it never changes between builds."""
    n = int.from_bytes(hashlib.sha256(slug.encode("utf-8")).digest(), "big")
    out = []
    for _ in range(length):
        n, i = divmod(n, len(ALPHABET))
        out.append(ALPHABET[i])
    return "".join(out)


def load_links(path: Path = LINKS_FILE) -> dict[str, str]:
    """Read links.json (a flat {"code": "url"} object). A missing file is fine."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ShortLinkError([f"{path.name} is not valid JSON: {exc.msg} (line {exc.lineno}, col {exc.colno})."]) from exc
    if not isinstance(data, dict):
        raise ShortLinkError([f'{path.name} must be a JSON object such as {{"talk": "https://example.com/slides"}}.'])
    problems = []
    for code, url in data.items():
        if (why := sv.short_code_problem(code)) is not None:
            problems.append(f"{path.name}: code {code!r} {why}.")
        if (why := url_problem(url)) is not None:
            problems.append(f"{path.name}: {code!r} {why}.")
    if problems:
        raise ShortLinkError(problems)
    return dict(data)


def url_problem(url: object) -> str | None:
    if not isinstance(url, str):
        return "needs a URL string"
    if url != url.strip() or any(ch.isspace() for ch in url):
        return "has whitespace in its URL"
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return "must point to an http:// or https:// URL"
    if len(url) > MAX_URL_LENGTH:
        return f"has a URL longer than {MAX_URL_LENGTH} characters"
    return None


def plan_links(artifacts: list[tuple[str, dict]], extra: dict[str, str]) -> Plan:
    """Assign a code to every published artifact and check nothing collides.

    `artifacts` is [(slug, metadata)] for published (non-draft) artifacts.
    Nothing is ever renumbered silently: a collision is an error that says
    which `short` field to set, so printed links keep working.
    """
    claims: dict[str, list[str]] = {}
    plan = Plan(external=dict(extra))
    for code in extra:
        claims.setdefault(code, []).append("links.json")
    for slug, meta in sorted(artifacts):
        code = meta.get("short") or auto_code(slug)
        origin = f"artifact {slug!r}" + ("" if meta.get("short") else f" (automatic code {code!r})")
        claims.setdefault(code, []).append(origin)
        plan.artifacts[slug] = code
        if (why := sv.short_code_problem(code)) is not None:  # only reachable for automatic codes
            raise ShortLinkError([f"{origin}: code {code!r} {why}. Set a different \"short\" in its metadata."])
    problems = [
        f"Short code {code!r} is claimed by more than one thing: {', '.join(owners)}. "
        'Give one of the artifacts its own "short" in metadata, or rename the links.json entry.'
        for code, owners in sorted(claims.items())
        if len(owners) > 1
    ]
    if problems:
        raise ShortLinkError(problems)
    return plan


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
{share}<title>Redirecting to {label}</title>
<link rel="canonical" href="{href}">
<script>
(function () {{
  var base = location.origin + location.pathname.replace(/\\/?$/, "/");
  var url = new URL({target}, base).href{forward};
  location.replace(url);
}})();
</script>
<noscript><meta http-equiv="refresh" content="0; url={href}"></noscript>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px; font: 16px/1.5 system-ui, sans-serif; }}
</style>
</head>
<body>
<p>Redirecting to <a href="{href}">{label}</a>&hellip;</p>
</body>
</html>
"""


def _js_string(value: str) -> str:
    return json.dumps(value).replace("<", "\\u003c")


def redirect_page(target: str, label: str, *, forward: bool, share: str = "") -> str:
    """HTML for one redirect. `forward` carries ?query and #hash to the target,
    which is how a link like /ab3k#4 can open slide 4. `share` is optional
    pre-escaped <meta> markup (Open Graph) so crawlers see a card."""
    return _PAGE.format(
        share=share + "\n" if share else "",
        href=html.escape(target, quote=True),
        label=html.escape(label),
        target=_js_string(target),
        forward=" + location.search + location.hash" if forward else "",
    )


def write_redirects(out: Path, plan: Plan) -> int:
    """Write site/<code>/index.html for every extra link in links.json. Returns how many.

    Artifact codes are not redirects: the artifact itself is served at /<code>/ (see build.py)."""
    problems = [
        f"Short code {code!r} would overwrite {out / code}; choose a different code."
        for code in plan.external
        if (out / code).exists()
    ]
    if problems:
        raise ShortLinkError(problems)
    for code, url in plan.external.items():
        _write(out / code, redirect_page(url, urlparse(url).netloc, forward=False))
    return len(plan.external)


def _write(folder: Path, text: str) -> None:
    folder.mkdir(parents=True)
    (folder / "index.html").write_text(text, encoding="utf-8")


def write_alias_redirects(out: Path, targets: dict[str, str]) -> int:
    """Keep every older address alive: site/artifacts/<name>/ -> ../../<code>/.

    `targets` maps a name (the artifact's slug, or an old slug from `aliases`) to the short code the
    artifact is now served at. Query string and hash are forwarded, so an old link to a slide still
    opens that slide."""
    problems = [
        f"Address artifacts/{name}/ ({code!r}) would overwrite {out / 'artifacts' / name}; remove the alias or rename the artifact."
        for name, code in sorted(targets.items())
        if (out / "artifacts" / name).exists()
    ]
    if problems:
        raise ShortLinkError(problems)
    for name, code in targets.items():
        _write(out / "artifacts" / name, redirect_page(f"../../{code}/", code, forward=True))
    return len(targets)


def base_url(env: dict[str, str] | None = None) -> str | None:
    """Public address of the site, when the environment tells us (always ends in /)."""
    env = os.environ if env is None else env
    if env.get("SHELF_BASE_URL", "").strip():
        return env["SHELF_BASE_URL"].strip().rstrip("/") + "/"
    if env.get("SHELF_CNAME", "").strip():
        return f"https://{env['SHELF_CNAME'].strip()}/"
    if "/" in env.get("GITHUB_REPOSITORY", ""):
        owner, repo = env["GITHUB_REPOSITORY"].split("/", 1)
        host = f"{owner.lower()}.github.io"
        return f"https://{host}/" if repo.lower() == host else f"https://{host}/{repo}/"
    return None


def describe(plan: Plan, titles: dict[str, str], base: str | None) -> list[tuple[str, str, str]]:
    """Rows of (short link, what it opens, kind) for printing."""
    prefix = base or "/"
    rows = [(prefix + code, titles.get(slug, slug), "artifact") for slug, code in sorted(plan.artifacts.items(), key=lambda kv: kv[1])]
    rows += [(prefix + code, url, "link") for code, url in sorted(plan.external.items())]
    return rows


def format_table(rows: list[tuple[str, str, str]]) -> str:
    if not rows:
        return "No short links."
    width = max(len(r[0]) for r in rows)
    return "\n".join(f"  {link.ljust(width)}  {target}" for link, target, _ in rows)


def format_markdown(rows: list[tuple[str, str, str]]) -> str:
    lines = ["## Short links", "", "| Short link | Opens |", "| --- | --- |"]
    for link, target, _ in rows:
        escaped = target.replace("|", "\\|")
        lines.append(f"| `{link}` | {escaped} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?", help="show only this artifact's short link")
    ap.add_argument("--artifacts-dir", type=Path, default=REPO / "artifacts")
    ap.add_argument("--links", type=Path, default=LINKS_FILE)
    args = ap.parse_args(argv)

    results = sv.validate_all(args.artifacts_dir)
    broken = [r.slug for r in results if not r.ok]
    if broken:
        print(f"Cannot list short links: {', '.join(broken)} fail validation. Run tools/validate/shelf_validate.py.", file=sys.stderr)
        return 1
    drafts = {r.slug for r in results if r.draft}
    try:
        plan = plan_links([(r.slug, r.metadata) for r in results if not r.draft], load_links(args.links))
    except ShortLinkError as exc:
        print("\n".join(f"error: {p}" for p in exc.problems), file=sys.stderr)
        return 1

    base = base_url() or DEFAULT_BASE_URL
    if args.slug:
        if args.slug in drafts:
            print(f"{args.slug} is a draft: it is not published, so it has no short link yet.", file=sys.stderr)
            return 1
        if args.slug not in plan.artifacts:
            print(f"No artifact named {args.slug!r}.", file=sys.stderr)
            return 1
        print(base + plan.artifacts[args.slug])
        return 0
    titles = {r.slug: r.metadata["title"] for r in results if r.metadata}
    print(format_table(describe(plan, titles, base)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
