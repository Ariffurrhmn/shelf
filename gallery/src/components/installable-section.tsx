import { Download, WifiOff } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { KIND_META } from "@/lib/kinds"
import type { Artifact } from "@/types"

/** Link that opens the artifact and shows its one-off install prompt (see tools/build/pwa.py). */
export const installUrl = (a: Artifact) => `${a.url}#install`

function AppIcon({ artifact }: { artifact: Artifact }) {
  const [failed, setFailed] = useState(false)
  const Icon = KIND_META[artifact.kind].icon
  if (artifact.icon && !failed) {
    return (
      <img
        src={artifact.icon}
        alt=""
        width={56}
        height={56}
        loading="lazy"
        onError={() => setFailed(true)}
        className="size-14 shrink-0 rounded-xl border"
      />
    )
  }
  return (
    <div className="bg-muted text-muted-foreground flex size-14 shrink-0 items-center justify-center rounded-xl border">
      <Icon className="size-6" aria-hidden />
    </div>
  )
}

export function InstallableSection({ artifacts }: { artifacts: Artifact[] }) {
  const apps = artifacts.filter((a) => a.install)
  if (apps.length === 0) return null
  return (
    <section id="installable" aria-labelledby="installable-title" className="mb-10 scroll-mt-20">
      <div className="mb-4">
        <h2 id="installable-title" className="flex items-center gap-2 text-xl font-semibold tracking-tight">
          <Download className="size-5" aria-hidden /> Install to your device
        </h2>
        <p className="text-muted-foreground mt-1 max-w-2xl text-sm">
          These work as apps on desktop and mobile: they open in their own window and keep working without a
          connection. On Chrome, Edge and Android you get an install prompt. On iPhone and iPad, tap Share, then Add
          to Home Screen.
        </p>
      </div>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Installable apps">
        {apps.map((a) => (
          <li key={a.slug} className="bg-card flex min-w-0 items-center gap-3 rounded-xl border p-3">
            <AppIcon artifact={a} />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{a.title}</p>
              <p className="text-muted-foreground flex items-center gap-1 text-xs">
                {a.network.length > 0 ? (
                  <>
                    <WifiOff className="size-3" aria-hidden /> Some features need a connection
                  </>
                ) : (
                  <>Works offline</>
                )}
              </p>
            </div>
            <Button asChild size="sm">
              <a href={installUrl(a)} aria-label={`Install ${a.title}`}>
                <Download /> Install
              </a>
            </Button>
          </li>
        ))}
      </ul>
    </section>
  )
}
