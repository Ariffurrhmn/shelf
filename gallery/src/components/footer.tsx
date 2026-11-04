import { formatDate } from "@/lib/format"

export function Footer({ count, generated, repo }: { count?: number; generated?: string; repo?: string }) {
  const day = generated?.slice(0, 10)
  return (
    <footer className="border-t border-line">
      <div className="wrap flex flex-col gap-2 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
        <p>
          <span className="font-display font-semibold text-ink">Shelf</span> — a personal shelf for small things, kept in one place.
        </p>
        <p className="mono-meta">
          {count !== undefined && `${count} ${count === 1 ? "project" : "projects"}`}
          {day && /^\d{4}-\d{2}-\d{2}$/.test(day) && ` · built ${formatDate(day)}`}
          {repo && (
            <>
              {" · "}
              <a className="underline underline-offset-4 hover:text-ink" href={repo} rel="noopener noreferrer">
                source
              </a>
            </>
          )}
        </p>
      </div>
    </footer>
  )
}
