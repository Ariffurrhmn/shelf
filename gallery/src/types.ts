export type Kind = "app" | "presentation" | "doc" | "game" | "other"
export type Status = "experiment" | "finished"

/** One entry of artifacts.json, written by tools/build/build.py. */
export interface Artifact {
  slug: string
  title: string
  description: string
  /** YYYY-MM-DD */
  created: string
  tool: string
  /** The category shown in the gallery. */
  kind: Kind
  tags: string[]
  storage: "none" | "local"
  network: string[]
  notes?: string | null
  /** Why it was made. Optional. */
  why?: string | null
  status?: Status | null
  featured?: boolean
  /** YYYY-MM-DD of the last meaningful change. Optional. */
  updated?: string | null
  /** Link to the conversation or repository it came from. Optional. */
  source?: string | null
  /** Earlier slugs. Old links such as #old-slug keep opening this artifact. */
  aliases?: string[]
  /** Relative URL of the artifact entry point, e.g. "artifacts/foo/". */
  url: string
  /** Short code, so the short link is "<site root>/<short>". */
  short?: string | null
  /** Relative URLs of the 1280x800 and 640x400 WebP thumbnails, or null when none exists. */
  thumbnail: string | null
  thumbnailSmall?: string | null
  thumbnailWidth?: number | null
  thumbnailHeight?: number | null
  /** True when the build made this artifact installable as a PWA. */
  install: boolean
  icon: string | null
  color: string | null
}

export interface Manifest {
  generated: string
  repo?: string
  artifacts: Artifact[]
}

export type SortKey = "newest" | "oldest" | "title-asc" | "title-desc"

export interface Filters {
  query: string
  kind: Kind | "all"
  tags: string[]
  installable: boolean
}
