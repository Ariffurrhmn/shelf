import { RefreshCw } from "lucide-react"
import { useDeferredValue, useEffect, useMemo, useRef } from "react"

import { Explore } from "@/components/explore"
import { Featured } from "@/components/featured"
import { Footer } from "@/components/footer"
import { Header } from "@/components/header"
import { Hero } from "@/components/hero"
import { ArtifactDialog } from "@/components/artifact-dialog"
import { useBrowse } from "@/hooks/use-browse"
import { useDetailsRoute } from "@/hooks/use-details-route"
import { useManifest } from "@/hooks/use-manifest"
import { useTheme } from "@/hooks/use-theme"
import { useAnnouncement } from "@/lib/announce"
import { arrange, filterArtifacts, hasActiveFilters, sortArtifacts } from "@/lib/filter"
import type { Artifact } from "@/types"

const NONE: Artifact[] = []

function isTyping(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false
  return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)
}

export default function App() {
  const state = useManifest()
  const { theme, toggle } = useTheme()
  const browse = useBrowse()
  const announcement = useAnnouncement()
  const searchRef = useRef<HTMLInputElement>(null)

  const all = state.status === "ready" ? state.manifest.artifacts : NONE
  const details = useDetailsRoute(all)

  const deferred = useDeferredValue(browse.filters)
  const filtering = hasActiveFilters(deferred)
  const sorted = useMemo(() => sortArtifacts(all, browse.sort), [all, browse.sort])
  const visible = useMemo(() => filterArtifacts(sorted, deferred), [sorted, deferred])
  const { featured, grid } = useMemo(() => arrange(sorted, visible, filtering), [sorted, visible, filtering])

  // "/" focuses search, unless the visitor is already typing somewhere or a dialog is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target) || details.active) return
      const input = searchRef.current
      if (!input) return
      e.preventDefault()
      input.focus()
      input.select()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [details.active])

  const repo = state.status === "ready" ? state.manifest.repo : undefined

  return (
    <div className="min-h-dvh">
      <Header theme={theme} onToggleTheme={toggle} repo={repo} />

      <main id="main" tabIndex={-1} className="outline-none">
        <Hero />

        {state.status === "loading" && (
          <section className="wrap pb-16" aria-busy="true" aria-label="Loading artifacts">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="overflow-hidden rounded-lg border border-line bg-surface">
                  <div className="skeleton aspect-[8/5]" />
                  <div className="space-y-3 p-5">
                    <div className="skeleton h-3 w-1/3 rounded" />
                    <div className="skeleton h-5 w-2/3 rounded" />
                    <div className="skeleton h-4 w-full rounded" />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {state.status === "error" && (
          <section className="wrap pb-16">
            <div role="alert" className="rounded-lg border border-danger/50 p-6">
              <p className="font-display text-lg font-semibold text-danger">The artifact list could not be loaded</p>
              <p className="mt-2 text-muted">
                {state.message}. If you opened this file straight from disk, serve the folder over HTTP instead (for example{" "}
                <code className="rounded bg-sunken px-1.5 py-0.5 font-mono text-sm">./shelf preview</code>).
              </p>
              <button type="button" className="btn btn-secondary mt-4" onClick={state.retry}>
                <RefreshCw aria-hidden /> Try again
              </button>
            </div>
          </section>
        )}

        {state.status === "ready" && (
          <>
            <Featured artifacts={featured} onDetails={details.open} />
            <Explore
              all={all}
              results={grid}
              hiddenFeatured={featured.length}
              filters={browse.filters}
              sort={browse.sort}
              searchRef={searchRef}
              onQuery={browse.setQuery}
              onKind={browse.setKind}
              onTag={browse.toggleTag}
              onInstallable={browse.setInstallable}
              onSort={browse.setSort}
              onClear={browse.clear}
              onDetails={details.open}
            />
          </>
        )}
      </main>

      <Footer />

      <ArtifactDialog active={details.active} onClose={details.close} onCloseFocus={details.restoreFocus} />
      <div className="sr-only-live" role="status" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>
    </div>
  )
}
