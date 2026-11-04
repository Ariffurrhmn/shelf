import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { parseHash, resolveSlug } from "@/lib/url"
import type { Artifact } from "@/types"

const MARK = "shelf-details"

/**
 * The details dialog is a real history entry addressed by "#slug":
 *  - opening it from the gallery pushes an entry, so Back closes it and Forward reopens it;
 *  - a direct link (or a refresh) opens it straight away;
 *  - closing a dialog that was opened from the gallery goes Back; closing one that was opened by
 *    a direct link just removes the hash, so the visitor is never sent off the site;
 *  - old slugs (aliases) open the right artifact and the address is corrected to the current slug.
 */
export function useDetailsRoute(artifacts: Artifact[]) {
  const [slug, setSlug] = useState<string | null>(() => parseHash(window.location.hash))
  const opener = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const sync = () => setSlug(parseHash(window.location.hash))
    window.addEventListener("popstate", sync)
    window.addEventListener("hashchange", sync)
    return () => {
      window.removeEventListener("popstate", sync)
      window.removeEventListener("hashchange", sync)
    }
  }, [])

  const active = useMemo(() => resolveSlug(slug, artifacts), [slug, artifacts])

  useEffect(() => {
    if (active && slug && slug !== active.slug) {
      window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}#${active.slug}`)
      setSlug(active.slug)
    }
  }, [active, slug])

  useEffect(() => {
    document.title = active ? `${active.title} · Shelf` : "Shelf · Small experiments. Useful creations."
  }, [active])

  const open = useCallback((a: Artifact) => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    window.history.pushState({ [MARK]: true }, "", `${window.location.pathname}${window.location.search}#${a.slug}`)
    setSlug(a.slug)
  }, [])

  const close = useCallback(() => {
    if (window.history.state?.[MARK]) {
      window.history.back() // popstate then clears the slug
    } else {
      window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search)
      setSlug(null)
    }
  }, [])

  /** Puts focus back on the control that opened the dialog (or on the page, after a direct link or Back/Forward). */
  const restoreFocus = useCallback(() => {
    const el = opener.current
    opener.current = null
    const target = el && el.isConnected ? el : document.getElementById("main")
    target?.focus({ preventScroll: true })
  }, [])

  return { active, open, close, restoreFocus }
}
