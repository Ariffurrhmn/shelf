#!/usr/bin/env python3
"""Runtime hardening for published artifacts.

Every artifact is served from the same origin as the gallery, so the browser
cannot keep one artifact's script away from another's (see docs/security.md).
What the build *can* do is make the metadata the artifact declares into a rule
the browser enforces: a Content-Security-Policy <meta> tag is added to the
served copy of each artifact so that

  * network requests (fetch, XHR, WebSocket, images, media, frames, forms) can
    only go to the artifact's own folder and the domains in its `network` field;
  * pinned CDN scripts, styles and fonts keep working (the validator already
    restricts those hosts);
  * plugins (<object>, <embed>) are off and <base> cannot be redirected.

This is a mitigation, not isolation: it does not stop a script from reading
shared storage or from navigating the page elsewhere. The source file is never
changed, only the copy in site/.
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "validate"))
import shelf_validate as sv  # noqa: E402

MARKER = "shelf-csp"


def _hosts(domains: list[str]) -> list[str]:
    out: list[str] = []
    for d in domains:
        out += [f"https://{d}", f"https://*.{d}"]
    return out


def policy(meta: dict) -> str:
    """The Content-Security-Policy string for one artifact's metadata."""
    network = [n.lower() for n in meta.get("network", []) or []]
    code_hosts = list(sv.ALLOWED_CDN_HOSTS) + list(sv.ALLOWED_FONT_HOSTS)
    declared = _hosts(network)
    ws = [f"wss://{d}" for d in network]
    cdn = [f"https://{h}" for h in code_hosts]
    directives = {
        "default-src": ["'none'"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'", "blob:", *cdn, *declared],
        "style-src": ["'self'", "'unsafe-inline'", *cdn, *declared],
        "font-src": ["'self'", "data:", *cdn, *declared],
        "img-src": ["'self'", "data:", "blob:", *declared],
        "media-src": ["'self'", "data:", "blob:", *declared],
        "connect-src": ["'self'", "data:", "blob:", *declared, *ws],
        "frame-src": ["'self'", "blob:", "data:", *declared],
        "worker-src": ["'self'", "blob:"],
        "manifest-src": ["'self'"],
        "form-action": ["'self'", *declared],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
    }
    return "; ".join(f"{name} {' '.join(values)}" for name, values in directives.items())


class _HeadStart(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.head_end: int | None = None
        self._line_starts: list[int] = [0]

    def feed(self, data: str) -> None:  # noqa: D102
        for m in re.finditer("\n", data):
            self._line_starts.append(m.end())
        super().feed(data)

    def handle_starttag(self, tag, attrs):
        if tag == "head" and self.head_end is None:
            line, col = self.getpos()
            text = self.get_starttag_text() or ""
            self.head_end = self._line_starts[line - 1] + col + len(text)


def inject_csp(html: str, meta: dict) -> str:
    """Return `html` with the policy as the first thing in <head> (before any script)."""
    p = _HeadStart()
    p.feed(html)
    p.close()
    if p.head_end is None:
        return html  # the validator requires a <head>; nothing to do without one
    tag = f'<meta http-equiv="Content-Security-Policy" content="{policy(meta)}" data-{MARKER}="1">'
    return html[: p.head_end] + tag + html[p.head_end :]


def harden_artifact(dest: Path, meta: dict) -> None:
    """Add the policy to <dest>/index.html (the served copy)."""
    entry = dest / "index.html"
    text = entry.read_text(encoding="utf-8")
    entry.write_text(inject_csp(text, meta), encoding="utf-8")
