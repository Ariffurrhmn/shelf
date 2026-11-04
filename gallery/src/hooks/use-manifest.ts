import { useCallback, useEffect, useState } from "react"

import type { Manifest } from "@/types"

export type ManifestState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; manifest: Manifest }

export function useManifest(): ManifestState & { retry: () => void } {
  const [state, setState] = useState<ManifestState>({ status: "loading" })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let live = true
    setState({ status: "loading" })
    fetch("artifacts.json", { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`artifacts.json returned ${r.status}`)
        return r.json() as Promise<Manifest>
      })
      .then((manifest) => {
        if (!manifest || !Array.isArray(manifest.artifacts)) throw new Error("artifacts.json is not in the expected format")
        if (live) setState({ status: "ready", manifest })
      })
      .catch((e: Error) => live && setState({ status: "error", message: e.message }))
    return () => {
      live = false
    }
  }, [attempt])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])
  return { ...state, retry }
}
