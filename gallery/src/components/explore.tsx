import { Check, ChevronDown, Download, Search, SlidersHorizontal, X } from "lucide-react"
import { useMemo, useState } from "react"

import { ArtifactCard } from "@/components/artifact-card"
import { cx } from "@/lib/cx"
import { SORT_OPTIONS, hasActiveFilters, kindCounts, tagCounts } from "@/lib/filter"
import { plural } from "@/lib/format"
import { KIND_META } from "@/lib/kinds"
import type { Artifact, Filters, Kind, SortKey } from "@/types"

const TAGS_COLLAPSED = 12

interface Props {
  /** The whole collection, for counts and tag lists. */
  all: Artifact[]
  /** What matches right now (after filters and sort), shown in the grid. */
  results: Artifact[]
  /** Featured artifacts shown above, so the grid is "the rest". */
  hiddenFeatured: number
  filters: Filters
  sort: SortKey
  searchRef: React.RefObject<HTMLInputElement | null>
  onQuery: (q: string) => void
  onKind: (k: Kind | "all") => void
  onTag: (t: string) => void
  onInstallable: (on: boolean) => void
  onSort: (s: SortKey) => void
  onClear: () => void
  onDetails: (a: Artifact) => void
}

export function Explore(p: Props) {
  const { all, results, filters, sort } = p
  const [tagsOpen, setTagsOpen] = useState(false)
  const [allTags, setAllTags] = useState(false)
  const tagPanelId = "tag-panel"
  const kinds = useMemo(() => kindCounts(all), [all])
  const tags = useMemo(() => tagCounts(all), [all])
  const installableCount = useMemo(() => all.filter((a) => a.install).length, [all])
  const filtering = hasActiveFilters(filters)
  const shownTags = allTags ? tags : tags.slice(0, TAGS_COLLAPSED)
  // A selected tag is always visible, even if it would be hidden by "show fewer".
  const selectedHidden = filters.tags.filter((t) => !shownTags.some((x) => x.tag === t))

  const countText = filtering
    ? `${results.length} of ${plural(all.length, "artifact")} match`
    : p.hiddenFeatured > 0
      ? `${plural(results.length, "more artifact")}, plus ${p.hiddenFeatured} featured above`
      : plural(results.length, "artifact")

  return (
    <section id="explore" tabIndex={-1} aria-labelledby="explore-title" className="wrap scroll-mt-16 pb-16 outline-none">
      {/* Section title and live result count: announced to screen readers, not drawn. */}
      <h2 id="explore-title" className="sr-only-live">
        Explore Shelf
      </h2>
      <p className="sr-only-live" role="status" aria-live="polite">
        {countText}
      </p>

      {all.length > 0 && (
        <div className="mb-8 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted" aria-hidden />
              <input
                ref={p.searchRef}
                type="search"
                value={filters.query}
                onChange={(e) => p.onQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Escape" && filters.query) {
                    e.preventDefault()
                    p.onQuery("")
                  }
                }}
                placeholder="Search by title, tag, tool…"
                aria-label="Search artifacts"
                autoComplete="off"
                spellCheck={false}
                enterKeyHint="search"
                className="field pr-14 pl-10"
              />
              {filters.query ? (
                <button type="button" onClick={() => { p.onQuery(""); p.searchRef.current?.focus() }} className="btn btn-ghost btn-icon absolute top-1/2 right-1 -translate-y-1/2" aria-label="Clear search">
                  <X aria-hidden />
                </button>
              ) : (
                <kbd className="pointer-events-none absolute top-1/2 right-3 hidden -translate-y-1/2 sm:block" aria-hidden="true">
                  /
                </kbd>
              )}
            </div>
            <label className="flex items-center gap-2 sm:w-52">
              <span className="mono-meta shrink-0">Sort</span>
              <select value={sort} onChange={(e) => p.onSort(e.target.value as SortKey)} className="field cursor-pointer px-3">
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="-mx-4 overflow-x-auto px-4 pb-1 sm:mx-0 sm:overflow-visible sm:px-0 no-scrollbar">
            <div role="group" aria-label="Filter by category" className="flex w-max gap-2 sm:w-auto sm:flex-wrap">
              <button type="button" className="chip" aria-pressed={filters.kind === "all"} onClick={() => p.onKind("all")}>
                All <span className="count">{all.length}</span>
              </button>
              {kinds.map(({ kind, count }) => {
                const Icon = KIND_META[kind].icon
                return (
                  <button key={kind} type="button" className="chip" aria-pressed={filters.kind === kind} onClick={() => p.onKind(filters.kind === kind ? "all" : kind)}>
                    <Icon aria-hidden /> {KIND_META[kind].plural} <span className="count">{count}</span>
                  </button>
                )
              })}
              {installableCount > 0 && (
                <button type="button" className="chip" aria-pressed={filters.installable} onClick={() => p.onInstallable(!filters.installable)}>
                  <Download aria-hidden /> Installable <span className="count">{installableCount}</span>
                </button>
              )}
              {tags.length > 0 && (
                <button type="button" className="chip" aria-expanded={tagsOpen} aria-controls={tagPanelId} onClick={() => setTagsOpen((o) => !o)}>
                  <SlidersHorizontal aria-hidden /> Tags
                  {filters.tags.length > 0 && <span className="count">{filters.tags.length}</span>}
                  <ChevronDown aria-hidden className={cx("transition-transform", tagsOpen && "rotate-180")} />
                </button>
              )}
            </div>
          </div>

          {(filtering || tagsOpen) && (
            <div className="flex flex-wrap items-center gap-2">
              {!tagsOpen &&
                filters.tags.map((t) => (
                  <button key={t} type="button" className="chip" aria-pressed="true" onClick={() => p.onTag(t)} aria-label={`Remove tag filter ${t}`}>
                    #{t} <X aria-hidden />
                  </button>
                ))}
              {filtering && (
                <button type="button" className="btn btn-ghost" onClick={p.onClear}>
                  <X aria-hidden /> Clear filters
                </button>
              )}
            </div>
          )}
          {tags.length > 0 && (
            <div id={tagPanelId} hidden={!tagsOpen} className="fade-up flex flex-wrap gap-2" role="group" aria-label="Filter by tag">
              {[...shownTags.map((t) => t.tag), ...selectedHidden].map((t) => {
                const count = tags.find((x) => x.tag === t)?.count ?? 0
                const on = filters.tags.includes(t)
                return (
                  <button key={t} type="button" className="chip" aria-pressed={on} onClick={() => p.onTag(t)}>
                    {on && <Check aria-hidden />}#{t} <span className="count">{count}</span>
                  </button>
                )
              })}
              {tags.length > TAGS_COLLAPSED && (
                <button type="button" className="btn btn-ghost" onClick={() => setAllTags((v) => !v)}>
                  {allTags ? "Show fewer" : `Show all ${tags.length}`}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {all.length === 0 ? (
        <Empty
          title="The shelf is empty"
          body={
            <>
              Add your first artifact: <code className="rounded bg-sunken px-1.5 py-0.5 font-mono text-sm">./shelf add my-app.html</code>, then push.
            </>
          }
        />
      ) : results.length === 0 && p.hiddenFeatured === 0 ? (
        <Empty
          title="Nothing matches"
          body={filters.query.trim() ? <>No artifact matches “{filters.query.trim()}” with these filters.</> : <>No artifact matches this combination of filters.</>}
          action={
            <button type="button" className="btn btn-secondary" onClick={p.onClear}>
              <X aria-hidden /> Clear all filters
            </button>
          }
        />
      ) : results.length > 0 ? (
        <ul className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3" aria-label="Artifacts">
          {results.map((a, i) => (
            <li key={a.slug}>
              <ArtifactCard artifact={a} onDetails={p.onDetails} eager={i < 3 && p.hiddenFeatured === 0} />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

function Empty({ title, body, action }: { title: string; body: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line px-6 py-14 text-center">
      <p className="font-display text-xl font-semibold">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-muted">{body}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
