/* End-to-end tests for the interactive artifacts, run against the BUILT site so the real
 * Content-Security-Policy is in force. Prerequisite: python tools/build/build.py --no-thumbnails */
const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")
const { after, before, describe, test } = require("node:test")
const { chromium } = require("playwright")
const { serve } = require("../lib/serve.cjs")

const SITE = path.resolve(__dirname, "..", "..", "..", "site")
const manifest = () => JSON.parse(fs.readFileSync(path.join(SITE, "artifacts.json"), "utf8")).artifacts
let browser, server
const codeOf = (slug) => manifest().find((a) => a.slug === slug).short

before(async () => {
  server = await serve(SITE, { prefix: "/shelf" })
  browser = await chromium.launch({ executablePath: process.env.SHELF_CHROMIUM || undefined })
})
after(async () => { await browser?.close(); await server?.close() })

async function open(slug, opts = {}, query = "") {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...opts })
  const page = await context.newPage()
  const problems = []
  // Console errors include Content-Security-Policy violations; a missing /favicon.ico or a blocked web font is not one.
  page.on("console", (m) => m.type() === "error" && !m.text().startsWith("Failed to load resource") && problems.push(m.text()))
  page.on("pageerror", (e) => problems.push(e.message))
  await page.goto(`${server.url}${codeOf(slug)}/${query}`, { waitUntil: "load" })
  return { page, context, problems }
}
const fillRows = (page, n) => page.waitForFunction((n) => document.querySelectorAll("#tree [role=treeitem]").length === n, n)

describe("every new artifact", () => {
  for (const slug of ["star-wars-watch-order", "decision-wheel", "json-explorer", "168-hours", "premortem", "review-queue"]) {
    test(`${slug}: runs under its Content-Security-Policy, fits a phone, and has a title and one h1-level landmark`, async () => {
      const { page, context, problems } = await open(slug, { viewport: { width: 360, height: 780 }, hasTouch: true })
      assert.deepEqual(problems, [])
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), 0, "no horizontal scrolling at 360px")
      assert.equal(await page.locator("h1").count(), 1)
      assert.match(await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content"), /connect-src 'self'/)
      await context.close()
    })
  }
})

describe("Holocron (Star Wars watch order)", () => {
  const slug = "star-wars-watch-order"
  test("opens on the first entry, with the archive counted as sealed and done", async () => {
    const { page, context } = await open(slug)
    assert.equal(await page.locator("#next h2").innerText(), "Star Wars: The Bad Batch")
    assert.match(await page.locator("#count").innerText(), /^0 \/ \d+ logged$/)
    assert.equal(await page.locator("#archline").innerText(), "Sealed archive: 8 titles + 135 Clone Wars fragments")
    await page.click("#tab-archive")
    assert.equal(await page.locator("#view-archive details.group").count(), 9)
    assert.equal(await page.locator("#view-archive .cw").count(), 135)
    assert.equal(await page.locator("#view-archive .cw.event").count(), 1)
    await context.close()
  })

  test("checking things off survives a reload, and is stored in the original v8 save format", async () => {
    const { page, context } = await open(slug)
    await page.click("#next-mark")
    assert.match(await page.locator("#count").innerText(), /^1 \//)
    await page.reload()
    assert.match(await page.locator("#count").innerText(), /^1 \//)
    const saved = JSON.parse(await page.evaluate(() => localStorage.getItem("star-wars-watch-order:v8")))
    assert.equal(saved[0].id, "bad-batch")
    assert.equal(saved[0].seasons[0].eps[0], true)
    assert.equal(saved[1].w, false)
    await context.close()
  })

  test("importing a v8 save merges it; up next skips finished and upcoming entries", async () => {
    const { page, context } = await open(slug)
    const bb = { id: "bad-batch", expanded: false, seasons: [0, 1, 2].map((i) => ({ s: i + 1, eps: Array(16).fill(true) })) }
    await page.click("#backup summary")
    await page.fill("#imp", JSON.stringify([bb, { id: "solo", w: true }]))
    await page.click("#import")
    assert.match(await page.locator("#bmsg").innerText(), /Imported progress for 2 entries/)
    assert.equal(await page.locator("#next h2").innerText(), "Obi-Wan Kenobi", "Maul is upcoming and skipped, so the next entry is #4")
    assert.match(await page.locator("#next .lab").innerText(), /#4 in watch order/i)
    await page.fill("#imp", "nope"); await page.click("#import")
    assert.match(await page.locator("#bmsg").innerText(), /not valid JSON/)
    await page.fill("#imp", '[{"id":"nothing-here"}]'); await page.click("#import")
    assert.match(await page.locator("#bmsg").innerText(), /No entries/)
    await context.close()
  })

  test("episodes can be ticked, the datafile opens and closes with Escape, and reset needs confirmation", async () => {
    const { page, context } = await open(slug)
    await page.click("#exp-kenobi")
    assert.equal(await page.locator("#view-active li.ep").count(), 6)
    await page.locator("#chk-kenobi-0-0").check()
    assert.match(await page.locator("#list").innerText(), /1\/6 episodes/)
    await page.click("button[aria-label='Datafile for Obi-Wan Kenobi']")
    assert.equal(await page.locator("dialog[open] h2").innerText(), "Obi-Wan Kenobi")
    await page.keyboard.press("Escape")
    assert.equal(await page.locator("dialog[open]").count(), 0)
    page.once("dialog", (d) => d.dismiss()); await page.click("#backup summary"); await page.click("#reset")
    assert.match(await page.locator("#list").innerText(), /1\/6 episodes/, "dismissing the confirmation keeps the progress")
    page.once("dialog", (d) => d.accept()); await page.click("#reset")
    assert.match(await page.locator("#count").innerText(), /^0 \//)
    await context.close()
  })

  test("era filter, hide finished, and select-several bulk marking", async () => {
    const { page, context } = await open(slug)
    await page.getByRole("button", { name: /^Age of Rebellion/ }).click()
    assert.equal(await page.locator("#list > li").count(), 7)
    await page.click("#selmode")
    await page.locator("#sel-anh").check(); await page.locator("#sel-esb").check()
    assert.match(await page.locator("#selcount").innerText(), /^2 selected$/i)   // the label is drawn in capitals
    await page.click("#selwatch")
    assert.equal(await page.locator("#selbar").isHidden(), true)
    await page.click("#hidedone")
    assert.equal(await page.locator("#list > li").count(), 5, "two finished entries are hidden")
    await page.getByRole("button", { name: "All eras" }).click()
    assert.equal(await page.locator("#list > li").count(), 17)
    await context.close()
  })

  test("tabs work with the arrow keys, and extras link out safely", async () => {
    const { page, context } = await open(slug)
    await page.locator("#tab-active").focus(); await page.keyboard.press("ArrowRight")
    assert.equal(await page.locator("#tab-archive").getAttribute("aria-selected"), "true")
    await page.keyboard.press("ArrowRight")
    assert.equal(await page.locator("#view-extras").isVisible(), true)
    const rels = await page.locator("#view-extras a.card").evaluateAll((as) => as.map((a) => a.rel + "|" + a.target))
    assert.ok(rels.length >= 9 && rels.every((r) => r === "noopener noreferrer|_blank"))
    await context.close()
  })
})

describe("Decision Wheel", () => {
  const slug = "decision-wheel"
  test("the wheel lands on exactly the option the random draw picked", async () => {
    const { page, context } = await open(slug, { reducedMotion: "reduce" })
    for (let i = 0; i < 12; i++) {
      await page.click("#spin")
      const [picked, winner] = await page.locator("#wheel").evaluate((c) => [c.dataset.picked, c.dataset.winner])
      assert.equal(winner, picked)
      assert.equal(await page.locator("#rtext").innerText(), winner)
    }
    assert.equal(await page.locator("#hist li").count(), 12)
    await context.close()
  })

  test("weights change the odds", async () => {
    const { page, context } = await open(slug, { reducedMotion: "reduce" })
    await page.fill("#opts", "Heavy x200\nLight")
    let heavy = 0
    for (let i = 0; i < 30; i++) { await page.click("#spin"); if ((await page.locator("#rtext").innerText()) === "Heavy") heavy++ }
    assert.ok(heavy >= 27, `Heavy won ${heavy}/30`)
    await context.close()
  })

  test("remove-winner mode shrinks the list; too few options disables the spin", async () => {
    const { page, context } = await open(slug, { reducedMotion: "reduce" })
    await page.fill("#opts", "A\nB\nC"); await page.check("#remove")
    await page.click("#spin")
    assert.equal((await page.inputValue("#opts")).split("\n").filter(Boolean).length, 2)
    await page.click("#spin")
    assert.equal(await page.locator("#spin").isDisabled(), true)
    assert.match(await page.locator("#warn").innerText(), /at least two/)
    await context.close()
  })

  test("with animation: the hub is locked while spinning, then the winner is announced", async () => {
    const { page, context } = await open(slug)
    await page.fill("#opts", "One\nTwo\nThree"); await page.click("#spin")
    assert.equal(await page.locator("#spin").isDisabled(), true)
    await page.waitForFunction(() => document.getElementById("wheel").dataset.winner, null, { timeout: 12000 })
    assert.equal(await page.locator("#spin").isDisabled(), false)
    assert.equal(await page.locator("#wheel").evaluate((c) => c.dataset.winner === c.dataset.picked), true)
    await context.close()
  })

  test("options persist, and a shared link loads the same wheel", async () => {
    const { page, context } = await open(slug, { permissions: ["clipboard-read", "clipboard-write"] })
    await page.fill("#opts", "Café ☕ x2\nTea"); await page.reload()
    assert.equal(await page.inputValue("#opts"), "Café ☕ x2\nTea")
    await page.click("#link")
    const url = await page.evaluate(() => navigator.clipboard.readText())
    assert.match(url, /#wheel=/)
    const other = await browser.newContext(); const p2 = await other.newPage()
    await p2.goto(url); assert.equal(await p2.inputValue("#opts"), "Café ☕ x2\nTea")
    await other.close(); await context.close()
  })
})

describe("JSON Explorer", () => {
  const slug = "json-explorer"
  test("opens on a sample; the tree expands, finds, jumps to a path and walks by keyboard", async () => {
    const { page, context } = await open(slug)
    assert.match(await page.locator("#status").innerText(), /Valid JSON \(object\)/)
    await page.locator("#tree [role=treeitem]").first().focus()
    await page.keyboard.press("ArrowDown"); await page.keyboard.press("ArrowDown")
    assert.equal(await page.locator("#path").innerText(), "$.version")
    await page.fill("#q", "utility")
    assert.equal(await page.locator("#qn").innerText(), "1 / 1")
    assert.equal(await page.locator("#path").innerText(), "$.artifacts[1].tags[1]")
    await page.fill("#goto", '$["odd key"]["with.dots"]'); await page.click("#go")
    assert.equal(await page.locator("#path").innerText(), '$["odd key"]["with.dots"]')
    await page.fill("#goto", "$.nope.x"); await page.click("#go")
    assert.match(await page.locator("#status").innerText(), /Nothing at \$\.nope/)
    await context.close()
  })

  test("errors say what and where, the same in every browser", async () => {
    const { page, context } = await open(slug)
    const cases = [['{"a":1,}', "Expected a property name in double quotes (line 1, column 8)"], ["[1,2", "Unexpected end of input (line 1, column 5)"], ['{"a" 1}', "Expected ':' after the property name (line 1, column 6)"], ['[1,\n 2,,]', "Unexpected ',' (line 2, column 4)"]]
    for (const [input, expected] of cases) {
      await page.fill("#src", input)
      await page.waitForFunction((x) => document.getElementById("status").innerText.includes(x), expected)
    }
    await context.close()
  })

  test("a 5,000-item array stays light, and format / minify / sort rewrite the input", async () => {
    const { page, context } = await open(slug)
    await page.fill("#src", JSON.stringify(Array.from({ length: 5000 }, (_, i) => ({ id: i }))))
    await page.waitForFunction(() => /10,?001 values/i.test(document.getElementById("stats").innerText))
    assert.ok((await page.locator("#tree li").count()) <= 110, "only the first 100 children are drawn")
    await page.click(".more"); assert.ok((await page.locator("#tree li").count()) > 150)
    await page.fill("#src", '{"b":1,"a":{"d":1,"c":2}}')
    await page.waitForFunction(() => document.getElementById("status").innerText.startsWith("Valid"))
    await page.click("#sort"); assert.equal((await page.inputValue("#src")).replace(/\s+/g, ""), '{"a":{"c":2,"d":1},"b":1}')
    await page.click("#min"); assert.equal(await page.inputValue("#src"), '{"a":{"c":2,"d":1},"b":1}')
    await context.close()
  })

  test("opens a dropped/selected file, and saves nothing", async () => {
    const { page, context } = await open(slug)
    await page.setInputFiles("#file", { name: "x.json", mimeType: "application/json", buffer: Buffer.from('{"secret":"do not store me"}') })
    await page.waitForFunction(() => document.getElementById("src").value.includes("do not store me"))
    assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0)
    await context.close()
  })
})

describe("168 Hours", () => {
  const slug = "168-hours"
  const cell = (page, day, hour) => page.locator(`.c[data-i="${day * 24 + hour}"]`)
  test("dragging paints a run of hours; undo and redo restore it", async () => {
    const { page, context } = await open(slug)
    await page.getByLabel(/^Work, 0 hours/).check()
    const a = await cell(page, 0, 9).boundingBox(), z = await cell(page, 0, 12).boundingBox()
    await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2); await page.mouse.down()
    await page.mouse.move(z.x + z.width / 2, z.y + z.height / 2, { steps: 12 }); await page.mouse.up()
    assert.equal(await page.locator("#tPlanned").innerText(), "4")
    assert.equal(await page.locator("#tFree").innerText(), "164")
    assert.match(await cell(page, 0, 10).getAttribute("aria-label"), /Mon 10:00, Work/)
    await page.click("#undo"); assert.equal(await page.locator("#tPlanned").innerText(), "0")
    await page.click("#redo"); assert.equal(await page.locator("#tPlanned").innerText(), "4")
    await context.close()
  })

  test("keyboard: arrows move, Space paints, number keys pick brushes, painting twice clears", async () => {
    const { page, context } = await open(slug)
    await cell(page, 0, 0).focus()
    await page.keyboard.press("ArrowDown"); await page.keyboard.press("2"); await page.keyboard.press(" ")
    assert.match(await cell(page, 0, 1).getAttribute("aria-label"), /Mon 01:00, Work/)
    await page.keyboard.press(" ")
    assert.match(await cell(page, 0, 1).getAttribute("aria-label"), /unclaimed/)
    await page.keyboard.press("ArrowRight"); await page.keyboard.press("0"); await page.keyboard.press(" ")
    assert.equal(await page.locator("#tPlanned").innerText(), "0")
    await context.close()
  })

  test("sleep preset fills 56 hours, targets show what is left, and the plan survives a reload", async () => {
    const { page, context } = await open(slug)
    await page.click("#sleep")
    assert.equal(await page.locator("#tPlanned").innerText(), "56")
    assert.match(await page.locator(".brush").first().innerText(), /on target/)
    await page.getByLabel("Weekly target in hours for Work").fill("40")
    assert.match(await page.locator(".brush").nth(1).innerText(), /40 h to go/)
    await page.reload()
    assert.equal(await page.locator("#tPlanned").innerText(), "56")
    await page.click("#clear"); assert.equal(await page.locator("#tPlanned").innerText(), "0")
    await page.click("#undo"); assert.equal(await page.locator("#tPlanned").innerText(), "56")
    await context.close()
  })
})

describe("Premortem", () => {
  const slug = "premortem"
  test("reasons are scored, plotted and ranked; the top three need a mitigation", async () => {
    const { page, context } = await open(slug)
    await page.fill("#proj", "Move house")
    assert.match(await page.locator("#scene").innerText(), /“Move house” has failed/)
    for (const [text, l, i] of [["The van was too small", 2, 2], ["Nobody labelled the boxes", 5, 4], ["The lease date slipped", 3, 5]]) {
      await page.click("#add"); const n = await page.locator("#risks > li").count()
      await page.getByLabel(`Reason ${n}`, { exact: true }).fill(text)
      await page.getByLabel(`Likelihood of reason ${n}`).selectOption(String(l)); await page.getByLabel(`Impact of reason ${n}`).selectOption(String(i))
    }
    const fix = await page.locator("#fix li").allInnerTexts()
    assert.match(fix[0], /2\. Nobody labelled the boxes \(score 20\)/)
    assert.match(fix[1], /3\. The lease date slipped \(score 15\)/)
    assert.match(fix[0], /No mitigation yet/)
    await page.getByLabel("Mitigation for reason 2").fill("Colour-code rooms first.")
    assert.match((await page.locator("#fix li").first().innerText()), /Mitigation: Colour-code rooms first\./)
    assert.equal(await page.locator("#matrix .dot").count(), 3)
    assert.match(await page.locator("#stats").innerText(), /3 reasons · 2 high-risk \(15\+\) · 2 without a mitigation/)
    await context.close()
  })

  test("starter phrases add a reason; markdown export is sorted; everything persists; reset asks first", async () => {
    const { page, context } = await open(slug, { permissions: ["clipboard-read", "clipboard-write"] })
    await page.getByRole("button", { name: "Nobody ever decided…" }).click()
    assert.equal(await page.evaluate(() => document.activeElement.value), "Nobody ever decided ")
    await page.keyboard.type("who approves it"); await page.getByLabel("Likelihood of reason 1").selectOption("4")
    await page.click("#add"); await page.getByLabel("Reason 2", { exact: true }).fill("Low one"); await page.getByLabel("Likelihood of reason 2").selectOption("1")
    await page.click("#copy")
    const md = await page.evaluate(() => navigator.clipboard.readText())
    assert.match(md, /^# Premortem: Untitled/)
    assert.ok(md.indexOf("who approves it") < md.indexOf("Low one"), "highest score first")
    await page.reload()
    assert.equal(await page.locator("#risks > li").count(), 2)
    page.once("dialog", (d) => d.dismiss()); await page.click("#reset"); assert.equal(await page.locator("#risks > li").count(), 2)
    page.once("dialog", (d) => d.accept()); await page.click("#reset"); assert.equal(await page.locator("#risks > li.risk").count(), 0)
    await context.close()
  })
})

describe("Review Queue", () => {
  const slug = "review-queue"
  test("a new item is due tomorrow; remembering moves it out 3 days, forgetting brings it back next day", async () => {
    const { page, context } = await open(slug, {}, "?today=2026-01-01")
    await page.fill("#front", "What is idempotency?"); await page.fill("#back", "Doing it twice equals doing it once.")
    await page.click("button[type=submit]")
    assert.equal(await page.locator("#sDue").innerText(), "0")
    assert.match(await page.locator("#list").innerText(), /Next .*Jan 2.* \(in 1 d\)/)
    await page.goto(page.url().replace("2026-01-01", "2026-01-02"))
    assert.equal(await page.locator("#sDue").innerText(), "1")
    assert.equal(await page.getByText("Doing it twice").count(), 0, "the answer is hidden until asked for")
    await page.getByRole("button", { name: "Show answer" }).click()
    assert.equal(await page.getByText("Doing it twice equals doing it once.").count(), 1)
    await page.getByRole("button", { name: "Remembered" }).click()
    assert.equal(await page.locator("#sDue").innerText(), "0")
    assert.match(await page.locator("#list").innerText(), /\(in 3 d\)/)
    assert.equal(await page.locator("#sRate").innerText(), "100%")
    await page.goto(page.url().replace("2026-01-02", "2026-01-05"))
    assert.equal(await page.locator("#sDue").innerText(), "1")
    await page.getByRole("button", { name: "Show answer" }).click(); await page.getByRole("button", { name: "Forgot" }).click()
    assert.match(await page.locator("#list").innerText(), /\(in 1 d\)/)
    assert.equal(await page.locator("#sRate").innerText(), "50%")
    await context.close()
  })

  test("the 14-day chart counts what is due, overdue items are labelled, and a backup restores everything", async () => {
    const { page, context } = await open(slug, { permissions: ["clipboard-read", "clipboard-write"] }, "?today=2026-03-01")
    for (const t of ["One", "Two", "Three"]) { await page.fill("#front", t); await page.click("button[type=submit]") }
    assert.equal(await page.locator("#chart .col").count(), 14)
    assert.match(await page.locator("#chart").getAttribute("aria-label"), /^Reviews due over the next 14 days: 0, 3, 0/)
    await page.click("details summary"); const backup = await page.inputValue("#exp")
    await page.goto(page.url().replace("2026-03-01", "2026-03-05"))
    assert.match(await page.locator("#due").innerText(), /3 days overdue/)   // due Mar 2, viewed on Mar 5
    page.once("dialog", (d) => d.accept()); await page.click("details summary"); await page.click("#wipe")
    assert.equal(await page.locator("#sAll").innerText(), "0")
    await page.fill("#imp", backup); await page.click("#import")
    assert.equal(await page.locator("#sAll").innerText(), "3")
    await page.fill("#imp", "{}"); await page.click("#import"); assert.match(await page.locator("#bmsg").innerText(), /not a Review Queue backup/)
    await context.close()
  })

  test("ignores a bad ?today value and clears the item when deleted", async () => {
    const { page, context } = await open(slug, {}, "?today=banana")
    await page.fill("#front", "Temp"); await page.click("button[type=submit]")
    assert.equal(await page.locator("#sAll").innerText(), "1")
    await page.getByRole("button", { name: "Delete: Temp" }).click(); assert.equal(await page.locator("#sAll").innerText(), "0")
    await context.close()
  })
})

describe("installable apps (PWA)", () => {
  const installable = () => manifest().filter((a) => a.install)
  const pngSize = (buf) => [buf.readUInt32BE(16), buf.readUInt32BE(20)]

  test("every app marked install is in the gallery data, and the right ones are", () => {
    const slugs = installable().map((a) => a.slug).sort()
    for (const must of ["decision-wheel", "star-wars-watch-order", "json-explorer", "168-hours", "review-queue"]) assert.ok(slugs.includes(must), `${must} is installable`)
    assert.ok(!slugs.includes("premortem"), "premortem is left as a web page")
  })

  for (const slug of ["decision-wheel", "star-wars-watch-order", "json-explorer", "168-hours", "review-queue", "pomodoro-timer", "snake-game", "shelf-intro-slides"]) {
    test(`${slug}: manifest, real icons and iPhone tags`, async () => {
      const { page, context } = await open(slug)
      const entry = manifest().find((a) => a.slug === slug)
      const base = `${server.url}${entry.short}/`
      const mf = await (await context.request.get(base + (await page.locator('link[rel=manifest]').getAttribute("href")))).json()
      assert.equal(mf.name, entry.title)
      assert.equal(mf.display, "standalone")
      assert.equal(mf.scope, "./"); assert.equal(mf.start_url, "./")
      assert.match(mf.theme_color, /^#[0-9a-f]{6}$/i)
      for (const [size, file] of [[192, "icon-192.png"], [512, "icon-512.png"]]) {
        const res = await context.request.get(base + file)
        assert.equal(res.status(), 200); assert.match(res.headers()["content-type"], /image\/png/)
        assert.deepEqual(pngSize(await res.body()), [size, size], `${file} is really ${size}px`)
      }
      assert.equal(await page.locator('link[rel=apple-touch-icon]').getAttribute("href"), "icon-192.png")
      assert.equal(await page.locator('meta[name=apple-mobile-web-app-capable]').getAttribute("content"), "yes")
      assert.equal(await page.locator('meta[name=apple-mobile-web-app-title]').count(), 1)
      await context.close()
    })
  }

  for (const slug of ["decision-wheel", "star-wars-watch-order", "json-explorer", "168-hours", "review-queue"]) {
    test(`${slug}: the service worker takes over and the app still opens with the network off`, async () => {
      const { page, context } = await open(slug)
      await page.evaluate(() => navigator.serviceWorker.ready)
      await page.reload({ waitUntil: "load" })          // now served by the service worker
      assert.equal(await page.evaluate(() => !!navigator.serviceWorker.controller), true)
      await context.setOffline(true)
      await page.reload({ waitUntil: "load" })
      assert.equal(await page.locator("h1").count() > 0, true, "the page rendered from the cache")
      assert.ok((await page.title()).length > 0)
      await context.close()
    })
  }

  test("data written while online is still there offline (the Holocron's progress)", async () => {
    const { page, context } = await open("star-wars-watch-order")
    await page.evaluate(() => navigator.serviceWorker.ready); await page.reload()
    await page.click("#next-mark")
    await context.setOffline(true); await page.reload()
    assert.match(await page.locator("#count").innerText(), /^1 \//)
    await context.close()
  })
})
