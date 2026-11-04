import { KIND_META } from "@/lib/kinds"
import type { Artifact } from "@/types"

/** Lowercase, strip accents, turn punctuation into spaces: "Pomodoro-Timer!" -> "pomodoro timer". */
export function normalize(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
}

/** Splits a query into words, treating a trailing plural "s" as optional ("games" finds "game"). */
export function tokenize(query: string): string[] {
  return normalize(query)
    .split(" ")
    .filter(Boolean)
    .map((t) => (t.length > 3 && t.endsWith("s") ? t.slice(0, -1) : t))
}

const haystacks = new WeakMap<Artifact, string>()

/** Everything about an artifact that a visitor might search for, normalised once. */
export function haystack(a: Artifact): string {
  let h = haystacks.get(a)
  if (h === undefined) {
    const kind = KIND_META[a.kind]
    h = normalize(
      [a.title, a.slug, a.description, a.why, a.notes, a.tool, a.status, kind?.label, kind?.plural, a.kind, ...a.tags]
        .filter(Boolean)
        .join(" ")
    )
    haystacks.set(a, h)
  }
  return h
}

/** Every word of the query must appear somewhere (order does not matter). An empty query matches all. */
export function matchesQuery(a: Artifact, query: string): boolean {
  const tokens = tokenize(query)
  if (tokens.length === 0) return true
  const h = haystack(a)
  return tokens.every((t) => h.includes(t))
}
