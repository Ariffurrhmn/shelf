#!/usr/bin/env python3
"""Search and social-sharing files for the built site.

GitHub Pages is static, so JavaScript cannot set per-project <meta> tags for
crawlers. Instead the build writes them into real HTML files:

  * the gallery's index.html gets absolute canonical / Open Graph URLs;
  * every short-link redirect page carries Open Graph and Twitter tags for its
    artifact (title, description, thumbnail), so sharing a short link shows a
    proper card, and then redirects humans to the artifact;
  * robots.txt and sitemap.xml are generated from the real artifact list.
"""

from __future__ import annotations

import html
import re
from datetime import date

html_escape = lambda s: html.escape(s, quote=True)  # noqa: E731

BASE_PLACEHOLDER = "__SHELF_BASE_URL__"
SITE_IMAGE = "og.png"


def absolute(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def inject_site_urls(index_html: str, base: str) -> str:
    """Fill the base-URL placeholder used by gallery/index.html."""
    return index_html.replace(BASE_PLACEHOLDER, base.rstrip("/") + "/")


GALLERY_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'"
)


def inject_gallery_csp(index_html: str) -> str:
    """Add a Content-Security-Policy to the gallery page (not in dev, where Vite needs inline scripts).

    The gallery has no inline scripts and loads nothing from other origins, so the policy is strict."""
    tag = f'<meta http-equiv="Content-Security-Policy" content="{GALLERY_CSP}">'
    return index_html.replace("<head>", "<head>\n    " + tag, 1) if "Content-Security-Policy" not in index_html else index_html


def share_tags(*, title: str, description: str, url: str, image: str, kind: str = "article", with_description: bool = True) -> str:
    """Open Graph + Twitter card tags (already HTML-escaped)."""
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    return "\n".join(
        [
            f'<meta property="og:type" content="{kind}">',
            '<meta property="og:site_name" content="Shelf">',
            f'<meta property="og:title" content="{e(title)}">',
            f'<meta property="og:description" content="{e(description)}">',
            f'<meta property="og:url" content="{e(url)}">',
            f'<meta property="og:image" content="{e(image)}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{e(title)}">',
            f'<meta name="twitter:description" content="{e(description)}">',
            f'<meta name="twitter:image" content="{e(image)}">',
            *([f'<meta name="description" content="{e(description)}">'] if with_description else []),
        ]
    )


def artifact_head_tags(html: str, *, title: str, description: str, url: str, image: str) -> str:
    """Canonical + Open Graph + Twitter tags for an artifact page, skipping what the author already set.

    The artifact is the page people share (its short address), and crawlers do not run JavaScript,
    so the tags have to be in the served HTML itself."""
    if 'property="og:title"' in html or "property='og:title'" in html:
        return ""
    has_description = bool(re.search(r"<meta[^>]+name=[\"']description[\"']", html, re.I))
    tags = share_tags(title=title, description=description, url=url, image=image, with_description=not has_description)
    if not re.search(r"<link[^>]+rel=[\"']canonical[\"']", html, re.I):
        tags += f'\n<link rel="canonical" href="{html_escape(url)}">'
    return tags + "\n"


def robots_txt(base: str) -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {absolute(base, 'sitemap.xml')}\n"


def sitemap_xml(base: str, entries: list[dict]) -> str:
    """Home page plus each published artifact. Short-link redirect pages are left out on purpose."""
    urls = [(absolute(base, ""), date.today().isoformat())]
    for e in entries:
        urls.append((absolute(base, e["url"]), e.get("updated") or e["created"]))
    body = "\n".join(
        f"  <url><loc>{html.escape(loc)}</loc><lastmod>{lastmod}</lastmod></url>" for loc, lastmod in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n"
    )
