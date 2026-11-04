import type { Artifact } from "@/types"

export function make(over: Partial<Artifact> & { slug: string }): Artifact {
  return {
    title: over.slug,
    description: "A thing.",
    created: "2026-01-01",
    tool: "Claude",
    kind: "app",
    tags: [],
    storage: "none",
    network: [],
    url: `artifacts/${over.slug}/`,
    short: null,
    thumbnail: null,
    install: false,
    icon: null,
    color: null,
    ...over,
  }
}

export const SAMPLE: Artifact[] = [
  make({ slug: "pomodoro-timer", title: "Pomodoro timer", created: "2026-10-20", tags: ["timer", "productivity"], install: true, short: "74ng" }),
  make({ slug: "snake-game", title: "Snake", created: "2026-10-24", kind: "game", tags: ["game", "arcade"], install: true }),
  make({ slug: "url-shortener", title: "URL shortener", created: "2026-11-03", tags: ["links", "utility"], tool: "ChatGPT", notes: "Café-style helper", aliases: ["shorty"] }),
  make({ slug: "intro-slides", title: "Shelf: a short introduction", created: "2026-11-02", kind: "presentation", tags: ["slides"], featured: true }),
  make({ slug: "zeta", title: "zeta 10", created: "2026-05-05" }),
  make({ slug: "zeta-2", title: "zeta 9", created: "2026-05-05" }),
]
