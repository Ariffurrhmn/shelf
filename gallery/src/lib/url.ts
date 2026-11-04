import { DEFAULT_FILTERS, DEFAULT_SORT, isSortKey } from "@/lib/filter"
import { isKind } from "@/lib/kinds"
import type { Artifact, Filters, SortKey } from "@/types"

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

export interface Browse {
  filters: Filters
  /** null means "not in the URL": fall back to the saved preference. */
  sort: SortKey | null
}

/** "?q=timer&kind=app&tag=a,b&sort=oldest&installable=1" -> state. Unknown values are ignored. */
export function parseSearch(search: string): Browse {
  const p = new URLSearchParams(search)
  const kind = p.get("kind") ?? ""
  const sort = p.get("sort")
  return {
    filters: {
      query: (p.get("q") ?? "").slice(0, 200),
      kind: isKind(kind) ? kind : "all",
      tags: (p.get("tag") ?? "").split(",").map((t) => t.trim()).filter(Boolean).slice(0, 12),
      installable: p.get("installable") === "1",
    },
    sort: isSortKey(sort) ? sort : null,
  }
}

/** The inverse of parseSearch. Defaults are left out, so a clean gallery has a clean URL. */
export function buildSearch(filters: Filters, sort: SortKey | null): string {
  const p = new URLSearchParams()
  if (filters.query.trim()) p.set("q", filters.query.trim())
  if (filters.kind !== DEFAULT_FILTERS.kind) p.set("kind", filters.kind)
  if (filters.tags.length) p.set("tag", filters.tags.join(","))
  if (filters.installable) p.set("installable", "1")
  if (sort && sort !== DEFAULT_SORT) p.set("sort", sort)
  const s = p.toString()
  return s ? `?${s}` : ""
}

/** "#pomodoro-timer" -> "pomodoro-timer". Anything that is not a slug is ignored. */
export function parseHash(hash: string): string | null {
  let raw = hash.replace(/^#\/?/, "")
  try {
    raw = decodeURIComponent(raw)
  } catch {
    return null
  }
  return SLUG.test(raw) ? raw : null
}

/** Finds an artifact by its slug or by any earlier slug (alias), so old links keep working. */
export function resolveSlug(slug: string | null, artifacts: Artifact[]): Artifact | null {
  if (!slug) return null
  return artifacts.find((a) => a.slug === slug) ?? artifacts.find((a) => a.aliases?.includes(slug)) ?? null
}

/** The page address without ?query, #hash or a trailing index.html: the base for relative URLs. */
export function siteBase(href: string): string {
  const u = new URL(href)
  u.hash = ""
  u.search = ""
  u.pathname = u.pathname.replace(/index\.html$/, "")
  if (!u.pathname.endsWith("/")) u.pathname += "/"
  return u.toString()
}

/** Absolute URL of a manifest-relative path, correct under any base path (GitHub Pages sub-paths included). */
export function absoluteUrl(path: string, href: string): string {
  return new URL(path, siteBase(href)).toString()
}

/** The link worth sharing: the short link when there is one, otherwise the artifact's own address. */
export function shareUrl(a: Pick<Artifact, "short" | "url">, href: string): string {
  return absoluteUrl(a.short ?? a.url, href)
}

export function shareLabel(a: Pick<Artifact, "short" | "url">, href: string): string {
  return shareUrl(a, href).replace(/^https?:\/\//, "")
}
