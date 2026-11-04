export function Logo({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true" focusable="false">
      <rect width="64" height="64" rx="14" fill="var(--accent)" />
      <rect x="14" y="14" width="8" height="30" rx="2" fill="var(--accent-ink)" />
      <rect x="26" y="20" width="8" height="24" rx="2" fill="var(--accent-ink)" opacity=".85" />
      <rect x="38" y="12" width="8" height="32" rx="2" fill="var(--accent-ink)" transform="rotate(8 42 28)" />
      <rect x="12" y="48" width="40" height="4" rx="2" fill="var(--accent-ink)" />
    </svg>
  )
}
