#!/usr/bin/env node
/* Renders the site-level social preview (og.png, 1200x630) and the apple-touch-icon.
 *
 * Usage: node og.cjs            (writes into gallery/public/)
 *
 * The images are committed, so this only needs to run when the branding changes. It needs
 * `npm ci` in gallery/ (for the fonts) and in tools/build/ (for Playwright).
 */
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { pathToFileURL } = require("node:url")

const root = path.resolve(__dirname, "..", "..")
const fonts = path.join(root, "gallery", "node_modules", "@fontsource-variable")
const font = (pkg, file) => pathToFileURL(path.join(fonts, pkg, "files", file)).href

const mark = (size, radius = 14) => `
<svg viewBox="0 0 64 64" width="${size}" height="${size}">
  <rect width="64" height="64" rx="${radius}" fill="#3563e9"/>
  <rect x="14" y="14" width="8" height="30" rx="2" fill="#fff"/>
  <rect x="26" y="20" width="8" height="24" rx="2" fill="#fff" opacity=".85"/>
  <rect x="38" y="12" width="8" height="32" rx="2" fill="#fff" transform="rotate(8 42 28)"/>
  <rect x="12" y="48" width="40" height="4" rx="2" fill="#fff"/>
</svg>`

const css = `
@font-face { font-family: SG; src: url(${font("space-grotesk", "space-grotesk-latin-wght-normal.woff2")}); font-weight: 300 700; }
@font-face { font-family: GS; src: url(${font("geist", "geist-latin-wght-normal.woff2")}); font-weight: 100 900; }
* { box-sizing: border-box; margin: 0; }
body { width: 1200px; height: 630px; background: #fafaf8; color: #171717; font-family: GS, sans-serif; position: relative; overflow: hidden; }
.eyebrow { font: 500 20px ui-monospace, Menlo, monospace; letter-spacing: .16em; text-transform: uppercase; color: #3563e9; }
h1 { font: 600 104px/1.02 SG, sans-serif; letter-spacing: -.03em; margin-top: 28px; }
h1 span { color: #5b5e66; }
.brand { position: absolute; left: 80px; bottom: 72px; display: flex; align-items: center; gap: 18px; font: 600 38px SG, sans-serif; }
.url { position: absolute; right: 80px; bottom: 80px; font: 500 22px ui-monospace, Menlo, monospace; color: #5b5e66; }
.content { position: absolute; left: 80px; top: 92px; right: 80px; }
.shelf { position: absolute; right: 80px; top: 80px; display: flex; align-items: flex-end; gap: 10px; height: 120px; }
.shelf i { display: block; width: 26px; border-radius: 5px; background: #171717; }
.line { position: absolute; left: 80px; right: 80px; bottom: 150px; height: 2px; background: #dcdbd4; }
`

const page = `<!doctype html><meta charset="utf-8"><style>${css}</style>
<div class="content"><div class="eyebrow">A personal digital playground</div><h1>Small experiments.<br><span>Useful creations.</span></h1></div>
<div class="shelf"><i style="height:96px"></i><i style="height:70px;background:#3563e9"></i><i style="height:120px"></i><i style="height:84px;background:#8a8d95"></i></div>
<div class="line"></div>
<div class="brand">${mark(56, 14)}<span>Shelf</span></div>
<div class="url">ariffurrhmn.github.io/shelf</div>`

const touch = `<!doctype html><meta charset="utf-8"><style>*{margin:0}body{width:180px;height:180px;background:#3563e9}</style>${mark(180, 0)}`

async function main() {
  const { chromium } = require("playwright")
  const launch = process.env.SHELF_CHROMIUM ? { executablePath: process.env.SHELF_CHROMIUM } : {}
  const browser = await chromium.launch(launch)
  const out = path.join(root, "gallery", "public")
  try {
    for (const [name, html, w, h] of [["og.png", page, 1200, 630], ["apple-touch-icon.png", touch, 180, 180]]) {
      const file = path.join(os.tmpdir(), `shelf-${name}.html`)
      fs.writeFileSync(file, html)
      const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 })
      await p.goto(pathToFileURL(file).href)
      await p.evaluate(() => document.fonts.ready)
      await p.screenshot({ path: path.join(out, name), type: "png" })
      await p.close()
      fs.unlinkSync(file)
      console.log("wrote gallery/public/" + name)
    }
  } finally {
    await browser.close()
  }
}
main().catch((e) => {
  console.error(e)
  process.exit(1)
})
