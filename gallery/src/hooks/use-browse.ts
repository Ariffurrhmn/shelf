import { useCallback, useEffect, useState } from "react"

import { DEFAULT_FILTERS, DEFAULT_SORT, isSortKey } from "@/lib/filter"
import { readPref, writePref } from "@/lib/storage"
import { buildSearch, parseSearch } from "@/lib/url"
import type { Filters, Kind, SortKey } from "@/types"

const SORT_KEY = "shelf-sort"

/**
 * Search, filters and sort.
 *  - Filters live in the URL (?q=&kind=&tag=), so a filtered view can be shared and survives a refresh.
 *    They are never saved between visits: opening Shelf always starts from the whole collection.
 *  - Sort is a preference: the URL wins, otherwise the last explicit choice, otherwise "newest".
 *  - URL updates use replaceState, so filtering does not fill the Back button with history.
 */
export function useBrowse() {
  const [initial] = useState(() => parseSearch(window.location.search))
  const [filters, setFilters] = useState<Filters>(initial.filters)
  const [sort, setSortState] = useState<SortKey>(() => {
    const saved = readPref(SORT_KEY)
    return initial.sort ?? (isSortKey(saved) ? saved : DEFAULT_SORT)
  })

  useEffect(() => {
    const id = window.setTimeout(() => {
      const next = window.location.pathname + buildSearch(filters, sort) + window.location.hash
      if (next !== window.location.pathname + window.location.search + window.location.hash) {
        window.history.replaceState(window.history.state, "", next)
      }
    }, 200)
    return () => window.clearTimeout(id)
  }, [filters, sort])

  const setQuery = useCallback((query: string) => setFilters((f) => ({ ...f, query })), [])
  const setKind = useCallback((kind: Kind | "all") => setFilters((f) => ({ ...f, kind })), [])
  const toggleTag = useCallback(
    (tag: string) =>
      setFilters((f) => ({ ...f, tags: f.tags.includes(tag) ? f.tags.filter((t) => t !== tag) : [...f.tags, tag] })),
    []
  )
  const setInstallable = useCallback((installable: boolean) => setFilters((f) => ({ ...f, installable })), [])
  const clear = useCallback(() => setFilters(DEFAULT_FILTERS), [])
  const setSort = useCallback((s: SortKey) => {
    setSortState(s)
    writePref(SORT_KEY, s)
  }, [])

  return { filters, sort, setQuery, setKind, toggleTag, setInstallable, clear, setSort }
}
