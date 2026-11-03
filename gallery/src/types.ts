export type Kind = "app" | "presentation" | "doc" | "game" | "other"

export interface Artifact {
  slug: string
  title: string
  description: string
  created: string
  tool: string
  kind: Kind
  tags: string[]
  storage: "none" | "local"
  network: string[]
  notes?: string
  /** Relative URL of the artifact entry point, e.g. "artifacts/foo/". */
  url: string
  /** Short code, so the short link is "<site root>/<short>". Null for older manifests. */
  short?: string | null
  /** Relative URL of the thumbnail, or null when none could be generated. */
  thumbnail: string | null
}

export interface Manifest {
  generated: string
  repo?: string
  artifacts: Artifact[]
}
