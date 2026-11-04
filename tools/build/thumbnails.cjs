#!/usr/bin/env node
/* Generates a WebP thumbnail pair per artifact with Playwright.
 *
 * Usage: node thumbnails.cjs <site-dir> <jobs.json>
 *
 * jobs.json: { "cache": "<dir>", "items": [ { "slug": "...", "override": "cover.png" | null,
 *                                              "allowHosts": ["cdn.jsdelivr.net", ...] } ] }
 *
 * Reads   <site-dir>/artifacts/<slug>/            (the already-built copy)
 * Writes  <site-dir>/thumbnails/<slug>-<hash>.webp          1280x800
 *         <site-dir>/thumbnails/<slug>-<hash>-640.webp       640x400
 *         <site-dir>/thumbnails/index.json                   { slug: { src, small, width, height } }
 *
 * Properties:
 *  - Artifacts are loaded from a local HTTP server (as on the real site), not file://.
 *  - Every request is intercepted: only the local server, data:/blob: URLs and the
 *    artifact's approved hosts are allowed. Everything else is aborted.
 *  - A page is captured once it has loaded, fonts are ready and two consecutive
 *    screenshots are identical (or a short limit is hit, for animated pages).
 *  - Blank (uniform) screenshots are rejected, so the gallery shows its placeholder instead.
 *  - A "thumbnail" file named in the artifact's metadata replaces the screenshot but goes
 *    through the same resize, so every thumbnail has the same size and format.
 *  - Results are cached by content hash, so unchanged artifacts are not re-rendered.
 *
 * Thumbnails are best effort: a failure on one artifact is reported and skipped.
 */
const crypto = require("node:crypto")
const fs = require("node:fs")
const path = require("node:path")

const { serve } = require("./lib/serve.cjs")

const VERSION = "3" // bump to invalidate every cached thumbnail
const FULL = { w: 1280, h: 800 }
const SMALL = { w: 640, h: 400 }
const SETTLE_TRIES = 5
const SETTLE_MS = 250

function hashFolder(dir, extra) {
  const h = crypto.createHash("sha256")
  h.update(VERSION + "\0" + extra + "\0")
  const walk = (d) => {
    for (const name of fs.readdirSync(d).sort()) {
      const p = path.join(d, name)
      const st = fs.lstatSync(p)
      if (st.isDirectory()) walk(p)
      else if (st.isFile()) h.update(path.relative(dir, p).split(path.sep).join("/") + "\0").update(fs.readFileSync(p))
    }
  }
  walk(dir)
  return h.digest("hex").slice(0, 10)
}

/** Resizes inside the browser: cover-fit to 8:5 anchored at the top, WebP out, plus a blank check. */
async function encode(helper, pngBase64, mime) {
  return helper.evaluate(
    async ({ b64, mime, FULL, SMALL }) => {
      const img = new Image()
      img.src = `data:${mime};base64,${b64}`
      await img.decode()
      const draw = (size) => {
        const c = document.createElement("canvas")
        c.width = size.w
        c.height = size.h
        const g = c.getContext("2d")
        g.fillStyle = "#fff"
        g.fillRect(0, 0, size.w, size.h)
        g.imageSmoothingQuality = "high"
        const scale = Math.max(size.w / img.width, size.h / img.height)
        const w = img.width * scale
        const h = img.height * scale
        g.drawImage(img, (size.w - w) / 2, 0, w, h) // top-anchored: headers and titles stay visible
        return c
      }
      const full = draw(FULL)
      const small = draw(SMALL)
      const probe = document.createElement("canvas")
      probe.width = 64
      probe.height = 40
      const pg = probe.getContext("2d")
      pg.drawImage(full, 0, 0, 64, 40)
      const px = pg.getImageData(0, 0, 64, 40).data
      let sum = 0
      let sumSq = 0
      const n = px.length / 4
      for (let i = 0; i < px.length; i += 4) {
        const l = 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]
        sum += l
        sumSq += l * l
      }
      const mean = sum / n
      const stddev = Math.sqrt(Math.max(0, sumSq / n - mean * mean))
      return {
        full: full.toDataURL("image/webp", 0.84).split(",")[1],
        small: small.toDataURL("image/webp", 0.82).split(",")[1],
        stddev,
      }
    },
    { b64: pngBase64, mime, FULL, SMALL }
  )
}

async function screenshot(context, url) {
  const page = await context.newPage()
  try {
    await page.goto(url, { waitUntil: "load", timeout: 20000 })
    await page.evaluate(() => (document.fonts ? document.fonts.ready.then(() => undefined) : undefined)).catch(() => {})
    await page.waitForLoadState("networkidle", { timeout: 4000 }).catch(() => {})
    let prev = null
    let shot = null
    for (let i = 0; i < SETTLE_TRIES; i++) {
      await page.waitForTimeout(SETTLE_MS)
      shot = await page.screenshot({ type: "png", animations: "disabled", caret: "hide" })
      if (prev && prev.equals(shot)) break
      prev = shot
    }
    return shot
  } finally {
    await page.close()
  }
}

async function main() {
  const [siteDir, jobsFile] = process.argv.slice(2)
  if (!siteDir || !jobsFile) {
    console.error("usage: thumbnails.cjs <site-dir> <jobs.json>")
    process.exit(2)
  }
  const jobs = JSON.parse(fs.readFileSync(jobsFile, "utf8"))
  let chromium
  try {
    ;({ chromium } = require("playwright"))
  } catch (e) {
    console.error("playwright is not installed; skipping thumbnails (" + e.message + ")")
    process.exit(3)
  }
  const site = path.resolve(siteDir)
  const outDir = path.join(site, "thumbnails")
  const cacheDir = path.resolve(jobs.cache)
  fs.mkdirSync(outDir, { recursive: true })
  fs.mkdirSync(cacheDir, { recursive: true })

  const launchOpts = {}
  if (process.env.SHELF_CHROMIUM) launchOpts.executablePath = process.env.SHELF_CHROMIUM
  const server = await serve(site)
  const browser = await chromium.launch(launchOpts)
  const index = {}
  let rendered = 0
  let cached = 0
  try {
    const helper = await (await browser.newContext()).newPage()
    await helper.goto("about:blank")
    for (const item of jobs.items) {
      const { slug, override } = item
      const dir = path.join(site, "artifacts", slug)
      try {
        const hash = hashFolder(dir, String(override))
        const names = { src: `${slug}-${hash}.webp`, small: `${slug}-${hash}-640.webp` }
        const cacheFull = path.join(cacheDir, names.src)
        const cacheSmall = path.join(cacheDir, names.small)
        if (!(fs.existsSync(cacheFull) && fs.existsSync(cacheSmall))) {
          let png
          let mime = "image/png"
          if (override) {
            const file = path.join(dir, override)
            png = fs.readFileSync(file)
            mime = { ".png": "image/png", ".webp": "image/webp" }[path.extname(file).toLowerCase()] || "image/jpeg"
          } else {
            const allowed = new Set(item.allowHosts || [])
            const context = await browser.newContext({
              // 960x600 rendered at 4/3 gives a sharp 1280x800 image in which small apps
              // appear a third larger than at a 1280x800 viewport, so they stay readable on a card.
              viewport: { width: 960, height: 600 },
              deviceScaleFactor: FULL.w / 960,
              reducedMotion: "reduce",
              colorScheme: "light",
              serviceWorkers: "block",
              acceptDownloads: false,
              permissions: [],
            })
            try {
              await context.route("**/*", (route) => {
                const u = new URL(route.request().url())
                const ok =
                  u.origin === server.origin ||
                  u.protocol === "data:" ||
                  u.protocol === "blob:" ||
                  [...allowed].some((h) => u.hostname === h || u.hostname.endsWith("." + h))
                return ok ? route.continue() : route.abort("blockedbyclient")
              })
              context.on("page", async (p) => {
                if (await p.opener().catch(() => null)) await p.close().catch(() => {}) // close popups only
              })
              png = await screenshot(context, `${server.url}artifacts/${slug}/`)
            } finally {
              await context.close()
            }
          }
          const out = await encode(helper, png.toString("base64"), mime)
          if (out.stddev < 2) throw new Error(`blank (uniform) image, std dev ${out.stddev.toFixed(2)}`)
          fs.writeFileSync(cacheFull, Buffer.from(out.full, "base64"))
          fs.writeFileSync(cacheSmall, Buffer.from(out.small, "base64"))
          rendered++
          console.log(`thumbnail ok     ${slug}${override ? " (from " + override + ")" : ""}`)
        } else {
          cached++
          console.log(`thumbnail cached ${slug}`)
        }
        fs.copyFileSync(cacheFull, path.join(outDir, names.src))
        fs.copyFileSync(cacheSmall, path.join(outDir, names.small))
        index[slug] = { src: `thumbnails/${names.src}`, small: `thumbnails/${names.small}`, width: FULL.w, height: FULL.h }
      } catch (e) {
        console.warn(`thumbnail FAIL   ${slug}: ${String(e.message).split("\n")[0]}`)
      }
    }
  } finally {
    await browser.close()
    await server.close()
  }
  fs.writeFileSync(path.join(outDir, "index.json"), JSON.stringify(index, null, 2) + "\n")
  console.log(`${Object.keys(index).length}/${jobs.items.length} thumbnails ready (${rendered} rendered, ${cached} from cache)`)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
