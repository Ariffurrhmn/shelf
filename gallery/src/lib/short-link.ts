import { useState } from "react"

import type { Artifact } from "@/types"

/** Absolute short link for an artifact, or its full URL when it has no code. */
export function shortUrl(artifact: Artifact): string {
  const path = artifact.short ?? artifact.url
  return new URL(path, window.location.href.split("#")[0]).toString()
}

/** The same link without "https://", which is how it is typed or read out. */
export function shortLabel(artifact: Artifact): string {
  return shortUrl(artifact).replace(/^https?:\/\//, "")
}

/** Copies `text` and reports "copied" for a moment. Falls back to a prompt. */
export function useCopy() {
  const [copied, setCopied] = useState(false)
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      window.prompt("Copy this link", text)
    }
  }
  return { copied, copy }
}
