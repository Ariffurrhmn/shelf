/** "2026-10-20" -> "20 Oct 2026". Falls back to the raw text for anything that is not a real date. */
export function formatDate(iso: string, locale?: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (!m) return iso
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]))
  if (Number.isNaN(d.getTime()) || d.getUTCMonth() !== +m[2] - 1) return iso
  return new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(d)
}

/** Only http(s) links are rendered as links, whatever the manifest says. */
export function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const u = new URL(value)
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : null
  } catch {
    return null
  }
}

/** A stable hue (0-359) from a slug, for placeholder artwork. */
export function hueFromSlug(slug: string): number {
  let h = 2166136261
  for (let i = 0; i < slug.length; i++) {
    h ^= slug.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return (h >>> 0) % 360
}

export function plural(n: number, one: string, many = one + "s"): string {
  return `${n} ${n === 1 ? one : many}`
}
