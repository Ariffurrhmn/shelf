"""Turn a copied artifact folder into an installable, offline-capable PWA.

Runs in the build only, on the copy under <site>/artifacts/<slug>/. The source
under artifacts/ is never modified, and authors never write any of this
themselves (the validator still forbids service workers in artifact source).

For an artifact with `"install": true` it writes, next to index.html:

    manifest.webmanifest   app name, icons, scope and start URL
    icon-192.png           generated icon (also used as the apple-touch-icon)
    icon-512.png
    sw.js                  precaches every file; versioned by a content hash

and injects a small block before </head> of the copied index.html that links
the manifest, registers the service worker and, only when the URL hash is
#install, shows a one-off "Install" prompt.

Standard library only, like the rest of the tooling.
"""

from __future__ import annotations

import colorsys
import hashlib
import html as _html
import json
import math
import re
import struct
import zlib
from html.parser import HTMLParser
from pathlib import Path

MARKER = "shelf:pwa"
SW_FILE = "sw.js"
MANIFEST_FILE = "manifest.webmanifest"
ICON_SIZES = (192, 512)

# Hosts whose responses the service worker may cache at runtime. These are the
# approved, version-pinned CDNs plus Google Fonts (see spec section 2).
CACHEABLE_HOSTS = (
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
    "unpkg.com",
    "code.jquery.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)


class PwaError(Exception):
    """The artifact cannot be made installable (build should fail)."""


# --------------------------------------------------------------------------
# colour and icon
# --------------------------------------------------------------------------

def default_color(slug: str) -> str:
    """A stable, pleasant colour derived from the slug."""
    h = int.from_bytes(hashlib.sha256(slug.encode()).digest()[:2], "big") / 65535
    r, g, b = colorsys.hls_to_rgb(h, 0.38, 0.55)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _pattern(slug: str) -> list[list[bool]]:
    """A 5x5 left-right symmetric pattern, stable per slug (identicon style)."""
    bits = int.from_bytes(hashlib.sha256(("icon:" + slug).encode()).digest()[:4], "big")
    grid = [[False] * 5 for _ in range(5)]
    for row in range(5):
        for col in range(3):
            on = bool((bits >> (row * 3 + col)) & 1)
            grid[row][col] = grid[row][4 - col] = on
    if sum(map(sum, grid)) < 7:  # avoid near-empty icons
        for row in range(5):
            grid[row][2] = True
    return grid


def icon_png(size: int, slug: str, color: str) -> bytes:
    """Square PNG: solid colour with a light 5x5 pattern kept inside the maskable safe zone."""
    bg = _rgb(color)
    lum = 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]
    fg = (255, 255, 255) if lum < 160 else (20, 20, 20)
    grid = _pattern(slug)
    cell = max(1, int(size * 0.54 / 5))
    pad = (size - cell * 5) // 2

    rows = bytearray()
    for y in range(size):
        line = bytearray(b"\x00")  # filter type 0
        gy = (y - pad) // cell if pad <= y < pad + cell * 5 else -1
        for x in range(size):
            gx = (x - pad) // cell if pad <= x < pad + cell * 5 else -1
            on = gy >= 0 and gx >= 0 and grid[gy][gx]
            line += bytes(fg if on else bg)
        rows += line

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )


# --------------------------------------------------------------------------
# author-supplied icon: read a PNG, scale it to the sizes phones ask for
# --------------------------------------------------------------------------

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_header(data: bytes) -> dict:
    """Width, height, bit depth, colour type and interlacing of a PNG, or PwaError."""
    if data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise PwaError("The icon is not a PNG file.")
    w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", data[16:29])
    return {"width": w, "height": h, "depth": depth, "ctype": ctype, "interlace": interlace}


def png_problem(data: bytes) -> str | None:
    """Why this PNG cannot be used as an icon, or None. Shared with the validator."""
    try:
        hd = png_header(data)
    except (PwaError, struct.error):
        return "is not a PNG file"
    if hd["width"] != hd["height"]:
        return f"must be square, but is {hd['width']}x{hd['height']}"
    if hd["width"] < 512:
        return f"must be at least 512x512, but is {hd['width']}x{hd['height']}"
    if hd["depth"] != 8 or hd["ctype"] not in (2, 6) or hd["interlace"] != 0:
        return "must be a plain 8-bit RGB or RGBA PNG without interlacing (re-save it as PNG-24)"
    return None


def decode_png(data: bytes) -> tuple[int, int, int, list[bytearray]]:
    """Decode an 8-bit RGB/RGBA, non-interlaced PNG into (width, height, channels, rows)."""
    problem = png_problem(data)
    if problem and not problem.startswith("must be at least") and not problem.startswith("must be square"):
        raise PwaError(f"The icon {problem}.")
    hd = png_header(data)
    pos, idat = 8, bytearray()
    while pos + 8 <= len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
    w, h, ch = hd["width"], hd["height"], 3 if hd["ctype"] == 2 else 4
    stride = w * ch
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        raise PwaError("The icon PNG is damaged.") from None
    if len(raw) != h * (stride + 1):
        raise PwaError("The icon PNG is damaged (unexpected size).")
    rows, prev = [], bytearray(stride)
    for y in range(h):
        off = y * (stride + 1)
        ft, line = raw[off], bytearray(raw[off + 1:off + 1 + stride])
        if ft == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 255
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                line[i] = (line[i] + (((line[i - ch] if i >= ch else 0) + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a, b, c = (line[i - ch] if i >= ch else 0), prev[i], (prev[i - ch] if i >= ch else 0)
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif ft != 0:
            raise PwaError("The icon PNG uses an unknown filter.")
        rows.append(line)
        prev = line
    return w, h, ch, rows


def encode_png(size: int, ch: int, rows: list[bytearray]) -> bytes:
    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    return (PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2 if ch == 3 else 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _weights(src: int, dst: int) -> list[list[tuple[int, float]]]:
    """For each output pixel, the source pixels it covers and how much of each (box / area filter)."""
    scale, out = src / dst, []
    for i in range(dst):
        a, b = i * scale, (i + 1) * scale
        out.append([(j, (min(b, j + 1) - max(a, j)) / scale) for j in range(int(a), min(src, math.ceil(b)))])
    return out


def resize_square(w: int, ch: int, rows: list[bytearray], size: int) -> list[bytearray]:
    """Scale a square image down to size x size by averaging, which keeps small icons crisp."""
    wx, tmp = _weights(w, size), []
    for line in rows:
        out = [0.0] * (size * ch)
        for x, ws in enumerate(wx):
            for c in range(ch):
                out[x * ch + c] = sum(line[j * ch + c] * wt for j, wt in ws)
        tmp.append(out)
    res = []
    for ws in _weights(len(rows), size):
        res.append(bytearray(min(255, round(sum(tmp[j][k] * wt for j, wt in ws))) for k in range(size * ch)))
    return res


def icons_from_file(data: bytes) -> dict[int, bytes]:
    """{192: png, 512: png} from the author's 512+ pixel square PNG."""
    w, _h, ch, rows = decode_png(data)
    out = {}
    for size in ICON_SIZES:
        out[size] = data if (size == w) else encode_png(size, ch, resize_square(w, ch, rows, size))
    return out


# --------------------------------------------------------------------------
# manifest and service worker
# --------------------------------------------------------------------------

def build_manifest(meta: dict, color: str) -> dict:
    title = meta["title"]
    # No "id": it then defaults to the start URL, which is unique per artifact
    # and works under any base path (a relative id would resolve to the site root).
    return {
        "name": title,
        "short_name": title if len(title) <= 12 else title[:11].rstrip() + "…",
        "description": meta["description"],
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": color,
        "theme_color": color,
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }


_SW_TEMPLATE = """\
/* Generated by Shelf (tools/build/pwa.py). Do not edit. */
const CACHE = "shelf:%(slug)s:%(version)s";
const RUNTIME = "shelf:%(slug)s:runtime";
const PREFIX = "shelf:%(slug)s:";
const FILES = %(files)s;
const REMOTE = %(remote)s;

self.addEventListener("install", (event) => {
  // "reload" skips the HTTP cache so a new version is never built from stale files.
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES.map((f) => new Request(f, { cache: "reload" })))));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) {
        if (key.startsWith(PREFIX) && key !== CACHE && key !== RUNTIME) await caches.delete(key);
      }
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches
        .open(CACHE)
        .then((c) => c.match(req, { ignoreSearch: true }))
        .then((hit) => hit || fetch(req))
    );
  } else if (REMOTE.includes(url.hostname)) {
    // Pinned CDN files never change, so cache them on first use.
    event.respondWith(
      caches.open(RUNTIME).then(async (c) => {
        const hit = await c.match(req);
        if (hit) return hit;
        const res = await fetch(req);
        if (res.ok || res.type === "opaque") c.put(req, res.clone());
        return res;
      })
    );
  }
});
"""


def build_service_worker(slug: str, version: str, files: list[str]) -> str:
    return _SW_TEMPLATE % {
        "slug": slug,
        "version": version,
        "files": json.dumps(["./"] + files, indent=2),
        "remote": json.dumps(list(CACHEABLE_HOSTS)),
    }


# --------------------------------------------------------------------------
# HTML injection
# --------------------------------------------------------------------------

_INSTALL_JS = r"""
(function () {
  if (!("serviceWorker" in navigator)) return;
  addEventListener("load", function () {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  });
  var standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  if (standalone || location.hash !== "#install") return;

  var deferred = null, host = null;
  addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferred = e; render(); });
  addEventListener("appinstalled", remove);
  addEventListener("load", function () { setTimeout(render, 1200); });

  function remove() {
    if (host) host.remove();
    host = null;
    history.replaceState(null, "", location.pathname + location.search);
  }
  function render() {
    if (host) host.remove();
    host = document.createElement("div");
    var root = host.attachShadow({ mode: "open" });
    var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    var hint = ios ? "Tap Share, then Add to Home Screen." : "Use your browser menu and choose Install app or Add to Home Screen.";
    root.innerHTML =
      "<style>.b{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:2147483647;max-width:calc(100vw - 32px);" +
      "display:flex;gap:10px;align-items:center;padding:10px 12px;border-radius:12px;background:#1d1d1b;color:#fff;" +
      "font:14px/1.3 system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.35)}" +
      "button{font:inherit;border:0;border-radius:8px;padding:8px 12px;cursor:pointer}" +
      ".go{background:#fff;color:#1d1d1b;font-weight:600}.x{background:transparent;color:#fff;font-size:18px;padding:4px 8px}</style>" +
      '<div class="b" role="dialog" aria-label="Install app"><span></span></div>';
    var box = root.querySelector(".b"), label = root.querySelector("span");
    if (deferred) {
      var go = document.createElement("button");
      go.className = "go";
      go.textContent = "Install " + document.title;
      go.onclick = function () {
        deferred.prompt();
        deferred.userChoice.then(remove, remove);
      };
      box.replaceChild(go, label);
    } else {
      label.textContent = hint;
    }
    var x = document.createElement("button");
    x.className = "x";
    x.setAttribute("aria-label", "Dismiss");
    x.textContent = "×";
    x.onclick = remove;
    box.appendChild(x);
    document.body.appendChild(host);
  }
})();
"""


class _HeadEnd(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.pos: tuple[int, int] | None = None

    def handle_endtag(self, tag: str) -> None:
        if tag == "head" and self.pos is None:
            self.pos = self.getpos()


def head_end_offset(html: str) -> int | None:
    """Character offset of the </head> tag, found with a real parser (not a regex)."""
    p = _HeadEnd()
    p.feed(html)
    p.close()
    if p.pos is None:
        return None
    line, col = p.pos
    offset = 0
    for _ in range(line - 1):
        nl = html.find("\n", offset)
        if nl == -1:
            return None
        offset = nl + 1
    return offset + col


def inject(html: str, color: str, title: str | None = None) -> str:
    if MARKER in html:
        raise PwaError("index.html already contains the Shelf PWA block.")
    if re.search(r"<link[^>]+rel\s*=\s*[\"']?[^>]*\bmanifest\b", html, re.I):
        raise PwaError("index.html already links a web app manifest; remove it so the build can add its own.")
    at = head_end_offset(html)
    if at is None:
        raise PwaError("index.html has no </head> to add the PWA tags to.")
    theme = "" if re.search(r"<meta[^>]+name\s*=\s*[\"']?theme-color", html, re.I) else (
        f'<meta name="theme-color" content="{color}">\n'
    )
    short = ""
    if title:
        short = _html.escape(title if len(title) <= 12 else title[:11].rstrip() + "…", quote=True)
    ios = (  # iPhone and iPad: open from the Home Screen without browser chrome, with a proper label
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        + (f'<meta name="apple-mobile-web-app-title" content="{short}">\n' if short else "")
    )
    block = (
        f"<!-- {MARKER} (added by the build) -->\n"
        '<link rel="manifest" href="manifest.webmanifest">\n'
        '<link rel="apple-touch-icon" href="icon-192.png">\n'
        f"{ios}"
        f"{theme}"
        f"<script>{_INSTALL_JS.strip()}</script>\n"
    )
    return html[:at] + block + html[at:]


# --------------------------------------------------------------------------
# entry point used by build.py
# --------------------------------------------------------------------------

def version_of(folder: Path, exclude: tuple[str, ...] = (SW_FILE,)) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in folder.rglob("*") if x.is_file()):
        rel = p.relative_to(folder).as_posix()
        if rel in exclude:
            continue
        h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:10]


def make_installable(dest: Path, slug: str, meta: dict) -> None:
    """Write PWA files into the copied artifact folder `dest` and patch its index.html."""
    color = meta.get("color") or default_color(slug)
    index = dest / "index.html"
    index.write_text(inject(index.read_text(encoding="utf-8"), color, meta.get("title")), encoding="utf-8")
    icon = meta.get("icon")
    if icon:  # the author's own artwork, scaled to the sizes a phone asks for
        try:
            made = icons_from_file((dest / icon).read_bytes())
        except OSError:
            raise PwaError(f'the "icon" file {icon!r} cannot be read.') from None
        for size, png in made.items():
            (dest / f"icon-{size}.png").write_bytes(png)
    else:  # no artwork supplied: a generated pattern from the slug
        for size in ICON_SIZES:
            (dest / f"icon-{size}.png").write_bytes(icon_png(size, slug, color))
    (dest / MANIFEST_FILE).write_text(
        json.dumps(build_manifest(meta, color), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    files = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    files = [f for f in files if f != SW_FILE]
    (dest / SW_FILE).write_text(build_service_worker(slug, version_of(dest), files), encoding="utf-8")
