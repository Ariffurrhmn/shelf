import { describe, expect, it } from "vitest"

import { matchesQuery, normalize, tokenize } from "@/lib/search"

import { SAMPLE, make } from "./fixtures"

describe("normalize", () => {
  it("lowercases, strips accents and punctuation", () => {
    expect(normalize("Pomodoro-Timer!")).toBe("pomodoro timer")
    expect(normalize("Café  Crème")).toBe("cafe creme")
  })
})

describe("tokenize", () => {
  it("treats a trailing plural s as optional but leaves short words alone", () => {
    expect(tokenize("Games timers")).toEqual(["game", "timer"])
    expect(tokenize("css bus")).toEqual(["css", "bus"])
  })
})

describe("matchesQuery", () => {
  const by = (q: string) => SAMPLE.filter((a) => matchesQuery(a, q)).map((a) => a.slug)

  it("matches everything for an empty or blank query", () => {
    expect(by("")).toHaveLength(SAMPLE.length)
    expect(by("   ")).toHaveLength(SAMPLE.length)
  })
  it("is case-insensitive and searches title, tags, tool and category", () => {
    expect(by("POMODORO")).toEqual(["pomodoro-timer"])
    expect(by("arcade")).toEqual(["snake-game"])
    expect(by("chatgpt")).toEqual(["url-shortener"])
    expect(by("games")).toEqual(["snake-game"])
    expect(by("presentation")).toEqual(["intro-slides"])
  })
  it("searches notes and ignores accents", () => {
    expect(by("cafe")).toEqual(["url-shortener"])
  })
  it("requires every word, in any order", () => {
    expect(by("timer pomodoro")).toEqual(["pomodoro-timer"])
    expect(by("timer snake")).toEqual([])
  })
  it("finds the slug as well as the title", () => {
    expect(by("pomodoro timer")).toEqual(["pomodoro-timer"])
    expect(by("zeta-2")).toEqual(["zeta-2"])
  })
  it("treats regex characters as plain punctuation", () => {
    expect(by("(.*[")).toHaveLength(SAMPLE.length) // punctuation only: same as no query
    expect(by("snake)(")).toEqual(["snake-game"])
  })
  it("uses optional fields only when present", () => {
    const a = make({ slug: "x", why: "I wanted a quiet metronome", status: "experiment" })
    expect(matchesQuery(a, "metronome")).toBe(true)
    expect(matchesQuery(a, "experiment")).toBe(true)
    expect(matchesQuery(make({ slug: "y" }), "undefined")).toBe(false)
  })
})
