import { Library, Moon, Search, Sun, X } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { ArtifactCard } from "@/components/artifact-card"
import { ArtifactDialog } from "@/components/artifact-dialog"
import { InstallableSection } from "@/components/installable-section"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useTheme } from "@/hooks/use-theme"
import { KIND_META, KIND_ORDER } from "@/lib/kinds"
import type { Artifact, Kind, Manifest } from "@/types"

type State = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; manifest: Manifest }

function useManifest(): State {
  const [state, setState] = useState<State>({ status: "loading" })
  useEffect(() => {
    let live = true
    fetch("artifacts.json", { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`artifacts.json returned ${r.status}`)
        return r.json() as Promise<Manifest>
      })
      .then((manifest) => live && setState({ status: "ready", manifest }))
      .catch((e: Error) => live && setState({ status: "error", message: e.message }))
    return () => {
      live = false
    }
  }, [])
  return state
}

export default function App() {
  const state = useManifest()
  const { theme, toggle } = useTheme()
  const [query, setQuery] = useState("")
  const [kind, setKind] = useState<Kind | "all">("all")
  const [tag, setTag] = useState<string | null>(null)
  const [open, setOpen] = useState<Artifact | null>(null)

  const artifacts = useMemo(
    () =>
      state.status === "ready"
        ? [...state.manifest.artifacts].sort((a, b) => b.created.localeCompare(a.created) || a.title.localeCompare(b.title))
        : [],
    [state]
  )

  // Deep link: index.html#slug opens that artifact's details.
  useEffect(() => {
    if (!artifacts.length) return
    const sync = () => {
      const slug = window.location.hash.slice(1)
      setOpen(artifacts.find((a) => a.slug === slug) ?? null)
    }
    sync()
    window.addEventListener("hashchange", sync)
    return () => window.removeEventListener("hashchange", sync)
  }, [artifacts])

  function openDetails(a: Artifact | null) {
    setOpen(a)
    const next = a ? `#${a.slug}` : window.location.pathname + window.location.search
    window.history.replaceState(null, "", next)
  }

  const kinds = useMemo(() => {
    const counts = new Map<Kind, number>()
    artifacts.forEach((a) => counts.set(a.kind, (counts.get(a.kind) ?? 0) + 1))
    return KIND_ORDER.filter((k) => counts.has(k)).map((k) => ({ kind: k, count: counts.get(k)! }))
  }, [artifacts])

  const tags = useMemo(() => {
    const counts = new Map<string, number>()
    artifacts.forEach((a) => a.tags.forEach((t) => counts.set(t, (counts.get(t) ?? 0) + 1)))
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([t]) => t)
  }, [artifacts])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return artifacts.filter((a) => {
      if (kind !== "all" && a.kind !== kind) return false
      if (tag && !a.tags.includes(tag)) return false
      if (!q) return true
      return [a.title, a.description, a.tool, a.notes ?? "", ...a.tags].some((s) => s.toLowerCase().includes(q))
    })
  }, [artifacts, query, kind, tag])

  const filtering = query !== "" || kind !== "all" || tag !== null
  const clear = () => {
    setQuery("")
    setKind("all")
    setTag(null)
  }

  return (
    <div className="min-h-dvh">
      <header className="bg-background/80 sticky top-0 z-40 border-b backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <Library className="size-5" aria-hidden />
            <span className="text-lg">Shelf</span>
          </div>
          <div className="relative ml-auto w-full max-w-xs">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" aria-hidden />
            <Input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search artifacts"
              aria-label="Search artifacts"
              className="pl-8"
            />
          </div>
          <Button variant="ghost" size="icon" onClick={toggle} aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}>
            {theme === "dark" ? <Sun /> : <Moon />}
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <section className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">A personal shelf for small things.</h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Apps, games and slide decks made with AI tools. Each one is a single HTML file you can open by link, with no sign-in.
          </p>
        </section>

        {state.status === "ready" && <InstallableSection artifacts={artifacts} />}

        {state.status === "loading" && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-80" />
            ))}
          </div>
        )}

        {state.status === "error" && (
          <div role="alert" className="border-destructive/40 text-destructive rounded-lg border p-4 text-sm">
            Could not load the artifact list ({state.message}). If you opened this file directly from disk, serve the
            folder over HTTP instead.
          </div>
        )}

        {state.status === "ready" && (
          <>
            {artifacts.length > 0 && (
              <div className="mb-6 space-y-3">
                <ToggleGroup
                  type="single"
                  variant="outline"
                  value={kind}
                  onValueChange={(v) => setKind((v || "all") as Kind | "all")}
                  className="flex-wrap"
                  aria-label="Filter by kind"
                >
                  <ToggleGroupItem value="all" className="px-3">
                    All <span className="text-muted-foreground text-xs">{artifacts.length}</span>
                  </ToggleGroupItem>
                  {kinds.map(({ kind: k, count }) => {
                    const Icon = KIND_META[k].icon
                    return (
                      <ToggleGroupItem key={k} value={k} className="px-3">
                        <Icon aria-hidden /> {KIND_META[k].label}{" "}
                        <span className="text-muted-foreground text-xs">{count}</span>
                      </ToggleGroupItem>
                    )
                  })}
                </ToggleGroup>
                {tags.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter by tag">
                    {tags.map((t) => (
                      <button key={t} type="button" onClick={() => setTag(tag === t ? null : t)} aria-pressed={tag === t} className="rounded-md outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50">
                        <Badge variant={tag === t ? "default" : "outline"} className="cursor-pointer font-normal">
                          #{t}
                        </Badge>
                      </button>
                    ))}
                    {filtering && (
                      <Button variant="link" size="sm" onClick={clear}>
                        <X /> Clear filters
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}

            {artifacts.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-10 text-center">
                <p className="text-foreground font-medium">The shelf is empty.</p>
                <p className="mt-1 text-sm">Add a folder under <code>artifacts/</code> and push.</p>
              </div>
            ) : visible.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-10 text-center">
                <p className="text-foreground font-medium">Nothing matches.</p>
                <Button variant="link" onClick={clear}>
                  Clear filters
                </Button>
              </div>
            ) : (
              <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-label="Artifacts">
                {visible.map((a) => (
                  <li key={a.slug} className="flex">
                    <div className="flex w-full">
                      <ArtifactCard artifact={a} onDetails={openDetails} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </main>

      <footer className="text-muted-foreground mx-auto max-w-6xl border-t px-4 py-6 text-sm">
        <p>
          {state.status === "ready" && (
            <>
              {artifacts.length} artifact{artifacts.length === 1 ? "" : "s"}
              {filtering && ` (${visible.length} shown)`} · updated{" "}
              {new Date(state.manifest.generated).toLocaleDateString()}
              {state.manifest.repo && (
                <>
                  {" "}
                  ·{" "}
                  <a className="underline underline-offset-4" href={state.manifest.repo}>
                    source
                  </a>
                </>
              )}
            </>
          )}
        </p>
      </footer>

      <ArtifactDialog artifact={open} onClose={() => openDetails(null)} />
    </div>
  )
}
