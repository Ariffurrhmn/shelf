import { ArrowUpRight, Check, Download, Info, Link2 } from "lucide-react"

import { Thumb } from "@/components/thumb"
import { useCopy } from "@/hooks/use-copy"
import { cx } from "@/lib/cx"
import { formatDate } from "@/lib/format"
import { KIND_META, STATUS_LABEL } from "@/lib/kinds"
import { shareUrl } from "@/lib/url"
import type { Artifact } from "@/types"

interface Props {
  artifact: Artifact
  onDetails: (a: Artifact) => void
  /** Larger type, used in the Featured strip. */
  feature?: boolean
  /** Image beside the text on wide screens (a lone featured project). */
  wide?: boolean
  /** Load the screenshot immediately (above the fold). */
  eager?: boolean
}

/**
 * One project. The title is the single link to the project and is stretched over the whole card,
 * so the card is one big, obvious target; the action buttons sit above that layer. There are no
 * nested interactive elements and the tab order is: title, Open, Details, Copy link (the first two go to the same place).
 */
export function ProjectCard({ artifact, onDetails, feature = false, wide = false, eager = false }: Props) {
  const { copied, copy } = useCopy()
  const kind = KIND_META[artifact.kind]
  const KindIcon = kind.icon
  const sizes = wide
    ? "(min-width: 768px) 560px, 92vw"
    : feature
      ? "(min-width: 768px) 46vw, 92vw"
      : "(min-width: 1024px) 380px, (min-width: 640px) 46vw, 92vw"

  return (
    <article className={cx("card h-full", wide && "md:flex-row")}>
      <div className={cx(wide && "md:w-[58%] md:shrink-0")}>
        <Thumb artifact={artifact} sizes={sizes} eager={eager} />
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="mono-meta inline-flex items-center gap-1.5 !text-ink">
            <KindIcon className="size-3.5" aria-hidden />
            {kind.label}
          </span>
          {artifact.status && <span className="mono-meta">{STATUS_LABEL[artifact.status]}</span>}
          <span className="mono-meta ml-auto">
            <time dateTime={artifact.created}>{formatDate(artifact.created)}</time>
          </span>
        </div>

        <h3 className={cx("font-semibold leading-tight", feature ? "text-2xl" : "text-xl")}>
          <a href={artifact.url} className="stretched hover:text-accent">
            {artifact.title}
          </a>
        </h3>

        {artifact.description && (
          <p className={cx("text-muted", feature ? "line-clamp-3" : "line-clamp-2")}>{artifact.description}</p>
        )}

        {(artifact.tool || artifact.install) && (
          <p className="mono-meta mt-auto flex flex-wrap items-center gap-x-3 gap-y-1">
            {artifact.tool && <span>Built with {artifact.tool}</span>}
            {artifact.install && (
              <span className="inline-flex items-center gap-1">
                <Download className="size-3" aria-hidden /> Installable
              </span>
            )}
          </p>
        )}

        <div className="above mt-1 flex items-center gap-2">
          <a href={artifact.url} className="btn btn-primary flex-1" aria-label={`Open ${artifact.title}`}>
            Open project <ArrowUpRight aria-hidden />
          </a>
          <button type="button" className="btn btn-secondary" onClick={() => onDetails(artifact)} aria-label={`Details for ${artifact.title}`}>
            <Info aria-hidden /> <span>Details</span>
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-icon"
            onClick={() => copy(shareUrl(artifact, window.location.href))}
            aria-label={`Copy link to ${artifact.title}`}
            title={copied ? "Copied" : "Copy link"}
          >
            {copied ? <Check aria-hidden /> : <Link2 aria-hidden />}
          </button>
        </div>
      </div>
    </article>
  )
}
