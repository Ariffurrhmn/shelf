import { ArtifactCard } from "@/components/artifact-card"
import { plural } from "@/lib/format"
import type { Artifact } from "@/types"

/** Hidden unless at least one artifact sets "featured": true in its metadata. */
export function Featured({ artifacts, onDetails }: { artifacts: Artifact[]; onDetails: (a: Artifact) => void }) {
  if (artifacts.length === 0) return null
  const alone = artifacts.length === 1
  return (
    <section aria-labelledby="featured-title" className="wrap pb-14">
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <h2 id="featured-title" className="text-2xl font-semibold sm:text-3xl">
          Featured
        </h2>
        <span className="mono-meta">{plural(artifacts.length, "pick")}</span>
      </div>
      <ul className={alone ? "grid grid-cols-1 gap-6" : "grid grid-cols-1 gap-6 md:grid-cols-2"}>
        {artifacts.map((a, i) => (
          <li key={a.slug}>
            <ArtifactCard artifact={a} onDetails={onDetails} feature wide={alone} eager={i < 2} />
          </li>
        ))}
      </ul>
    </section>
  )
}
