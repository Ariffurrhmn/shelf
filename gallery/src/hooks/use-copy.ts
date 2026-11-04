import { useCallback, useEffect, useRef, useState } from "react"

import { announce } from "@/lib/announce"

/** Copies text and reports "copied" for a moment (visually and to screen readers). */
export function useCopy(message = "Link copied to clipboard") {
  const [copied, setCopied] = useState(false)
  const timer = useRef<number>(0)
  useEffect(() => () => window.clearTimeout(timer.current), [])

  const flash = useCallback(() => {
    setCopied(true)
    announce(message)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setCopied(false), 1800)
  }, [message])

  const copy = useCallback(
    async (text: string) => {
      try {
        await navigator.clipboard.writeText(text)
      } catch {
        window.prompt("Copy this", text) // clipboard blocked (insecure origin, old browser)
        return
      }
      flash()
    },
    [flash]
  )

  /**
   * Copies text that has to be fetched first. The clipboard write starts inside the click and
   * receives a promise for the text, which keeps the user-gesture permission that Safari and
   * Chrome require (a plain fetch-then-writeText can lose it). `fallback` runs if copying fails.
   */
  const copyLoaded = useCallback(
    async (load: () => Promise<string>, fallback?: () => void) => {
      try {
        if (typeof ClipboardItem !== "undefined" && navigator.clipboard?.write) {
          const blob = load().then((t) => new Blob([t], { type: "text/plain" }))
          await navigator.clipboard.write([new ClipboardItem({ "text/plain": blob })])
        } else {
          await navigator.clipboard.writeText(await load())
        }
      } catch {
        fallback?.()
        return
      }
      flash()
    },
    [flash]
  )

  return { copied, copy, copyLoaded }
}
