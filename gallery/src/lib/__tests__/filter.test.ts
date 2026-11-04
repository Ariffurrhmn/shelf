import { describe, expect, it } from "vitest"

import { DEFAULT_FILTERS, arrange, filterArtifacts, hasActiveFilters, kindCounts, sortArtifacts, tagCounts } from "@/lib/filter"
import type { Filters } from "@/types"

import { SAMPLE, make } from "./fixtures"

const f = (over: Partial<Filters>): Filters => ({ ...DEFAULT_FILTERS, ...over })
const slugs = (l: { slug: string }[]) => l.map((a) => a.slug)

describe("filterArtifacts", () => {
  it("returns everything with default filters", () => {
    expect(filterArtifacts(SAMPLE, DEFAULT_FILTERS)).toHaveLength(SAMPLE.length)
  })
  it("filters by category (kind)", () => {
    expect(slugs(filterArtifacts(SAMPLE, f({ kind: "game" })))).toEqual(["snake-game"])
  })
  it("filters by tag, and several tags must all match", () => {
    expect(slugs(filterArtifacts(SAMPLE, f({ tags: ["timer"] })))).toEqual(["pomodoro-timer"])
    expect(filterArtifacts(SAMPLE, f({ tags: ["timer", "arcade"] }))).toEqual([])
  })
  it("filters installable apps", () => {
    expect(slugs(filterArtifacts(SAMPLE, f({ installable: true }))).sort()).toEqual(["pomodoro-timer", "snake-game"])
  })
  it("combines search, category and tag", () => {
    expect(slugs(filterArtifacts(SAMPLE, f({ query: "timer", kind: "app", tags: ["productivity"] })))).toEqual(["pomodoro-timer"])
    expect(filterArtifacts(SAMPLE, f({ query: "timer", kind: "game" }))).toEqual([])
  })
  it("does not mutate its input", () => {
    const copy = [...SAMPLE]
    filterArtifacts(SAMPLE, f({ kind: "app" }))
    expect(SAMPLE).toEqual(copy)
  })
  it("knows when filters are active", () => {
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false)
    expect(hasActiveFilters(f({ query: "  " }))).toBe(false)
    expect(hasActiveFilters(f({ query: "x" }))).toBe(true)
    expect(hasActiveFilters(f({ tags: ["a"] }))).toBe(true)
    expect(hasActiveFilters(f({ installable: true }))).toBe(true)
  })
})

describe("sortArtifacts", () => {
  it("newest first, ties by title", () => {
    expect(slugs(sortArtifacts(SAMPLE, "newest"))).toEqual(["url-shortener", "intro-slides", "snake-game", "pomodoro-timer", "zeta-2", "zeta"])
  })
  it("oldest first", () => {
    expect(slugs(sortArtifacts(SAMPLE, "oldest")).slice(0, 2)).toEqual(["zeta-2", "zeta"])
    expect(slugs(sortArtifacts(SAMPLE, "oldest")).at(-1)).toBe("url-shortener")
  })
  it("title A-Z is natural (9 before 10) and case-insensitive", () => {
    const list = [make({ slug: "b", title: "banana" }), make({ slug: "a", title: "Apple" }), make({ slug: "z10", title: "zeta 10" }), make({ slug: "z9", title: "zeta 9" })]
    expect(slugs(sortArtifacts(list, "title-asc"))).toEqual(["a", "b", "z9", "z10"])
    expect(slugs(sortArtifacts(list, "title-desc"))).toEqual(["z10", "z9", "b", "a"])
  })
  it("puts unreadable dates last when newest, first when oldest, without throwing", () => {
    const list = [make({ slug: "bad", created: "not a date" }), make({ slug: "ok", created: "2026-01-01" })]
    expect(slugs(sortArtifacts(list, "newest"))).toEqual(["ok", "bad"])
    expect(slugs(sortArtifacts(list, "oldest"))).toEqual(["bad", "ok"])
  })
  it("returns a new array", () => {
    expect(sortArtifacts(SAMPLE, "newest")).not.toBe(SAMPLE)
  })
})

describe("counts", () => {
  it("counts kinds in a fixed order and skips empty ones", () => {
    expect(kindCounts(SAMPLE)).toEqual([
      { kind: "app", count: 4 },
      { kind: "game", count: 1 },
      { kind: "presentation", count: 1 },
    ])
  })
  it("ranks tags by use, then alphabetically, counting a repeated tag once per artifact", () => {
    const list = [make({ slug: "a", tags: ["x", "x", "b"] }), make({ slug: "b", tags: ["x", "a"] })]
    expect(tagCounts(list)).toEqual([{ tag: "x", count: 2 }, { tag: "a", count: 1 }, { tag: "b", count: 1 }])
  })
})

describe("arrange (featured vs grid)", () => {
  const sorted = sortArtifacts(SAMPLE, "newest")
  it("hides the featured strip when nothing is featured", () => {
    const plain = SAMPLE.map((a) => ({ ...a, featured: false }))
    expect(arrange(plain, plain, false)).toEqual({ featured: [], grid: plain })
  })
  it("shows featured once: strip in the default view, not repeated in the grid", () => {
    const r = arrange(SAMPLE, sorted, false)
    expect(slugs(r.featured)).toEqual(["intro-slides"])
    expect(slugs(r.grid)).not.toContain("intro-slides")
    expect(r.grid).toHaveLength(SAMPLE.length - 1)
  })
  it("while filtering, drops the strip and keeps featured projects in the results", () => {
    const r = arrange(SAMPLE, filterArtifacts(sorted, f({ kind: "presentation" })), true)
    expect(r.featured).toEqual([])
    expect(slugs(r.grid)).toEqual(["intro-slides"])
  })
  it("skips the strip when everything is featured", () => {
    const all = SAMPLE.map((a) => ({ ...a, featured: true }))
    expect(arrange(all, all, false)).toEqual({ featured: [], grid: all })
  })
})
