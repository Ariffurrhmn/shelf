import { useCallback, useEffect, useState } from "react"

import { readPref, writePref } from "@/lib/storage"

type Theme = "light" | "dark"
const KEY = "shelf-theme"

function current(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light"
}

function apply(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark")
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#181a20" : "#fafaf8")
}

/** Follows the system theme until the visitor picks one; the pick is then remembered. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(current)

  useEffect(() => {
    if (readPref(KEY)) return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => {
      if (readPref(KEY)) return
      const next: Theme = mq.matches ? "dark" : "light"
      apply(next)
      setTheme(next)
    }
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [])

  const toggle = useCallback(() => {
    const next: Theme = current() === "dark" ? "light" : "dark"
    apply(next)
    writePref(KEY, next)
    setTheme(next)
  }, [])

  return { theme, toggle }
}
