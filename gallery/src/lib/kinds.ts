import { AppWindow, FileText, Gamepad2, Presentation, Shapes, type LucideIcon } from "lucide-react"

import type { Kind, Status } from "@/types"

export const KIND_META: Record<Kind, { label: string; plural: string; icon: LucideIcon }> = {
  app: { label: "App", plural: "Apps", icon: AppWindow },
  presentation: { label: "Presentation", plural: "Presentations", icon: Presentation },
  game: { label: "Game", plural: "Games", icon: Gamepad2 },
  doc: { label: "Document", plural: "Documents", icon: FileText },
  other: { label: "Other", plural: "Other", icon: Shapes },
}

export const KIND_ORDER: Kind[] = ["app", "game", "presentation", "doc", "other"]

export const STATUS_LABEL: Record<Status, string> = {
  experiment: "Experiment",
  finished: "Finished",
}

export function isKind(value: string): value is Kind {
  return value in KIND_META
}
