import { ArrowUpRight, Moon, Sun } from "lucide-react"

import { Logo } from "@/components/logo"
import { SpecButton } from "@/components/spec-button"

interface Props {
  theme: "light" | "dark"
  onToggleTheme: () => void
  repo?: string
}

/** Scrolls to a section and moves focus there, without touching the URL hash (which is used for artifact links). */
export function jumpTo(id: string) {
  const el = document.getElementById(id)
  if (!el) return
  el.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" })
  el.focus({ preventScroll: true })
}

export function Header({ theme, onToggleTheme, repo }: Props) {
  return (
    <header className="bg-bg sticky top-0 z-40 border-b border-line">
      <a
        href="#main"
        onClick={(e) => {
          e.preventDefault()
          jumpTo("main")
        }}
        className="btn btn-primary fixed top-2 left-2 z-50 -translate-y-20 focus:translate-y-0"
      >
        Skip to content
      </a>
      <div className="wrap flex h-14 items-center gap-1 sm:gap-2">
        <a href="./" className="-ml-1 flex items-center gap-2.5 rounded-md p-1 font-display text-lg font-semibold tracking-tight" aria-label="Shelf home">
          <Logo />
          <span>Shelf</span>
        </a>
        <nav aria-label="Primary" className="ml-auto flex items-center gap-0.5 sm:gap-1">
          <SpecButton className="btn btn-ghost px-3" />
          {repo && (
            <a href={repo} className="btn btn-ghost hidden px-3 sm:inline-flex" rel="noopener noreferrer">
              Source <ArrowUpRight aria-hidden />
            </a>
          )}
          <button
            type="button"
            onClick={onToggleTheme}
            className="btn btn-ghost btn-icon"
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? <Sun aria-hidden /> : <Moon aria-hidden />}
          </button>
        </nav>
      </div>
    </header>
  )
}
