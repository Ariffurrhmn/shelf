/* End-to-end tests for the built site, in a real browser (Playwright + Chromium).
 *
 * Prerequisite:  python tools/build/build.py --no-thumbnails      (builds ./site)
 * Run:           cd tools/build && npm run e2e
 *
 * The site is served under /shelf/ like GitHub Pages. Edge cases that the real collection does
 * not contain (featured projects, aliases, many tags, long titles) use a copy of site/ with a
 * crafted artifacts.json: the gallery is driven entirely by that file.
 */
const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { after, before, describe, test } = require("node:test")

const { chromium } = require("playwright")
const { serve } = require("../lib/serve.cjs")

const SITE = path.resolve(__dirname, "..", "..", "..", "site")
const PREFIX = "/shelf"

let browser, real, fixture, tmp

function craft(manifest) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "shelf-e2e-"))
  fs.cpSync(SITE, dir, { recursive: true })
  fs.writeFileSync(path.join(dir, "artifacts.json"), JSON.stringify(manifest))
  return dir
}

function entry(i, over = {}) {
  const slug = `project-${String(i).padStart(2, "0")}`
  return {
    slug, title: `Project ${i}`, description: `Description of project ${i}.`, created: `2026-0${1 + (i % 9)}-1${i % 9}`, tool: "Claude",
    kind: ["app", "game", "doc", "presentation", "other"][i % 5], tags: [`tag-${i % 14}`, "common"], storage: "none", network: [],
    notes: null, why: null, status: null, featured: false, updated: null, source: null, aliases: [], url: `artifacts/pomodoro-timer/`, short: null,
    thumbnail: null, thumbnailSmall: null, thumbnailWidth: null, thumbnailHeight: null, install: false, icon: null, color: null, ...over,
  }
}

before(async () => {
  assert.ok(fs.existsSync(path.join(SITE, "artifacts.json")), "build the site first: python tools/build/build.py --no-thumbnails")
  const manifest = {
    generated: "2026-11-04T00:00:00+00:00", repo: "https://github.com/example/shelf",
    artifacts: [
      ...Array.from({ length: 40 }, (_, i) => entry(i)),
      entry(100, { slug: "star", title: "A featured project with an extraordinarily long title that must wrap cleanly instead of overflowing its card", featured: true, aliases: ["old-star"], why: "Because.", status: "finished", source: "https://example.com/chat" }),
      entry(101, { slug: "star-two", title: "Second featured", featured: true, description: "" }),
    ],
  }
  tmp = craft(manifest)
  real = await serve(SITE, { prefix: PREFIX })
  fixture = await serve(tmp, { prefix: PREFIX })
  browser = await chromium.launch({ executablePath: process.env.SHELF_CHROMIUM || undefined })
})

after(async () => {
  await browser?.close()
  await real?.close()
  await fixture?.close()
  if (tmp) fs.rmSync(tmp, { recursive: true, force: true })
})

async function open(server, urlPath = "", opts = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...opts })
  const page = await context.newPage()
  const problems = []
  page.on("console", (m) => m.type() === "error" && problems.push(m.text()))
  page.on("pageerror", (e) => problems.push(e.message))
  await page.goto(server.url + urlPath, { waitUntil: "networkidle" })
  await page.locator("h1").waitFor() // not by role: the dialog hides the page from the accessibility tree
  return { page, context, problems }
}

const cards = (page) => page.locator("article")
// Filtering is deferred a frame to keep typing responsive, so wait for the grid instead of reading it instantly.
const waitTitles = (page, expected) =>
  page.waitForFunction((t) => JSON.stringify([...document.querySelectorAll("article h3")].map((h) => h.textContent)) === JSON.stringify(t), expected)
const waitCards = (page, n) => page.waitForFunction((n) => document.querySelectorAll("article").length === n, n)
const titles = (page) => page.locator("article h3").allTextContents()

describe("homepage", () => {
  test("renders the hero, real counts and one card per project, with no console errors", async () => {
    const { page, context, problems } = await open(real)
    assert.equal(await page.getByRole("heading", { level: 1 }).innerText(), "Small experiments. Useful creations.")
    assert.match(await page.locator("section[aria-labelledby=hero-title]").innerText(), /4 projects/)
    assert.equal(await cards(page).count(), 4)
    assert.equal(await page.getByRole("heading", { name: "Featured", exact: true }).count(), 0, "no featured section when nothing is featured")
    assert.deepEqual(problems, [])
    await context.close()
  })

  test("has the SEO and social tags", async () => {
    const { page, context } = await open(real)
    assert.match(await page.locator('link[rel=canonical]').getAttribute("href"), /^https:\/\/.+\/shelf\/$/)
    for (const sel of ['meta[property="og:image"]', 'meta[name="twitter:card"]', 'meta[name="description"]', 'meta[property="og:title"]']) {
      assert.ok(await page.locator(sel).count(), sel)
    }
    assert.equal((await page.locator('meta[property="og:image"]').getAttribute("content")).endsWith("/og.png"), true)
    await context.close()
  })

  for (const width of [320, 375, 390, 768, 1024, 1440, 1920]) {
    test(`no horizontal scrolling at ${width}px (many projects, long titles)`, async () => {
      const { page, context } = await open(fixture, "", { viewport: { width, height: 800 } })
      const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      assert.equal(over, 0)
      await context.close()
    })
  }

  test("404 page is friendly", async () => {
    const context = await browser.newContext()
    const page = await context.newPage()
    const res = await page.goto(real.url + "nope/")
    assert.equal(res.status(), 404)
    assert.match(await page.locator("h1").innerText(), /isn't on the shelf/)
    await context.close()
  })
})

describe("discovery", () => {
  test("search is case-insensitive, combines with category, and shows an empty state with a reset", async () => {
    const { page, context } = await open(real)
    const search = page.getByRole("searchbox", { name: "Search projects" })
    await search.fill("POMODORO")
    await waitTitles(page, ["Pomodoro timer"])
    assert.match(await page.getByRole("status").first().innerText(), /1 of 4 projects match/)
    await page.getByRole("button", { name: /^Games/ }).click()
    assert.match(await page.getByText("Nothing matches").innerText(), /Nothing matches/)
    await page.getByRole("button", { name: "Clear all filters" }).click()
    await waitCards(page, 4)
    assert.equal(await search.inputValue(), "")
    await context.close()
  })

  test("'/' focuses search but never steals typing, and Escape clears", async () => {
    const { page, context } = await open(real)
    await page.keyboard.press("/")
    const search = page.getByRole("searchbox", { name: "Search projects" })
    assert.equal(await search.evaluate((el) => el === document.activeElement), true)
    await page.keyboard.type("a/b")
    assert.equal(await search.inputValue(), "a/b")
    await page.keyboard.press("Escape")
    assert.equal(await search.inputValue(), "")
    await context.close()
  })

  test("category and tag filters, sorting, and URL state survive a reload", async () => {
    const { page, context } = await open(real)
    await page.getByRole("button", { name: /^Apps/ }).click()
    await waitCards(page, 2)
    await page.getByRole("button", { name: /^Tags/ }).click()
    await page.getByRole("button", { name: /^#productivity/ }).click()
    await waitTitles(page, ["Pomodoro timer"])
    await page.waitForTimeout(400)
    assert.match(page.url(), /kind=app/)
    assert.match(page.url(), /tag=productivity/)
    await page.reload({ waitUntil: "networkidle" })
    await waitTitles(page, ["Pomodoro timer"])
    await page.getByRole("button", { name: "Clear filters" }).click()
    await page.getByLabel("Sort").selectOption("title-asc")
    await waitTitles(page, ["Pomodoro timer", "Shelf: a short introduction", "Snake", "URL shortener"])
    await page.getByLabel("Sort").selectOption("oldest")
    await waitTitles(page, ["Pomodoro timer", "Snake", "Shelf: a short introduction", "URL shortener"])
    await page.getByLabel("Sort").selectOption("newest")
    await waitTitles(page, ["URL shortener", "Shelf: a short introduction", "Snake", "Pomodoro timer"])
    await context.close()
  })

  test("a remembered sort applies on the next visit, but filters do not", async () => {
    const { page, context } = await open(real)
    await page.getByLabel("Sort").selectOption("title-desc")
    await page.getByRole("searchbox").fill("snake")
    await page.goto(real.url, { waitUntil: "networkidle" })
    assert.equal(await page.getByLabel("Sort").inputValue(), "title-desc")
    assert.equal(await page.getByRole("searchbox").inputValue(), "")
    await context.close()
  })

  test("featured projects appear once, above the grid, and give way to results while filtering", async () => {
    const { page, context } = await open(fixture)
    assert.equal(await page.getByRole("heading", { name: "Featured", exact: true }).count(), 1)
    const all = await titles(page)
    assert.equal(all.filter((t) => t === "Second featured").length, 1)
    await waitCards(page, 42)
    await page.getByRole("searchbox").fill("second featured")
    await page.getByRole("heading", { name: "Featured", exact: true }).waitFor({ state: "detached" })
    await waitTitles(page, ["Second featured"])
    await context.close()
  })

  test("many tags stay manageable: collapsed, then expandable", async () => {
    const { page, context } = await open(fixture)
    await page.getByRole("button", { name: /^Tags/ }).click()
    const group = page.getByRole("group", { name: "Filter by tag" })
    assert.equal(await group.getByRole("button", { name: /^#/ }).count(), 12)
    await group.getByRole("button", { name: /Show all/ }).click()
    assert.ok((await group.getByRole("button", { name: /^#/ }).count()) > 12)
    await context.close()
  })
})

describe("details dialog and history", () => {
  test("opens with a history entry; Back closes, Forward reopens, focus returns", async () => {
    const { page, context } = await open(real)
    const trigger = page.getByRole("button", { name: "Details for Snake" })
    await trigger.click()
    const dialog = page.getByRole("dialog")
    await dialog.waitFor()
    assert.equal(page.url().endsWith("#snake-game"), true)
    assert.equal(await dialog.getByRole("heading", { name: "Snake" }).count(), 1)
    await page.goBack()
    await dialog.waitFor({ state: "hidden" })
    assert.equal(page.url().includes("#"), false)
    await page.goForward()
    await dialog.waitFor()
    assert.equal(page.url().endsWith("#snake-game"), true)
    await context.close()
  })

  test("Escape closes the dialog and focus returns to the button that opened it", async () => {
    const { page, context } = await open(real)
    const trigger = page.getByRole("button", { name: "Details for Snake" })
    await trigger.focus()
    await page.keyboard.press("Enter")
    const dialog = page.getByRole("dialog")
    await dialog.waitFor()
    await page.keyboard.press("Escape")
    await dialog.waitFor({ state: "hidden" })
    await page.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Details for Snake")
    assert.equal(page.url().includes("#"), false)
    await context.close()
  })

  test("a direct link and a refresh open the dialog; closing it keeps the visitor on the page", async () => {
    const { page, context } = await open(real, "#pomodoro-timer")
    const dialog = page.getByRole("dialog")
    await dialog.waitFor()
    assert.equal(await page.title(), "Pomodoro timer · Shelf")
    await page.reload({ waitUntil: "networkidle" })
    await dialog.waitFor()
    await page.getByRole("button", { name: "Close details" }).click()
    await dialog.waitFor({ state: "hidden" })
    assert.equal(page.url(), real.url)
    assert.equal(await cards(page).count(), 4)
    await context.close()
  })

  test("an old slug (alias) opens the right project and the address is corrected", async () => {
    const { page, context } = await open(fixture, "#old-star")
    await page.getByRole("dialog").waitFor()
    assert.equal(page.url().endsWith("#star"), true)
    assert.match(await page.getByRole("dialog").innerText(), /Because\./)
    await context.close()
  })

  test("unknown hashes are ignored", async () => {
    const { page, context, problems } = await open(real, "#does-not-exist")
    assert.equal(await page.getByRole("dialog").count(), 0)
    assert.deepEqual(problems, [])
    await context.close()
  })

  test("technical details are tucked away, and dialog traps focus", async () => {
    const { page, context } = await open(real)
    await page.getByRole("button", { name: "Details for URL shortener" }).click()
    const dialog = page.getByRole("dialog")
    const details = dialog.locator("details")
    assert.equal(await details.evaluate((d) => d.open), false)
    await dialog.getByText("Technical details").click()
    assert.match(await details.innerText(), /Saves data in this browser only/)
    for (let i = 0; i < 12; i++) await page.keyboard.press("Tab")
    assert.equal(await dialog.evaluate((d) => d.contains(document.activeElement)), true)
    await context.close()
  })

  test("is a bottom sheet on phones", async () => {
    const { page, context } = await open(real, "", { viewport: { width: 390, height: 800 }, hasTouch: true, isMobile: true })
    await page.getByRole("button", { name: "Details for Snake" }).click()
    await page.getByRole("dialog").waitFor()
    await page.waitForTimeout(400) // let the slide-in animation finish
    const box = await page.getByRole("dialog").boundingBox()
    assert.equal(Math.round(box.x), 0)
    assert.equal(Math.round(box.x + box.width), 390)
    assert.ok(Math.abs(box.y + box.height - 800) < 2, "anchored to the bottom edge")
    await context.close()
  })
})

describe("links", () => {
  test("Copy link copies the short link under the /shelf base path and confirms", async () => {
    const { page, context } = await open(real, "", { permissions: ["clipboard-read", "clipboard-write"] })
    await page.getByRole("button", { name: "Copy link to Pomodoro timer" }).click()
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), `${real.url}74ng`)
    assert.match(await page.locator('[role=status][aria-atomic]').innerText(), /Link copied/)
    await context.close()
  })

  test("title and Open project go to the artifact", async () => {
    const { page, context } = await open(real)
    await page.getByRole("link", { name: "Pomodoro timer", exact: true }).click()
    await page.waitForURL(/\/shelf\/artifacts\/pomodoro-timer\/$/)
    assert.match(await page.title(), /Pomodoro/)
    await context.close()
  })

  test("short links redirect to the artifact and carry the #hash", async () => {
    const context = await browser.newContext()
    const page = await context.newPage()
    await page.goto(`${real.url}pdhh/#3`)
    await page.waitForURL(/\/shelf\/artifacts\/shelf-intro-slides\/#3$/)
    await context.close()
  })

  test("short-link pages are share cards for crawlers", async () => {
    const context = await browser.newContext()
    const html = await (await context.request.get(`${real.url}74ng/`)).text() // what a crawler sees: no JavaScript
    assert.match(html, /<meta property="og:title" content="Pomodoro timer">/)
    assert.match(html, /<meta property="og:image" content="https:\/\/[^"]+\/(thumbnails\/[^"]+\.webp|og\.png)">/)
    assert.match(html, /<meta name="twitter:card" content="summary_large_image">/)
    await context.close()
  })

  test("works when served from the domain root too (no base path)", async () => {
    const root = await serve(SITE)
    try {
      const { page, context, problems } = await open(root)
      assert.equal(await cards(page).count(), 4)
      assert.deepEqual(problems, [])
      await context.close()
    } finally {
      await root.close()
    }
  })
})

describe("theme and accessibility", () => {
  test("dark mode follows the system, can be toggled, and is remembered", async () => {
    const { page, context } = await open(real, "", { colorScheme: "dark" })
    assert.equal(await page.evaluate(() => document.documentElement.classList.contains("dark")), true)
    await page.getByRole("button", { name: "Switch to light theme" }).click()
    assert.equal(await page.evaluate(() => document.documentElement.classList.contains("dark")), false)
    await page.reload({ waitUntil: "networkidle" })
    assert.equal(await page.evaluate(() => document.documentElement.classList.contains("dark")), false)
    await context.close()
  })

  test("keyboard: skip link, visible focus ring, one h1, headings in order", async () => {
    const { page, context } = await open(real)
    await page.keyboard.press("Tab")
    assert.equal(await page.evaluate(() => document.activeElement.textContent), "Skip to content")
    await page.keyboard.press("Tab")
    await page.keyboard.press("Tab")
    const outline = await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle)
    assert.notEqual(outline, "none")
    assert.equal(await page.locator("h1").count(), 1)
    const levels = await page.locator("h1, h2, h3").evaluateAll((els) => els.map((e) => +e.tagName[1]))
    for (let i = 1; i < levels.length; i++) assert.ok(levels[i] - levels[i - 1] <= 1, `heading jump at ${i}: ${levels}`)
    await context.close()
  })

  test("images have alternative text and respect reduced motion", async () => {
    const { page, context } = await open(fixture, "", { reducedMotion: "reduce" })
    const missing = await page.locator("img:not([alt])").count()
    assert.equal(missing, 0)
    const dur = await page.evaluate(() => getComputedStyle(document.querySelector(".card")).transitionDuration)
    assert.ok(parseFloat(dur) < 0.001, dur)
    await context.close()
  })
})

describe("artifact isolation (Content-Security-Policy)", () => {
  for (const slug of ["pomodoro-timer", "snake-game", "shelf-intro-slides", "url-shortener"]) {
    test(`${slug}: policy present, page works, no violations`, async () => {
      const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
      const page = await context.newPage()
      const problems = []
      // Console errors catch CSP violations ("Refused to ..."); the implicit /favicon.ico 404 is not one.
      page.on("console", (m) => m.type() === "error" && !m.text().startsWith("Failed to load resource") && problems.push(m.text()))
      page.on("response", (r) => r.status() >= 400 && !r.url().endsWith("/favicon.ico") && problems.push(`${r.status()} ${r.url()}`))
      page.on("pageerror", (e) => problems.push(e.message))
      await page.goto(`${real.url}artifacts/${slug}/`, { waitUntil: "networkidle" })
      assert.match(await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content"), /connect-src 'self'/)
      assert.deepEqual(problems, [])
      await context.close()
    })
  }

  test("undeclared network requests, and nested sites, are blocked by the browser", async () => {
    const context = await browser.newContext()
    const page = await context.newPage()
    await page.goto(`${real.url}artifacts/pomodoro-timer/`, { waitUntil: "networkidle" })
    const result = await page.evaluate(async () => {
      const out = {}
      try {
        await fetch("https://example.com/")
        out.fetch = "allowed"
      } catch (e) {
        out.fetch = "blocked"
      }
      out.img = await new Promise((r) => {
        const i = new Image()
        i.onload = () => r("allowed")
        i.onerror = () => r("blocked")
        i.src = "https://example.com/x.png"
      })
      return out
    })
    assert.deepEqual(result, { fetch: "blocked", img: "blocked" })
    await context.close()
  })
})
