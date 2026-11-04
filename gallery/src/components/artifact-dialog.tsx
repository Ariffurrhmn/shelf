import * as Dialog from "@radix-ui/react-dialog"
import { ArrowUpRight, Check, Download, Link2, X } from "lucide-react"
import { useRef } from "react"

import { Thumb } from "@/components/thumb"
import { useCopy } from "@/hooks/use-copy"
import { formatDate, safeHttpUrl } from "@/lib/format"
import { KIND_META, STATUS_LABEL } from "@/lib/kinds"
import { shareLabel, shareUrl } from "@/lib/url"
import type { Artifact } from "@/types"

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[7rem_1fr] gap-3 py-2.5 text-sm sm:grid-cols-[9rem_1fr]">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h3 className="mono-meta mb-2 uppercase tracking-widest">{title}</h3>
      <p className="whitespace-pre-line text-ink">{children}</p>
    </section>
  )
}

export function ArtifactDialog({ active, onClose, onCloseFocus }: { active: Artifact | null; onClose: () => void; onCloseFocus: () => void }) {
  const { copied, copy } = useCopy()
  // Keep showing the last artifact while the closing animation plays, instead of an empty panel.
  const last = useRef<Artifact | null>(null)
  if (active) last.current = active
  const artifact = active ?? last.current
  const href = typeof window === "undefined" ? "https://example.invalid/" : window.location.href
  const source = safeHttpUrl(artifact?.source)

  return (
    <Dialog.Root open={active !== null} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          className="dialog-content"
          aria-describedby={artifact ? "dialog-desc" : undefined}
          onCloseAutoFocus={(e) => {
            e.preventDefault() // Radix only restores focus to a Dialog.Trigger; ours is a card button elsewhere
            onCloseFocus()
          }}
        >
          {artifact && (
            <>
              <Dialog.Close className="btn btn-secondary btn-icon !bg-surface absolute top-3 right-3 z-10" aria-label="Close details">
                <X aria-hidden />
              </Dialog.Close>

              <div className="[&_.thumb]:rounded-none [&_.thumb]:border-0 sm:[&_.thumb]:rounded-t-[15px]">
                <Thumb artifact={artifact} sizes="(min-width: 768px) 736px, 100vw" eager />
              </div>

              <div className="p-5 sm:p-8">
                <p className="mono-meta flex flex-wrap items-center gap-x-3">
                  <span className="!text-ink">{KIND_META[artifact.kind].label}</span>
                  {artifact.status && <span>{STATUS_LABEL[artifact.status]}</span>}
                  <time dateTime={artifact.created}>{formatDate(artifact.created)}</time>
                </p>
                <Dialog.Title className="mt-2 font-display text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">{artifact.title}</Dialog.Title>
                <Dialog.Description id="dialog-desc" className="mt-3 text-lg text-muted">
                  {artifact.description}
                </Dialog.Description>

                <div className="mt-6 flex flex-wrap gap-3">
                  <a href={artifact.url} className="btn btn-primary">
                    Open artifact <ArrowUpRight aria-hidden />
                  </a>
                  <button type="button" className="btn btn-secondary" onClick={() => copy(shareUrl(artifact, href))}>
                    {copied ? <Check aria-hidden /> : <Link2 aria-hidden />} {copied ? "Copied" : "Copy link"}
                  </button>
                  {artifact.install && (
                    <a href={`${artifact.url}#install`} className="btn btn-secondary">
                      <Download aria-hidden /> Install app
                    </a>
                  )}
                </div>

                {artifact.why && <Section title="Why I made it">{artifact.why}</Section>}
                {artifact.notes && <Section title="Notes">{artifact.notes}</Section>}

                <details className="group mt-8 border-t border-line pt-4">
                  <summary className="mono-meta cursor-pointer list-none uppercase tracking-widest hover:text-ink [&::-webkit-details-marker]:hidden">
                    <span className="inline-block transition-transform group-open:rotate-90" aria-hidden>
                      ›
                    </span>{" "}
                    Technical details
                  </summary>
                  <dl className="mt-2 divide-y divide-line">
                    <Row label="Link">
                      <code className="font-mono text-[0.8125rem]">{shareLabel(artifact, href)}</code>
                    </Row>
                    <Row label="Built with">{artifact.tool}</Row>
                    <Row label="Created">{formatDate(artifact.created)}</Row>
                    {artifact.updated && <Row label="Updated">{formatDate(artifact.updated)}</Row>}
                    {artifact.tags.length > 0 && <Row label="Tags">{artifact.tags.map((t) => `#${t}`).join("  ")}</Row>}
                    <Row label="Storage">{artifact.storage === "local" ? "Saves data in this browser only" : "Saves nothing"}</Row>
                    <Row label="Network">
                      {artifact.network.length ? (
                        <span className="font-mono text-[0.8125rem]">{artifact.network.join(", ")}</span>
                      ) : (
                        "Makes no network requests"
                      )}
                    </Row>
                    <Row label="Offline app">{artifact.install ? "Installable; works offline once installed" : "Not installable"}</Row>
                    {source && (
                      <Row label="Source">
                        <a href={source} className="underline underline-offset-4 hover:text-accent" rel="noopener noreferrer">
                          {new URL(source).hostname}
                        </a>
                      </Row>
                    )}
                    <Row label="Safety">
                      Runs on this site's own address, so it shares browser storage with the other artifacts here. Network access is limited to the
                      domains listed above.
                    </Row>
                  </dl>
                </details>
              </div>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
