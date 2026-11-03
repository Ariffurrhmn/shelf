import { ArrowUpRight, ChevronUp, Download, HardDrive, Monitor, Smartphone, Wifi, WifiOff, X, AppWindow, RefreshCw } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import type { Artifact } from "@/types"

/** Opens the artifact and shows its one-off install prompt (see tools/build/pwa.py). */
export const installUrl = (a: Artifact) => `${a.url}#install`

const PLATFORMS = [
  { icon: Monitor, name: "Chrome and Edge on desktop", how: "Install prompt, or the install icon in the address bar" },
  { icon: Smartphone, name: "Android (Chrome, Edge)", how: "Install prompt, or Menu → Install app" },
  { icon: Smartphone, name: "iPhone and iPad (Safari)", how: "Share → Add to Home Screen" },
  { icon: Monitor, name: "Mac (Safari 17 and later)", how: "File → Add to Dock" },
]

/**
 * The "Installable" strip at the bottom of an artifact card. Hovering it (or focusing it,
 * or tapping it on a touch screen) opens a panel over the card with what the installed app
 * can do, where it can be installed, and the Install button.
 */
export function InstallInfo({ artifact }: { artifact: Artifact }) {
  const [pinned, setPinned] = useState(false)
  if (!artifact.install) return null

  const live = artifact.network.filter((n) => !/^(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|unpkg\.com|code\.jquery\.com|fonts\.(googleapis|gstatic)\.com)$/.test(n))
  const show =
    "data-[open=true]:visible data-[open=true]:translate-y-0 data-[open=true]:opacity-100 " +
    "group-hover/install:visible group-hover/install:translate-y-0 group-hover/install:opacity-100 " +
    "group-has-focus-visible/install:visible group-has-focus-visible/install:translate-y-0 group-has-focus-visible/install:opacity-100"

  return (
    <div
      className="group/install"
      onPointerLeave={(e) => e.pointerType === "mouse" && setPinned(false)}
      onKeyDown={(e) => e.key === "Escape" && setPinned(false)}
    >
      <button
        type="button"
        onClick={() => setPinned((p) => !p)}
        aria-expanded={pinned}
        aria-controls={`install-${artifact.slug}`}
        className="text-muted-foreground hover:text-foreground focus-visible:ring-ring/50 flex w-full items-center justify-between gap-2 border-t px-4 py-2 text-xs outline-none focus-visible:ring-[3px]"
      >
        <span className="flex items-center gap-1.5">
          <Download className="size-3.5" aria-hidden /> Installable app · works offline
        </span>
        <span className="flex items-center gap-1">
          Details <ChevronUp className="size-3.5" aria-hidden />
        </span>
      </button>

      <div
        id={`install-${artifact.slug}`}
        data-open={pinned}
        role="region"
        aria-label={`Install ${artifact.title}`}
        className={`bg-card invisible absolute inset-x-0 bottom-0 z-10 flex max-h-full translate-y-2 flex-col gap-3 overflow-y-auto border-t p-4 opacity-0 shadow-[0_-8px_24px_-12px_rgba(0,0,0,0.25)] transition duration-150 ${show}`}
      >
        <div className="flex items-start justify-between gap-2">
          <p className="flex items-center gap-2 font-medium">
            <Download className="size-4" aria-hidden /> Install {artifact.title}
          </p>
          <button type="button" onClick={() => setPinned(false)} aria-label="Close details" className="text-muted-foreground hover:text-foreground -m-1 rounded p-1 pointer-fine:hidden">
            <X className="size-4" />
          </button>
        </div>

        <section>
          <h3 className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">What you get</h3>
          <ul className="space-y-1 text-sm">
            <li className="flex gap-2">
              <AppWindow className="mt-0.5 size-4 shrink-0" aria-hidden /> Opens in its own window, like a normal app
            </li>
            <li className="flex gap-2">
              {live.length ? <WifiOff className="mt-0.5 size-4 shrink-0" aria-hidden /> : <Wifi className="mt-0.5 size-4 shrink-0" aria-hidden />}
              {live.length ? `Works offline, except what needs ${live.join(", ")}` : "Works fully offline once installed"}
            </li>
            <li className="flex gap-2">
              <HardDrive className="mt-0.5 size-4 shrink-0" aria-hidden />
              {artifact.storage === "local" ? "Keeps its data on this device only" : "Keeps nothing; no data is saved"}
            </li>
            <li className="flex gap-2">
              <RefreshCw className="mt-0.5 size-4 shrink-0" aria-hidden /> Updates itself when the shelf changes
            </li>
          </ul>
        </section>

        <section>
          <h3 className="text-muted-foreground mb-1 text-xs font-medium tracking-wide uppercase">Where it installs</h3>
          <ul className="space-y-1 text-xs">
            {PLATFORMS.map((p) => (
              <li key={p.name} className="flex gap-2">
                <p.icon className="text-muted-foreground mt-0.5 size-3.5 shrink-0" aria-hidden />
                <span>
                  <span className="font-medium">{p.name}:</span> <span className="text-muted-foreground">{p.how}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="text-muted-foreground mt-1 text-xs">Firefox on desktop can't install apps, but the page still opens normally.</p>
        </section>

        <p className="text-muted-foreground text-xs">
          Install opens the app and shows your browser's install prompt at the bottom of the page.
        </p>

        <div className="flex gap-2">
          <Button asChild size="sm" className="flex-1">
            <a href={installUrl(artifact)}>
              <Download /> Install
            </a>
          </Button>
          <Button asChild size="sm" variant="outline">
            <a href={artifact.url}>
              Open <ArrowUpRight />
            </a>
          </Button>
        </div>
      </div>
    </div>
  )
}
