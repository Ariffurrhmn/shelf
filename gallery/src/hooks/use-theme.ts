import { useCallback, useEffect, useState } from "react"

type Theme = "light" | "dark"

function initial(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light"
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initial)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
  }, [theme])

  const toggle = useCallback(() => {
    setTheme((t) => {
      const next: Theme = t === "dark" ? "light" : "dark"
      try {
        localStorage.setItem("shelf-theme", next)
      } catch {
        /* storage may be unavailable; the choice just will not persist */
      }
      return next
    })
  }, [])

  return { theme, toggle }
}
