import { describe, expect, it } from "vitest"

import { DEFAULT_FILTERS } from "@/lib/filter"
import { absoluteUrl, buildSearch, parseHash, parseSearch, resolveSlug, shareLabel, shareUrl, siteBase } from "@/lib/url"

import { SAMPLE } from "./fixtures"

describe("search params", () => {
  it("round-trips filters and sort", () => {
    const state = { filters: { query: "timer", kind: "app" as const, tags: ["a", "b"], installable: true }, sort: "oldest" as const }
    const search = buildSearch(state.filters, state.sort)
    expect(search).toBe("?q=timer&kind=app&tag=a%2Cb&installable=1&sort=oldest")
    expect(parseSearch(search)).toEqual(state)
  })
  it("leaves defaults out so a clean gallery has a clean URL", () => {
    expect(buildSearch(DEFAULT_FILTERS, "newest")).toBe("")
    expect(buildSearch(DEFAULT_FILTERS, null)).toBe("")
  })
  it("ignores unknown or malicious values", () => {
    const parsed = parseSearch("?kind=<script>&sort=sideways&installable=yes&tag=,,")
    expect(parsed.filters).toEqual(DEFAULT_FILTERS)
    expect(parsed.sort).toBeNull()
  })
  it("caps the query length", () => {
    expect(parseSearch("?q=" + "x".repeat(500)).filters.query).toHaveLength(200)
  })
})

describe("hash links", () => {
  it("reads a slug", () => {
    expect(parseHash("#pomodoro-timer")).toBe("pomodoro-timer")
    expect(parseHash("#/pomodoro-timer")).toBe("pomodoro-timer")
  })
  it("ignores anything that is not a slug", () => {
    expect(parseHash("")).toBeNull()
    expect(parseHash("#")).toBeNull()
    expect(parseHash("#../etc")).toBeNull()
    expect(parseHash("#%E0%A4%A")).toBeNull()
    expect(parseHash("#Has Space")).toBeNull()
    expect(parseHash("#install")).toBe("install") // looks like a slug; resolveSlug decides it matches nothing
  })
  it("resolves current slugs and old aliases, and nothing else", () => {
    expect(resolveSlug("pomodoro-timer", SAMPLE)?.slug).toBe("pomodoro-timer")
    expect(resolveSlug("shorty", SAMPLE)?.slug).toBe("url-shortener")
    expect(resolveSlug("install", SAMPLE)).toBeNull()
    expect(resolveSlug(null, SAMPLE)).toBeNull()
  })
})

describe("URLs under a GitHub Pages sub-path", () => {
  const page = "https://user.github.io/shelf/?q=x#pomodoro-timer"
  it("derives the base from any page address", () => {
    expect(siteBase(page)).toBe("https://user.github.io/shelf/")
    expect(siteBase("https://user.github.io/shelf")).toBe("https://user.github.io/shelf/")
    expect(siteBase("https://user.github.io/shelf/index.html#x")).toBe("https://user.github.io/shelf/")
    expect(siteBase("http://localhost:8000/")).toBe("http://localhost:8000/")
  })
  it("builds absolute artifact and short links", () => {
    expect(absoluteUrl("artifacts/a/", page)).toBe("https://user.github.io/shelf/artifacts/a/")
    expect(shareUrl({ short: "74ng", url: "artifacts/a/" }, page)).toBe("https://user.github.io/shelf/74ng")
    expect(shareUrl({ short: null, url: "artifacts/a/" }, page)).toBe("https://user.github.io/shelf/artifacts/a/")
    expect(shareLabel({ short: "74ng", url: "artifacts/a/" }, page)).toBe("user.github.io/shelf/74ng")
  })
  it("works on a custom domain at the root", () => {
    expect(shareUrl({ short: "74ng", url: "x/" }, "https://go.example.com/#a")).toBe("https://go.example.com/74ng")
  })
})
