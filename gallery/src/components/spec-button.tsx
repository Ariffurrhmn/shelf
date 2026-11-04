import { Check, ClipboardCopy } from "lucide-react"

import { useCopy } from "@/hooks/use-copy"

/**
 * Copies everything an AI assistant needs to make an artifact that Shelf accepts: the prompt, the
 * full spec and the metadata reference. The text is built from spec/ at deploy time (shelf-spec.txt).
 */
export function SpecButton({ className }: { className: string }) {
  const { copied, copyLoaded } = useCopy("Spec and prompt copied to clipboard")

  const load = async () => {
    const r = await fetch("shelf-spec.txt", { cache: "no-cache" })
    if (!r.ok) throw new Error(`shelf-spec.txt returned ${r.status}`)
    return r.text()
  }

  return (
    <button
      type="button"
      className={className}
      onClick={() => copyLoaded(load, () => window.open("shelf-spec.txt", "_blank", "noopener"))}
      title="Copy the Shelf spec and AI prompt to paste into Claude, ChatGPT or any assistant"
    >
      {copied ? <Check aria-hidden /> : <ClipboardCopy aria-hidden />} {copied ? "Copied" : "Spec + prompt"}
    </button>
  )
}
