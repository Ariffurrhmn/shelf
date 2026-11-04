import { ArrowDown } from "lucide-react"

import { jumpTo } from "@/components/header"
import { formatDate, plural } from "@/lib/format"
import type { Artifact } from "@/types"

/** Numbers come from the loaded manifest only; nothing here is hard-coded. */
function Stats({ artifacts, generated }: { artifacts: Artifact[]; generated: string }) {
  const kinds = new Set(artifacts.map((a) => a.kind)).size
  const installable = artifacts.filter((a) => a.install).length
  const day = generated.slice(0, 10)
  const parts = [
    plural(artifacts.length, "project"),
    plural(kinds, "category", "categories"),
    installable > 0 ? `${installable} installable` : null,
    /^\d{4}-\d{2}-\d{2}$/.test(day) ? `updated ${formatDate(day)}` : null,
  ].filter(Boolean)
  return <p className="mono-meta">{parts.join("  ·  ")}</p>
}

export function Hero({ artifacts, generated }: { artifacts: Artifact[] | null; generated?: string }) {
  return (
    <section className="wrap pt-12 pb-10 sm:pt-20 sm:pb-14" aria-labelledby="hero-title">
      <p className="eyebrow">A personal digital playground</p>
      <h1 id="hero-title" className="mt-4 max-w-3xl text-[clamp(2.25rem,5.5vw+0.5rem,4.25rem)] leading-[1.03] font-semibold">
        Small experiments. <span className="text-muted">Useful creations.</span>
      </h1>
      <p className="mt-5 max-w-xl text-lg text-muted">
        A growing collection of little apps, creative experiments, and interactive ideas — built, collected, and shared.
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-4">
        <a
          href="#explore"
          onClick={(e) => {
            e.preventDefault()
            jumpTo("explore")
          }}
          className="btn btn-primary"
        >
          Explore the collection <ArrowDown aria-hidden />
        </a>
        <div className="min-h-5">{artifacts && generated && artifacts.length > 0 && <Stats artifacts={artifacts} generated={generated} />}</div>
      </div>
    </section>
  )
}
