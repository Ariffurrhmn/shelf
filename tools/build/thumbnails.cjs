#!/usr/bin/env node
/* Generates a JPEG thumbnail per artifact with Playwright.
 *
 * Usage: node thumbnails.cjs <site-dir> <slug> [<slug> ...]
 *
 * Reads  <site-dir>/artifacts/<slug>/index.html
 * Writes <site-dir>/thumbnails/<slug>.jpg
 *
 * Thumbnails are best effort: a failure on one artifact is reported and
 * skipped, and the gallery falls back to a placeholder.
 */
const fs = require("node:fs")
const path = require("node:path")
const { pathToFileURL } = require("node:url")

async function main() {
  const [siteDir, ...slugs] = process.argv.slice(2)
  if (!siteDir || slugs.length === 0) {
    console.error("usage: thumbnails.cjs <site-dir> <slug> [<slug> ...]")
    process.exit(2)
  }
  let chromium
  try {
    ;({ chromium } = require("playwright"))
  } catch (e) {
    console.error("playwright is not installed; skipping thumbnails (" + e.message + ")")
    process.exit(3)
  }
  const outDir = path.join(siteDir, "thumbnails")
  fs.mkdirSync(outDir, { recursive: true })

  const launchOpts = { args: ["--no-sandbox"] }
  if (process.env.SHELF_CHROMIUM) launchOpts.executablePath = process.env.SHELF_CHROMIUM
  const browser = await chromium.launch(launchOpts)
  let made = 0
  try {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      deviceScaleFactor: 0.75,
      reducedMotion: "reduce",
      serviceWorkers: "block",
    })
    for (const slug of slugs) {
      const entry = path.resolve(siteDir, "artifacts", slug, "index.html")
      const page = await context.newPage()
      try {
        await page.goto(pathToFileURL(entry).href, { waitUntil: "load", timeout: 20000 })
        await page.waitForTimeout(600)
        await page.screenshot({ path: path.join(outDir, slug + ".jpg"), type: "jpeg", quality: 78 })
        made++
        console.log("thumbnail ok   " + slug)
      } catch (e) {
        console.warn("thumbnail FAIL " + slug + ": " + e.message.split("\n")[0])
      } finally {
        await page.close()
      }
    }
  } finally {
    await browser.close()
  }
  console.log(made + "/" + slugs.length + " thumbnails written")
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
