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
  /** Relative URL of the thumbnail, or null when none could be generated. */
  thumbnail: string | null
  /** True when the build made this artifact installable as a PWA. */
  install: boolean
  /** Relative URL of the generated app icon, when installable. */
  icon: string | null
  /** Theme colour of the installed app, when installable. */
  color: string | null
}

export interface Manifest {
  generated: string
  repo?: string
  artifacts: Artifact[]
}
