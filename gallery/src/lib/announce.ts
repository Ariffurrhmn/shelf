import { useSyncExternalStore } from "react"

/** A tiny store behind the screen-reader live region: announce("Link copied"). */
let message = ""
const listeners = new Set<() => void>()

export function announce(text: string): void {
  // Toggle a trailing space so repeating the same message is still announced.
  message = message === text ? text + " " : text
  listeners.forEach((l) => l())
}

export function useAnnouncement(): string {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
    () => message,
    () => ""
  )
}
