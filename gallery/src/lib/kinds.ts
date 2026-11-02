import { AppWindow, FileText, Gamepad2, Presentation, Shapes, type LucideIcon } from "lucide-react"

import type { Kind } from "@/types"

export const KIND_META: Record<Kind, { label: string; icon: LucideIcon }> = {
  app: { label: "Apps", icon: AppWindow },
  presentation: { label: "Slides", icon: Presentation },
  doc: { label: "Docs", icon: FileText },
  game: { label: "Games", icon: Gamepad2 },
  other: { label: "Other", icon: Shapes },
}

export const KIND_ORDER: Kind[] = ["app", "presentation", "game", "doc", "other"]

export function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00")
  if (Number.isNaN(d.getTime())) return iso
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(d)
}
