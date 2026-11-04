// Checks the colour tokens in src/index.css against WCAG 2.2 AA (4.5:1 text, 3:1 UI).
// Run: node scripts/check-contrast.mjs
import { readFileSync } from "node:fs"

const css = readFileSync(new URL("../src/index.css", import.meta.url), "utf8")
const block = (sel) => {
  const m = css.match(new RegExp(`${sel}\\s*\\{([^}]*)\\}`))
  return Object.fromEntries([...m[1].matchAll(/--([a-z-]+):\s*(#[0-9a-f]{6})/gi)].map((x) => [x[1], x[2]]))
}
const lum = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
const ratio = (a, b) => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}
const light = block(":root")
const dark = { ...light, ...block("\\.dark") }
const pairs = [
  ["ink", "bg", 4.5], ["ink", "surface", 4.5], ["muted", "bg", 4.5], ["muted", "surface", 4.5], ["muted", "sunken", 4.5],
  ["accent", "bg", 4.5], ["accent", "surface", 4.5], ["accent-ink", "accent", 4.5], ["accent-ink", "accent-hover", 4.5],
  ["accent", "accent-soft", 4.5], ["danger", "bg", 4.5], ["focus", "bg", 3], ["focus", "surface", 3], ["faint", "bg", 3],
]
let failed = 0
for (const [name, t] of [["light", light], ["dark", dark]]) {
  for (const [fg, bg, min] of pairs) {
    const r = ratio(t[fg], t[bg])
    const ok = r >= min
    if (!ok) failed++
    console.log(`${ok ? "ok  " : "FAIL"} ${name.padEnd(5)} ${fg} on ${bg}: ${r.toFixed(2)} (need ${min})`)
  }
}
process.exit(failed ? 1 : 0)
