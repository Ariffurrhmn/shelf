import { useCallback, useEffect, useRef, useState } from "react"

import { announce } from "@/lib/announce"

/** Copies text and reports "copied" for a moment (visually and to screen readers). */
export function useCopy() {
  const [copied, setCopied] = useState(false)
  const timer = useRef<number>(0)
  useEffect(() => () => window.clearTimeout(timer.current), [])

  const copy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      window.prompt("Copy this link", text) // clipboard blocked (insecure origin, old browser)
      return
    }
    setCopied(true)
    announce("Link copied to clipboard")
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setCopied(false), 1800)
  }, [])

  return { copied, copy }
}
