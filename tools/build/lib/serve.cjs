/* Tiny static file server used by the thumbnail step and the end-to-end tests.
 *
 * serve(root, { prefix: "/shelf", port: 0 }) serves `root` under an optional
 * URL prefix, which is how GitHub Pages project sites are laid out. Only files
 * inside `root` are reachable. Binds to 127.0.0.1 only.
 */
const fs = require("node:fs")
const http = require("node:http")
const path = require("node:path")

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
}

function serve(root, { prefix = "", port = 0 } = {}) {
  const base = path.resolve(root)
  prefix = prefix.replace(/\/+$/, "")
  const server = http.createServer((req, res) => {
    let pathname
    try {
      pathname = decodeURIComponent(new URL(req.url, "http://x").pathname)
    } catch {
      res.writeHead(400).end("bad request")
      return
    }
    if (prefix) {
      if (pathname === prefix) {
        res.writeHead(301, { Location: prefix + "/" }).end()
        return
      }
      if (!pathname.startsWith(prefix + "/")) {
        res.writeHead(404).end("not found")
        return
      }
      pathname = pathname.slice(prefix.length)
    }
    let file = path.join(base, pathname)
    if (file !== base && !file.startsWith(base + path.sep)) {
      res.writeHead(403).end("forbidden")
      return
    }
    try {
      if (fs.statSync(file).isDirectory()) {
        if (!pathname.endsWith("/")) {
          res.writeHead(301, { Location: (prefix + pathname) + "/" }).end()
          return
        }
        file = path.join(file, "index.html")
      }
      const body = fs.readFileSync(file)
      res.writeHead(200, {
        "Content-Type": TYPES[path.extname(file).toLowerCase()] || "application/octet-stream",
        "Cache-Control": "no-store",
      })
      res.end(body)
    } catch {
      const notFound = path.join(base, "404.html")
      res.writeHead(404, { "Content-Type": "text/html; charset=utf-8" })
      res.end(fs.existsSync(notFound) ? fs.readFileSync(notFound) : "not found")
    }
  })
  return new Promise((resolve, reject) => {
    server.once("error", reject)
    server.listen(port, "127.0.0.1", () => {
      const { port: p } = server.address()
      resolve({ server, port: p, origin: `http://127.0.0.1:${p}`, url: `http://127.0.0.1:${p}${prefix}/`, close: () => new Promise((r) => { server.close(r); server.closeAllConnections() }) })
    })
  })
}

module.exports = { serve }
