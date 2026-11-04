import { ArrowDown } from "lucide-react"

import { jumpTo } from "@/components/header"
import { SpecButton } from "@/components/spec-button"

export function Hero() {
  return (
    <section className="wrap pt-12 pb-10 sm:pt-20 sm:pb-14" aria-labelledby="hero-title">
      <p className="eyebrow">A personal digital playground</p>
      <h1 id="hero-title" className="mt-4 max-w-3xl text-[clamp(2.25rem,5.5vw+0.5rem,4.25rem)] leading-[1.03] font-semibold">
        Small experiments. <span className="text-muted">Useful creations.</span>
      </h1>
      <p className="mt-5 max-w-xl text-lg text-muted">
        A growing collection of little apps, creative experiments, and interactive ideas — built, collected, and shared.
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-3">
        <a
          href="#explore"
          onClick={(e) => {
            e.preventDefault()
            jumpTo("explore")
          }}
          className="btn btn-primary"
        >
          Explore the collection <ArrowDown aria-hidden />
        </a>
        <SpecButton className="btn btn-secondary" />
      </div>
    </section>
  )
}
