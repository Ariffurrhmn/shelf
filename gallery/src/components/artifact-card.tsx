import { ArrowUpRight, Check, Info, Link2 } from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { KIND_META, formatDate } from "@/lib/kinds"
import { shortUrl, useCopy } from "@/lib/short-link"
import type { Artifact } from "@/types"

export function Thumb({ artifact, className = "" }: { artifact: Artifact; className?: string }) {
  const [failed, setFailed] = useState(false)
  const Icon = KIND_META[artifact.kind].icon
  const show = artifact.thumbnail && !failed
  return (
    <div className={`bg-muted relative aspect-[16/10] w-full overflow-hidden ${className}`}>
      {show ? (
        <img
          src={artifact.thumbnail!}
          alt={`Preview of ${artifact.title}`}
          loading="lazy"
          onError={() => setFailed(true)}
          className="size-full object-cover object-top"
        />
      ) : (
        <div className="from-muted to-accent text-muted-foreground flex size-full items-center justify-center bg-gradient-to-br">
          <Icon className="size-10 opacity-60" aria-hidden />
        </div>
      )}
    </div>
  )
}

export function ArtifactCard({ artifact, onDetails }: { artifact: Artifact; onDetails: (a: Artifact) => void }) {
  const { icon: Icon, label } = KIND_META[artifact.kind]
  const { copied, copy } = useCopy()
  return (
    <Card className="group gap-0 overflow-hidden py-0 transition-shadow hover:shadow-md">
      <a href={artifact.url} className="block focus-visible:ring-ring/50 outline-none focus-visible:ring-[3px]" aria-label={`Open ${artifact.title}`}>
        <Thumb artifact={artifact} className="border-b" />
      </a>
      <CardHeader className="gap-2 pt-4">
        <div className="flex items-center justify-between gap-2">
          <Badge variant="secondary">
            <Icon aria-hidden /> {label.replace(/s$/, "")}
          </Badge>
          <span className="text-muted-foreground text-xs">{formatDate(artifact.created)}</span>
        </div>
        <CardTitle className="text-lg">{artifact.title}</CardTitle>
        <CardDescription className="line-clamp-2">{artifact.description}</CardDescription>
      </CardHeader>
      <CardContent className="mt-3 flex flex-wrap gap-1.5">
        {artifact.tags.slice(0, 4).map((t) => (
          <Badge key={t} variant="outline" className="font-normal">
            {t}
          </Badge>
        ))}
      </CardContent>
      <CardFooter className="mt-auto gap-2 pt-4 pb-4">
        <Button asChild className="flex-1">
          <a href={artifact.url}>
            Open <ArrowUpRight />
          </a>
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={() => copy(shortUrl(artifact))}
          aria-label={`Copy short link for ${artifact.title}`}
          title={copied ? "Copied" : "Copy short link"}
        >
          {copied ? <Check /> : <Link2 />}
        </Button>
        <Button variant="outline" size="icon" onClick={() => onDetails(artifact)} aria-label={`Details for ${artifact.title}`}>
          <Info />
        </Button>
      </CardFooter>
    </Card>
  )
}
