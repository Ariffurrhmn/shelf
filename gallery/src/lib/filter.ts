import { KIND_ORDER } from "@/lib/kinds"
import { matchesQuery } from "@/lib/search"
import type { Artifact, Filters, Kind, SortKey } from "@/types"

export const DEFAULT_FILTERS: Filters = { query: "", kind: "all", tags: [], installable: false }
export const DEFAULT_SORT: SortKey = "newest"

export const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "title-asc", label: "Title A–Z" },
  { value: "title-desc", label: "Title Z–A" },
]

export function isSortKey(value: string | null | undefined): value is SortKey {
  return SORT_OPTIONS.some((o) => o.value === value)
}

export function hasActiveFilters(f: Filters): boolean {
  return f.query.trim() !== "" || f.kind !== "all" || f.tags.length > 0 || f.installable
}

export function filterArtifacts(list: Artifact[], f: Filters): Artifact[] {
  return list.filter(
    (a) =>
      (f.kind === "all" || a.kind === f.kind) &&
      f.tags.every((t) => a.tags.includes(t)) &&
      (!f.installable || a.install) &&
      matchesQuery(a, f.query)
  )
}

const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true })
const isoDate = (s: string) => (/^\d{4}-\d{2}-\d{2}$/.test(s) ? s : "")

/** Returns a new, stably sorted array. Entries with an unreadable date sort as the oldest. */
export function sortArtifacts(list: Artifact[], sort: SortKey): Artifact[] {
  const byTitle = (a: Artifact, b: Artifact) => collator.compare(a.title, b.title) || a.slug.localeCompare(b.slug)
  const cmp: Record<SortKey, (a: Artifact, b: Artifact) => number> = {
    newest: (a, b) => isoDate(b.created).localeCompare(isoDate(a.created)) || byTitle(a, b),
    oldest: (a, b) => isoDate(a.created).localeCompare(isoDate(b.created)) || byTitle(a, b),
    "title-asc": byTitle,
    "title-desc": (a, b) => byTitle(b, a),
  }
  return [...list].sort(cmp[sort])
}

export function kindCounts(list: Artifact[]): { kind: Kind; count: number }[] {
  const counts = new Map<Kind, number>()
  list.forEach((a) => counts.set(a.kind, (counts.get(a.kind) ?? 0) + 1))
  return KIND_ORDER.filter((k) => counts.has(k)).map((kind) => ({ kind, count: counts.get(kind)! }))
}

/** Tags by how many artifacts use them (most used first, then A–Z). */
export function tagCounts(list: Artifact[]): { tag: string; count: number }[] {
  const counts = new Map<string, number>()
  list.forEach((a) => new Set(a.tags).forEach((t) => counts.set(t, (counts.get(t) ?? 0) + 1)))
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag))
}

export interface Collection {
  featured: Artifact[]
  /** What the main grid shows. */
  grid: Artifact[]
}

/**
 * Splits the (already filtered and sorted) list into the Featured strip and the grid.
 * Featured artifacts appear once: in the strip when nothing is filtered, and in the grid
 * while searching or filtering, when the strip is hidden. If everything is featured the
 * strip is skipped, because it would just repeat the whole collection.
 */
export function arrange(all: Artifact[], visible: Artifact[], filtering: boolean): Collection {
  const featured = all.filter((a) => a.featured === true)
  if (filtering || featured.length === 0 || featured.length === all.length) return { featured: [], grid: visible }
  return { featured, grid: visible.filter((a) => a.featured !== true) }
}
