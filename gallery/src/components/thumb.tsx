import { useState } from "react"

import { KIND_META } from "@/lib/kinds"
import { hueFromSlug } from "@/lib/format"
import type { Artifact } from "@/types"

/**
 * The project's screenshot at a fixed 8:5 ratio (so nothing shifts while images load).
 * Without a screenshot, or if it fails to load, a quiet placeholder tinted from the slug is shown.
 */
export function Thumb({ artifact, sizes, eager = false }: { artifact: Artifact; sizes: string; eager?: boolean }) {
  const [failed, setFailed] = useState(false)
  const Icon = KIND_META[artifact.kind].icon
  const src = artifact.thumbnail
  const show = src && !failed
  const srcSet = artifact.thumbnailSmall && src ? `${artifact.thumbnailSmall} 640w, ${src} 1280w` : undefined

  return (
    <div className="thumb">
      {show ? (
        <img
          src={src}
          srcSet={srcSet}
          sizes={srcSet ? sizes : undefined}
          width={artifact.thumbnailWidth ?? 1280}
          height={artifact.thumbnailHeight ?? 800}
          alt={`Screenshot of ${artifact.title}`}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : "auto"}
          decoding="async"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="ph" style={{ "--h": hueFromSlug(artifact.slug) } as React.CSSProperties} role="img" aria-label={`No screenshot yet for ${artifact.title}`}>
          <div className="flex flex-col items-center gap-2 px-4 text-center">
            <Icon className="size-8 opacity-70" aria-hidden />
            <span className="font-display text-xl font-semibold tracking-tight">{artifact.title.slice(0, 40)}</span>
          </div>
        </div>
      )}
    </div>
  )
}
