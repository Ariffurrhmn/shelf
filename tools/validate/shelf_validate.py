#!/usr/bin/env python3
"""Shelf artifact validator.

Checks every artifact under ``artifacts/<slug>/`` against ``spec/SPEC.md``
and fails with readable errors. Standard library only (Python 3.9+).

Usage:
    python tools/validate/shelf_validate.py                 # all artifacts
    python tools/validate/shelf_validate.py artifacts/foo   # one artifact
    python tools/validate/shelf_validate.py --json          # machine output
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

# --------------------------------------------------------------------------
# Configuration (decisions recorded in docs/decisions.md)
# --------------------------------------------------------------------------

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$")

KINDS = ("app", "presentation", "doc", "game", "other")
STORAGE_VALUES = ("none", "local")
REQUIRED_FIELDS = ("title", "description", "created", "tool", "kind")
OPTIONAL_FIELDS = ("tags", "storage", "network", "draft", "notes", "install", "color")
KNOWN_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# File names the build writes into installable artifacts; authors must not use them.
PWA_RESERVED_FILES = ("sw.js", "manifest.webmanifest", "icon-192.png", "icon-512.png")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# CDN hosts whose URLs must carry an exact version.
ALLOWED_CDN_HOSTS = (
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
    "unpkg.com",
    "code.jquery.com",
)
# Font hosts: allowed, but their URLs are not versioned.
ALLOWED_FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")

EXACT_VERSION_RE = re.compile(r"[@/-]v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)(?=[/@.?#_-]|$)")
RANGE_MARKERS_RE = re.compile(r"@[\^~><*]|@latest|/latest/|@next\b|\blatest\b", re.I)

TEXT_SUFFIXES = {
    ".html", ".htm", ".js", ".mjs", ".css", ".json", ".svg", ".txt", ".md", ".xml",
}

STORAGE_PATTERNS = [
    (re.compile(r"\blocalStorage\b"), "localStorage"),
    (re.compile(r"\bsessionStorage\b"), "sessionStorage"),
    (re.compile(r"\bindexedDB\b|\bopenDatabase\b"), "IndexedDB"),
    (re.compile(r"\bdocument\s*\.\s*cookie\b|\bcookieStore\b"), "cookies"),
    (re.compile(r"\bserviceWorker\b"), "service workers"),
    (re.compile(r"\bcaches\s*\.\s*(?:open|match|keys)\b"), "Cache API"),
]

NETWORK_PATTERNS = [
    (re.compile(r"\bfetch\s*\("), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\bnew\s+WebSocket\b"), "WebSocket"),
    (re.compile(r"\bsendBeacon\b"), "navigator.sendBeacon"),
    (re.compile(r"\bnew\s+EventSource\b"), "EventSource"),
    (re.compile(r"\bimportScripts\s*\("), "importScripts()"),
]

SECRET_PATTERNS = [
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"), "GitHub fine-grained token"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"), "Anthropic API key"),
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}"), "OpenAI-style API key"),
    (re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"), "Stripe live key"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), "Slack token"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "Google API key"),
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"), "private key block"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "JSON web token"),
    (
        re.compile(
            r"""(?ix)\b(?:api[_-]?key|secret|access[_-]?token|auth[_-]?token|password|passwd|private[_-]?key)\b
                ["']?\s*[:=]\s*["'][^"'\s]{8,}["']"""
        ),
        "hard-coded credential assignment",
    ),
]

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b")
SAFE_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")
SAFE_EMAIL_SUFFIXES = (".test", ".invalid", ".example", ".localhost")
PHONE_RE = re.compile(r"(?<![\w.])(?:\+\d{1,3}[ .\-]?)?(?:\(\d{2,4}\)[ .\-]?)?\d{3,4}[ .\-]\d{3,4}[ .\-]\d{3,4}(?![\w.])")

# --------------------------------------------------------------------------
# Result model
# --------------------------------------------------------------------------

ERROR, WARNING = "error", "warning"
# These stay errors even for drafts, because drafts are still public.
ALWAYS_ERROR_PREFIXES = ("SECRET", "PII", "META")


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    file: str = "index.html"
    line: int | None = None

    def to_dict(self) -> dict:
        return {
            "severity": self.severity, "code": self.code, "message": self.message,
            "file": self.file, "line": self.line,
        }


@dataclass
class Result:
    slug: str
    path: Path
    issues: list[Issue] = field(default_factory=list)
    metadata: dict | None = None
    draft: bool = False

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, severity: str, code: str, message: str, file: str = "index.html", line: int | None = None) -> None:
        self.issues.append(Issue(severity, code, message, file, line))

    def error(self, code: str, message: str, **kw) -> None:
        self.add(ERROR, code, message, **kw)

    def warn(self, code: str, message: str, **kw) -> None:
        self.add(WARNING, code, message, **kw)


# --------------------------------------------------------------------------
# HTML parsing
# --------------------------------------------------------------------------


class _Page(HTMLParser):
    """Collects the facts the rules need from index.html."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang: str | None = None
        self.has_html_tag = False
        self.viewport: str | None = None
        self.title = ""
        self.has_title_tag = False
        self._in_title = False
        self._in_head = False
        self._seen_body = False
        self.meta_blocks: list[tuple[str, int, bool, str]] = []  # (text, line, in_head, type)
        self.scripts: list[dict] = []  # {src, text, line, type}
        self.styles: list[tuple[str, int]] = []
        self.refs: list[tuple[str, str, int]] = []  # (tag, url, line)
        self.inline_styles: list[tuple[str, int]] = []
        self.form_actions: list[tuple[str, int]] = []
        self._capture: dict | None = None

    # -- helpers
    def _line(self) -> int:
        return self.getpos()[0]

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        line = self._line()
        if tag == "html":
            self.has_html_tag = True
            self.html_lang = a.get("lang")
        elif tag == "head":
            self._in_head = True
        elif tag == "body":
            self._seen_body = True
            self._in_head = False
        elif tag == "title":
            self._in_title = True
            self.has_title_tag = True
        elif tag == "meta" and a.get("name", "").lower() == "viewport":
            self.viewport = a.get("content", "")
        elif tag == "script":
            if a.get("id") == "shelf-meta":
                self._capture = {"kind": "meta", "line": line, "in_head": self._in_head and not self._seen_body,
                                "type": a.get("type", ""), "text": ""}
            else:
                self._capture = {"kind": "script", "line": line, "src": a.get("src"), "type": a.get("type", ""), "text": ""}
                if a.get("src"):
                    self.refs.append(("script", a["src"], line))
        elif tag == "style":
            self._capture = {"kind": "style", "line": line, "text": ""}
        elif tag == "link":
            href = a.get("href")
            if href:
                rel = a.get("rel", "").lower()
                self.refs.append(("link:" + rel, href, line))
        elif tag in ("img", "source", "video", "audio", "iframe", "embed", "track", "input"):
            for key in ("src", "poster"):
                if a.get(key):
                    self.refs.append((tag, a[key], line))
            if a.get("srcset"):
                for part in a["srcset"].split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.refs.append((tag, url, line))
        elif tag == "object" and a.get("data"):
            self.refs.append((tag, a["data"], line))
        elif tag == "a" and a.get("href"):
            self.refs.append(("a", a["href"], line))
        elif tag == "form" and a.get("action"):
            self.form_actions.append((a["action"], line))
        if a.get("style"):
            self.inline_styles.append((a["style"], line))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self._in_head = False
        elif tag in ("script", "style") and self._capture is not None:
            c, self._capture = self._capture, None
            if c["kind"] == "meta":
                self.meta_blocks.append((c["text"], c["line"], c["in_head"], c["type"].strip().lower()))
            elif c["kind"] == "script":
                self.scripts.append(c)
            else:
                self.styles.append((c["text"], c["line"]))

    def handle_data(self, data):
        if self._capture is not None:
            self._capture["text"] += data
        elif self._in_title:
            self.title += data


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------


def _domain_allowed(host: str, domains: list[str]) -> bool:
    host = host.lower()
    return any(host == d or host.endswith("." + d) for d in domains)


def _check_metadata(res: Result, page: _Page) -> dict | None:
    blocks = page.meta_blocks
    if not blocks:
        res.error("META-MISSING", 'No <script type="application/json" id="shelf-meta"> block found in <head>.')
        return None
    if len(blocks) > 1:
        res.error("META-DUPLICATE", f"Found {len(blocks)} shelf-meta blocks; exactly one is allowed.", line=blocks[1][1])
    text, line, in_head, mtype = blocks[0]
    if not in_head:
        res.error("META-PLACEMENT", "The shelf-meta block must be inside <head>.", line=line)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        res.error("META-JSON", f"shelf-meta is not valid JSON: {exc.msg} (line {exc.lineno}, col {exc.colno} of the block).", line=line)
        return None
    if not isinstance(data, dict):
        res.error("META-JSON", "shelf-meta must be a JSON object.", line=line)
        return None
    if mtype != "application/json":
        res.error("META-TYPE", 'shelf-meta must have type="application/json".', line=line)

    for name in REQUIRED_FIELDS:
        if name not in data:
            res.error("META-REQUIRED", f'Missing required metadata field "{name}".', line=line)
    for name in data:
        if name not in KNOWN_FIELDS:
            res.warn("META-UNKNOWN", f'Unknown metadata field "{name}" is ignored.', line=line)

    def need_str(name: str, max_len: int | None = None) -> str | None:
        if name not in data:
            return None
        v = data[name]
        if not isinstance(v, str) or not v.strip():
            res.error("META-TYPE", f'"{name}" must be a non-empty string.', line=line)
            return None
        if max_len and len(v) > max_len:
            res.error("META-LENGTH", f'"{name}" is {len(v)} characters; the limit is {max_len}.', line=line)
        return v

    need_str("title", 80)
    desc = need_str("description", 200)
    if desc and ("\n" in desc or "\r" in desc):
        res.error("META-DESCRIPTION", '"description" must be a single line.', line=line)
    need_str("tool", 80)
    if (created := need_str("created")) is not None:
        try:
            d = _dt.date.fromisoformat(created)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", created):
                raise ValueError
            if d > _dt.date.today():
                res.warn("META-DATE", f'"created" ({created}) is in the future.', line=line)
        except ValueError:
            res.error("META-DATE", f'"created" must be a real date as YYYY-MM-DD, got "{created}".', line=line)
    if (kind := data.get("kind")) is not None and kind not in KINDS:
        res.error("META-KIND", f'"kind" must be one of {", ".join(KINDS)}; got {kind!r}.', line=line)
    if "storage" in data and data["storage"] not in STORAGE_VALUES:
        res.error("META-STORAGE", f'"storage" must be "none" or "local"; got {data["storage"]!r}.', line=line)
    if "tags" in data:
        t = data["tags"]
        if not (isinstance(t, list) and all(isinstance(x, str) and x.strip() for x in t)):
            res.error("META-TYPE", '"tags" must be a list of non-empty strings.', line=line)
    if "network" in data:
        n = data["network"]
        if not isinstance(n, list) or not all(isinstance(x, str) for x in n):
            res.error("META-TYPE", '"network" must be a list of domain strings.', line=line)
        else:
            for dom in n:
                if not DOMAIN_RE.match(dom):
                    res.error("META-NETWORK", f'"network" entry {dom!r} must be a bare domain such as "cdn.jsdelivr.net" (no scheme, path or port).', line=line)
    if "draft" in data and not isinstance(data["draft"], bool):
        res.error("META-TYPE", '"draft" must be true or false.', line=line)
    if "notes" in data and not isinstance(data["notes"], str):
        res.error("META-TYPE", '"notes" must be a string.', line=line)
    if "install" in data and not isinstance(data["install"], bool):
        res.error("META-TYPE", '"install" must be true or false.', line=line)
    if "color" in data and not (isinstance(data["color"], str) and COLOR_RE.match(data["color"])):
        res.error("META-COLOR", f'"color" must be a hex colour such as "#d64933"; got {data["color"]!r}.', line=line)
    return data


def _check_html(res: Result, page: _Page) -> None:
    if not page.has_html_tag or not (page.html_lang or "").strip():
        res.error("HTML-LANG", "The <html> element needs a lang attribute, e.g. <html lang=\"en\">.")
    vp = (page.viewport or "").replace(" ", "").lower()
    if page.viewport is None:
        res.error("HTML-VIEWPORT", 'Missing <meta name="viewport" content="width=device-width, initial-scale=1">.')
    elif "width=device-width" not in vp:
        res.error("HTML-VIEWPORT", 'The viewport meta tag must include "width=device-width" so the layout works on phones.')
    if not page.has_title_tag or not page.title.strip():
        res.error("HTML-TITLE", "A non-empty <title> is required.")


def _classify_ref(url: str):
    """Return ("data"|"anchor"|"special"|"remote"|"local", parsed)."""
    u = url.strip()
    low = u.lower()
    if not u:
        return "empty", None
    if low.startswith("data:") or low.startswith("blob:") or low.startswith("about:"):
        return "data", None
    if u.startswith("#"):
        return "anchor", None
    if low.startswith(("mailto:", "tel:", "javascript:", "sms:")):
        return "special", None
    if low.startswith("//"):
        return "remote", urlparse("https:" + u)
    p = urlparse(u)
    if p.scheme in ("http", "https"):
        return "remote", p
    if p.scheme:
        return "special", p
    return "local", p


def _check_ref_local(res: Result, root: Path, url: str, tag: str, line: int, fname: str) -> None:
    path = urlparse(url).path
    if not path:
        return
    if path.startswith("/"):
        res.error("LAYOUT-OUTSIDE", f'{tag} reference "{url}" is root-absolute; use a relative path inside the artifact folder.', file=fname, line=line)
        return
    target = (root / path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        res.error("LAYOUT-OUTSIDE", f'{tag} reference "{url}" points outside the artifact folder.', file=fname, line=line)
        return
    if tag != "a" and not target.exists():
        res.error("LAYOUT-MISSING", f'{tag} reference "{url}" does not exist in the artifact folder.', file=fname, line=line)


def _check_dependency_url(res: Result, url: str, kind: str, line: int, network: list[str], fname: str) -> None:
    _, p = _classify_ref(url)
    host = (p.hostname or "").lower()
    if host in ALLOWED_FONT_HOSTS:
        if host not in network:
            res.warn("NET-UNLISTED", f'"{host}" serves a font and should be listed in "network".', file=fname, line=line)
        return
    if host not in ALLOWED_CDN_HOSTS:
        res.error(
            "DEP-HOST",
            f'{kind} loads from "{host}", which is not an approved CDN. Approved: {", ".join(ALLOWED_CDN_HOSTS)}. '
            "Inline the code or copy the file into the artifact folder.",
            file=fname, line=line,
        )
        return
    full = p.path + ("?" + p.query if p.query else "")
    if RANGE_MARKERS_RE.search(full) or not EXACT_VERSION_RE.search(full):
        res.error(
            "DEP-VERSION",
            f'{kind} "{url}" must pin an exact version such as "@1.2.3" or "/1.2.3/"; '
            '"latest", ranges and partial versions are not allowed.',
            file=fname, line=line,
        )
    if host not in network:
        res.warn("NET-UNLISTED", f'CDN host "{host}" should be listed in "network" so external reach is visible.', file=fname, line=line)


CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)|@import\s+(['"])([^'"]+)\3""", re.I)


def _check_css_refs(res: Result, css: str, base_line: int, network: list[str], root: Path, fname: str) -> None:
    for m in CSS_URL_RE.finditer(css):
        url = m.group(2) or m.group(4)
        if not url:
            continue
        line = base_line + css.count("\n", 0, m.start())
        kind, p = _classify_ref(url)
        if kind == "remote":
            host = (p.hostname or "").lower()
            if m.group(4):  # @import acts as a stylesheet dependency
                _check_dependency_url(res, url, "@import", line, network, fname)
            elif host in ALLOWED_FONT_HOSTS:
                if host not in network:
                    res.warn("NET-UNLISTED", f'"{host}" should be listed in "network".', file=fname, line=line)
            elif not _domain_allowed(host, network):
                res.error("NET-REMOTE-ASSET", f'CSS loads "{url}" from "{host}", which is not listed in "network".', file=fname, line=line)
        elif kind == "local":
            _check_ref_local(res, root, url, "CSS url()", line, fname)


def _check_refs(res: Result, page: _Page, network: list[str], root: Path) -> None:
    for tag, url, line in page.refs:
        kind, p = _classify_ref(url)
        if kind in ("empty", "data", "anchor", "special"):
            continue
        if kind == "local":
            _check_ref_local(res, root, url, tag, line, "index.html")
            continue
        host = (p.hostname or "").lower()
        if tag == "script":
            _check_dependency_url(res, url, "Script", line, network, "index.html")
        elif tag.startswith("link:"):
            rel = tag[5:]
            if "stylesheet" in rel:
                _check_dependency_url(res, url, "Stylesheet", line, network, "index.html")
            elif any(r in rel for r in ("preconnect", "dns-prefetch", "preload", "modulepreload")):
                if host not in ALLOWED_CDN_HOSTS + ALLOWED_FONT_HOSTS and not _domain_allowed(host, network):
                    res.error("NET-REMOTE-ASSET", f'"{url}" is not listed in "network".', line=line)
            elif any(r in rel for r in ("icon", "image", "manifest")):
                if not _domain_allowed(host, network):
                    res.error("NET-REMOTE-ASSET", f'Remote {rel} "{url}" is not listed in "network".', line=line)
        elif tag == "a":
            continue  # outbound links are navigation, not requests
        else:
            if not _domain_allowed(host, network):
                res.error(
                    "NET-REMOTE-ASSET",
                    f'<{tag}> loads "{url}" from "{host}", which is not listed in "network". '
                    "Inline the image (data: URI) or list the domain.",
                    line=line,
                )
    for action, line in page.form_actions:
        kind, p = _classify_ref(action)
        if kind == "remote" and not _domain_allowed((p.hostname or "").lower(), network):
            res.error("NET-FORM", f'Form posts to "{action}", which is not listed in "network".', line=line)
    for css, line in page.styles:
        _check_css_refs(res, css, line, network, root, "index.html")
    for css, line in page.inline_styles:
        _check_css_refs(res, css, line, network, root, "index.html")


def _check_behaviour(res: Result, files: dict[str, str], meta: dict) -> None:
    storage = meta.get("storage", "none")
    network = meta.get("network", []) or []
    for fname, text in files.items():
        if Path(fname).suffix.lower() not in (".html", ".htm", ".js", ".mjs"):
            continue
        if storage != "local":
            for pat, label in STORAGE_PATTERNS:
                for m in pat.finditer(text):
                    res.error(
                        "STORAGE",
                        f'Uses {label} but metadata does not declare "storage": "local".',
                        file=fname, line=_line_of(text, m.start()),
                    )
                    break  # one report per API per file keeps output readable
        if not network:
            for pat, label in NETWORK_PATTERNS:
                for m in pat.finditer(text):
                    res.error(
                        "NETWORK",
                        f"Uses {label} but metadata lists no allowed domains in \"network\".",
                        file=fname, line=_line_of(text, m.start()),
                    )
                    break


def _check_install(res: Result, root: Path, meta: dict) -> None:
    """Rules for artifacts that opt in to being installed as a PWA (SPEC section 10)."""
    if meta.get("install") is not True:
        return
    for name in PWA_RESERVED_FILES:
        if (root / name).exists():
            res.error(
                "PWA-RESERVED",
                f'"{name}" is reserved: the build generates it for installable artifacts. Remove or rename it.',
                file=name,
            )
    net = meta.get("network", [])
    if isinstance(net, list):
        live = [n for n in net if isinstance(n, str) and n.lower() not in ALLOWED_CDN_HOSTS + ALLOWED_FONT_HOSTS]
        if live:
            res.warn(
                "PWA-OFFLINE",
                f"Installable, but requests to {', '.join(live)} need a connection; the app only works offline "
                "where it handles that. Pinned CDN files are cached after the first online visit.",
            )


def _check_secrets(res: Result, files: dict[str, str]) -> None:
    for fname, text in files.items():
        for pat, label in SECRET_PATTERNS:
            for m in pat.finditer(text):
                res.error(
                    "SECRET",
                    f"Possible {label}. Remove it and rotate the credential if it was real.",
                    file=fname, line=_line_of(text, m.start()),
                )
        for m in EMAIL_RE.finditer(text):
            domain = m.group(1).lower()
            if domain in SAFE_EMAIL_DOMAINS or domain.endswith(SAFE_EMAIL_SUFFIXES):
                continue
            if m.group(0).lower().startswith(("noreply@", "no-reply@")):
                continue
            # Skip versioned package specs such as "lib@1.2.3" matched by accident.
            if re.fullmatch(r"[\d.]+", domain):
                continue
            res.error(
                "PII",
                f'Contains an email address ({m.group(0)}). Use an @example.com address, or remove it.',
                file=fname, line=_line_of(text, m.start()),
            )
        for m in PHONE_RE.finditer(text):
            res.warn(
                "PII-PHONE",
                f'Looks like a phone number ("{m.group(0).strip()}"). Check it is not personal data.',
                file=fname, line=_line_of(text, m.start()),
            )


def _check_presentation(res: Result, files: dict[str, str], page: _Page) -> None:
    code = "\n".join(t for n, t in files.items() if Path(n).suffix.lower() in (".html", ".htm", ".js", ".mjs"))
    css = "\n".join([c for c, _ in page.styles] + [t for n, t in files.items() if n.endswith(".css")])
    has_arrows = bool(re.search(r"ArrowRight|keyCode\s*={1,3}\s*39|\bwhich\s*={1,3}\s*39", code)) and \
        bool(re.search(r"ArrowLeft|keyCode\s*={1,3}\s*37|\bwhich\s*={1,3}\s*37", code))
    has_space = bool(re.search(r"""['"]\s['"]|['"]Space['"]|['"]Spacebar['"]|keyCode\s*={1,3}\s*32|\bwhich\s*={1,3}\s*32""", code))
    if not has_arrows:
        res.error("PRES-KEYS", "Presentations must handle the ArrowLeft and ArrowRight keys.")
    if not has_space:
        res.error("PRES-SPACE", "Presentations must advance with the space bar.")
    has_fs_api = "requestFullscreen" in code or "webkitRequestFullscreen" in code
    has_f_key = bool(re.search(r"""['"][fF]['"]|KeyF|keyCode\s*={1,3}\s*70|\bwhich\s*={1,3}\s*70""", code))
    if not (has_fs_api and has_f_key):
        res.error("PRES-FULLSCREEN", "Presentations must toggle fullscreen with the F key (requestFullscreen on keydown).")
    has_print = bool(re.search(r"@media\s+print", css, re.I)) and \
        bool(re.search(r"(?:page-)?break-(?:after|before|inside)|page-break-(?:after|before)", css, re.I))
    if not has_print:
        res.error("PRES-PRINT", "Presentations need @media print CSS with page breaks so each slide prints on its own page.")


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def _read_text_files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
            try:
                out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8", errors="replace")
    return out


def validate_artifact(path: str | Path) -> Result:
    root = Path(path)
    slug = root.name
    res = Result(slug=slug, path=root)

    if not SLUG_RE.match(slug):
        res.error("LAYOUT-SLUG", f'Folder name "{slug}" is not a valid slug: use lowercase letters, digits and single hyphens, starting with a letter or digit.', file=".")
    entry = root / "index.html"
    if not entry.is_file():
        res.error("LAYOUT-ENTRY", "artifacts/<slug>/index.html is required but was not found.", file=".")
        return res

    files = _read_text_files(root)
    html = files.get("index.html", "")
    page = _Page()
    try:
        page.feed(html)
        page.close()
    except Exception as exc:  # parser is lenient; this is a safety net
        res.error("HTML-PARSE", f"Could not parse index.html: {exc}")
        return res

    meta = _check_metadata(res, page)
    _check_html(res, page)

    network = []
    if meta is not None:
        res.metadata = meta
        res.draft = meta.get("draft") is True
        net = meta.get("network", [])
        network = [n.lower() for n in net if isinstance(n, str)] if isinstance(net, list) else []
        _check_behaviour(res, files, meta)
        _check_install(res, root, meta)
        if meta.get("kind") == "presentation":
            _check_presentation(res, files, page)
    _check_refs(res, page, network, root)
    # Local script/style files can also pull remote resources.
    for fname, text in files.items():
        if fname.endswith(".css"):
            _check_css_refs(res, text, 1, network, root, fname)
    _check_secrets(res, files)

    if res.draft:
        for issue in res.issues:
            if issue.severity == ERROR and not issue.code.startswith(ALWAYS_ERROR_PREFIXES):
                issue.severity = WARNING
                issue.message += " (draft: reported as a warning)"
    return res


def discover(artifacts_dir: str | Path) -> list[Path]:
    base = Path(artifacts_dir)
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("."))


def validate_all(artifacts_dir: str | Path) -> list[Result]:
    return [validate_artifact(p) for p in discover(artifacts_dir)]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _format(results: list[Result], color: bool) -> str:
    def c(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if color else s

    lines: list[str] = []
    for r in results:
        status = c("32", "PASS") if r.ok else c("31", "FAIL")
        draft = c("33", " (draft)") if r.draft else ""
        lines.append(f"{status} {r.slug}{draft}")
        for i in r.issues:
            loc = f"{i.file}:{i.line}" if i.line else i.file
            tag = c("31", "error") if i.severity == ERROR else c("33", "warn ")
            lines.append(f"  {tag} [{i.code}] {loc}: {i.message}")
    n_err = sum(len(r.errors) for r in results)
    n_warn = sum(len(r.warnings) for r in results)
    n_fail = sum(1 for r in results if not r.ok)
    lines.append("")
    lines.append(f"{len(results)} artifact(s) checked: {len(results) - n_fail} passed, {n_fail} failed, {n_err} error(s), {n_warn} warning(s).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate Shelf artifacts against spec/SPEC.md.")
    ap.add_argument("paths", nargs="*", help="artifact folders (default: every folder in --artifacts-dir)")
    ap.add_argument("--artifacts-dir", default=None, help="directory of artifacts (default: <repo>/artifacts)")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]
    artifacts_dir = Path(args.artifacts_dir) if args.artifacts_dir else repo / "artifacts"
    targets = [Path(p) for p in args.paths] if args.paths else discover(artifacts_dir)
    results = [validate_artifact(t) for t in targets]

    if args.json:
        print(json.dumps([
            {"slug": r.slug, "ok": r.ok, "draft": r.draft, "metadata": r.metadata,
             "issues": [i.to_dict() for i in r.issues]} for r in results
        ], indent=2))
    else:
        print(_format(results, color=sys.stdout.isatty()))

    failed = any(not r.ok for r in results) or (args.strict and any(r.warnings for r in results))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
