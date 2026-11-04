#!/usr/bin/env node
/* Draws the installed-app icons (artifacts/<slug>/icon.png, 512x512) for the artifacts below.
 *
 * Usage: node artifact-icons.cjs [slug ...]      (default: all)
 *
 * Each icon is full-bleed colour (so phones can round or crop it) with the drawing kept inside the
 * middle 80%. The PNGs are committed; this only needs to run when the artwork changes.
 */
const fs = require("node:fs")
const path = require("node:path")

const wedge = (cx, cy, r, a0, a1) => {
  const p = (a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)]
  const [x0, y0] = p(a0), [x1, y1] = p(a1)
  return `M${cx},${cy} L${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 0 1 ${x1.toFixed(1)},${y1.toFixed(1)} Z`
}
const wheel = Array.from({ length: 6 }, (_, i) => {
  const a0 = (i / 6) * Math.PI * 2 - Math.PI / 2 + 0.05, a1 = ((i + 1) / 6) * Math.PI * 2 - Math.PI / 2 + 0.05
  return `<path d="${wedge(256, 276, 168, a0, a1)}" fill="hsl(${i * 60 + 18} 78% 62%)" stroke="#1f1f1d" stroke-width="6" stroke-linejoin="round"/>`
}).join("")
const grid = Array.from({ length: 42 }, (_, i) => {
  const c = i % 7, r = Math.floor(i / 7), on = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 15, 16, 17, 19, 22, 23, 24, 26, 33, 34, 40].includes(i)
  const fill = !on ? "rgba(255,255,255,.22)" : [1, 3, 6, 8, 12, 17, 22, 24, 33, 40].includes(i) ? "#fcd34d" : "#ffffff"
  return `<rect x="${99 + c * 48}" y="${105 + r * 48}" width="38" height="38" rx="9" fill="${fill}"/>`
}).join("")

const ICONS = {
  "decision-wheel": ["#1f1f1d", `${wheel}<circle cx="256" cy="276" r="42" fill="#d9480f" stroke="#1f1f1d" stroke-width="8"/><path d="M226,86 L286,86 L256,142 Z" fill="#ffffff" stroke="#1f1f1d" stroke-width="6" stroke-linejoin="round"/>`],
  "star-wars-watch-order": ["#04060c", `${[[70, 90, 3], [430, 120, 2.5], [96, 410, 2], [420, 400, 3], [60, 250, 2], [452, 270, 2]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="#cbd5e1"/>`).join("")}
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fde68a"/><stop offset="1" stop-color="#b45309"/></linearGradient></defs>
    <polygon points="256,86 398,256 256,426 114,256" fill="url(#g)"/>
    <polygon points="256,150 340,256 256,362 172,256" fill="none" stroke="#04060c" stroke-opacity=".55" stroke-width="10" stroke-linejoin="round"/>
    <path d="M256,86 L256,426 M114,256 L398,256" stroke="#04060c" stroke-opacity=".35" stroke-width="8"/><circle cx="256" cy="256" r="22" fill="#04060c" fill-opacity=".7"/>`],
  "json-explorer": ["#2f6fed", `<g fill="none" stroke="#ffffff" stroke-width="26" stroke-linecap="round" stroke-linejoin="round">
    <path d="M196,110 C150,110 156,170 156,214 C156,242 140,256 118,256 C140,256 156,270 156,298 C156,342 150,402 196,402"/>
    <path d="M316,110 C362,110 356,170 356,214 C356,242 372,256 394,256 C372,256 356,270 356,298 C356,342 362,402 316,402"/></g>
    <g fill="#ffffff"><circle cx="226" cy="256" r="15"/><circle cx="256" cy="256" r="15"/><circle cx="286" cy="256" r="15"/></g>`],
  "168-hours": ["#0f766e", grid],
  "review-queue": ["#6d3fd8", `<rect x="138" y="96" width="236" height="300" rx="34" fill="#ffffff" fill-opacity=".28" transform="rotate(-9 256 256)"/>
    <rect x="138" y="108" width="236" height="300" rx="34" fill="#ffffff" fill-opacity=".5" transform="rotate(5 256 256)"/>
    <rect x="130" y="116" width="252" height="300" rx="34" fill="#ffffff"/>
    <path d="M196,274 L240,318 L318,226" fill="none" stroke="#6d3fd8" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>`],
  "pomodoro-timer": ["#d64933", `<circle cx="256" cy="268" r="140" fill="none" stroke="#ffffff" stroke-opacity=".3" stroke-width="40"/>
    <circle cx="256" cy="268" r="140" fill="none" stroke="#ffffff" stroke-width="40" stroke-linecap="round" stroke-dasharray="660 880" transform="rotate(-90 256 268)"/>
    <path d="M256,268 L256,196" stroke="#ffffff" stroke-width="26" stroke-linecap="round"/><path d="M232,110 C240,70 280,64 300,84 C270,84 256,100 256,120 Z" fill="#9be07a"/>`],
  "snake-game": ["#1f3a26", `<path d="M120,380 L120,300 Q120,260 160,260 L300,260 Q344,260 344,216 L344,170 Q344,130 304,130 L206,130" fill="none" stroke="#7bd88f" stroke-width="54" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="206" cy="130" r="8" fill="#1f3a26"/><circle cx="392" cy="372" r="30" fill="#ff6b5e"/>`],
  "shelf-intro-slides": ["#3563e9", `<rect x="130" y="124" width="52" height="210" rx="12" fill="#fff"/><rect x="204" y="164" width="52" height="170" rx="12" fill="#fff" fill-opacity=".85"/>
    <rect x="278" y="114" width="52" height="220" rx="12" fill="#fff" transform="rotate(8 304 224)"/><rect x="118" y="364" width="276" height="26" rx="13" fill="#fff"/>`],
}

async function main() {
  const { chromium } = require("playwright")
  const want = process.argv.slice(2)
  const slugs = want.length ? want : Object.keys(ICONS)
  const browser = await chromium.launch(process.env.SHELF_CHROMIUM ? { executablePath: process.env.SHELF_CHROMIUM } : {})
  try {
    for (const slug of slugs) {
      if (!ICONS[slug]) throw new Error("no icon design for " + slug)
      const [bg, art] = ICONS[slug]
      const page = await browser.newPage({ viewport: { width: 512, height: 512 }, deviceScaleFactor: 1 })
      await page.setContent(`<!doctype html><style>*{margin:0}body{width:512px;height:512px;overflow:hidden}</style><svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><rect width="512" height="512" fill="${bg}"/>${art}</svg>`)
      const out = path.resolve(__dirname, "..", "..", "artifacts", slug, "icon.png")
      await page.screenshot({ path: out, type: "png", omitBackground: false })
      await page.close()
      console.log("wrote", path.relative(process.cwd(), out), fs.statSync(out).size + " bytes")
    }
  } finally {
    await browser.close()
  }
}
main().catch((e) => { console.error(e); process.exit(1) })
