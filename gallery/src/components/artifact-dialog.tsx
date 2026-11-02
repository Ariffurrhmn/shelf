import { ArrowUpRight, Check, Link2 } from "lucide-react"
import { useState } from "react"

import { Thumb } from "@/components/artifact-card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { KIND_META, formatDate } from "@/lib/kinds"
import type { Artifact } from "@/types"

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[6.5rem_1fr] gap-2 py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  )
}

export function ArtifactDialog({ artifact, onClose }: { artifact: Artifact | null; onClose: () => void }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    if (!artifact) return
    const abs = new URL(artifact.url, window.location.href).toString()
    try {
      await navigator.clipboard.writeText(abs)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      window.prompt("Copy this link", abs)
    }
  }

  return (
    <Dialog open={artifact !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-xl">
        {artifact && (
          <>
            <DialogHeader>
              <DialogTitle>{artifact.title}</DialogTitle>
              <DialogDescription>{artifact.description}</DialogDescription>
            </DialogHeader>
            <Thumb artifact={artifact} className="rounded-md border" />
            <dl className="divide-y">
              <Row label="Kind">{KIND_META[artifact.kind].label.replace(/s$/, "")}</Row>
              <Row label="Created">{formatDate(artifact.created)}</Row>
              <Row label="Built with">{artifact.tool}</Row>
              <Row label="Storage">
                {artifact.storage === "local" ? "Keeps data in your browser only" : "Keeps nothing"}
              </Row>
              <Row label="Network">
                {artifact.network.length ? (
                  <span className="flex flex-wrap gap-1.5">
                    {artifact.network.map((n) => (
                      <Badge key={n} variant="outline" className="font-mono font-normal">
                        {n}
                      </Badge>
                    ))}
                  </span>
                ) : (
                  "Makes no requests"
                )}
              </Row>
              {artifact.tags.length > 0 && (
                <Row label="Tags">
                  <span className="flex flex-wrap gap-1.5">
                    {artifact.tags.map((t) => (
                      <Badge key={t} variant="secondary" className="font-normal">
                        {t}
                      </Badge>
                    ))}
                  </span>
                </Row>
              )}
              {artifact.notes && <Row label="Notes">{artifact.notes}</Row>}
            </dl>
            <DialogFooter>
              <Button variant="outline" onClick={copy}>
                {copied ? <Check /> : <Link2 />} {copied ? "Copied" : "Copy link"}
              </Button>
              <Button asChild>
                <a href={artifact.url}>
                  Open <ArrowUpRight />
                </a>
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
