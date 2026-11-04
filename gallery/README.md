# Shelf gallery

The gallery UI: Vite, React 19, Tailwind CSS v4 and one Radix primitive (`@radix-ui/react-dialog`, for an accessible dialog). It reads `artifacts.json` at runtime and builds into `../site`. Fonts (Space Grotesk, Geist) are self-hosted from `@fontsource-variable`, latin subset only.

```bash
npm ci
npm run dev        # needs public/artifacts.json: run `python tools/build/build.py` once
npm run build      # type-checks, then builds into ../site
npm run typecheck
npm test           # Vitest: search, filters, sorting, URL state
node scripts/check-contrast.mjs   # WCAG 2.2 AA check of the colour tokens
```

`tools/build/build.py` runs the build for you.

## Layout

```text
src/
├── App.tsx                  page composition, "/" shortcut, loading and error states
├── components/              header, hero, featured, explore (search + filters + grid),
│                            project-card, project-dialog, thumb, footer
├── hooks/                   use-manifest, use-browse (filters in the URL, sort preference),
│                            use-details-route (dialog as a history entry), use-copy, use-theme
├── lib/                     pure logic with tests: search, filter (filter/sort/featured), url, format
└── index.css                design tokens and component classes
public/                      favicon, og.png, apple-touch-icon.png, 404.html, theme-init.js
```

## Design system

All visual decisions are CSS variables in `src/index.css`: colour roles (`--bg`, `--surface`, `--sunken`, `--ink`, `--muted`, `--accent`, `--line`), a 6 / 10 / 16 px radius scale, one motion curve (`--dur`, `--ease`, 150-200 ms), and one focus ring. Tailwind utilities map to them (`bg-surface`, `text-muted`, `border-line`). Component classes (`.btn`, `.chip`, `.field`, `.card`, `.thumb`) keep markup short. Dark mode is the `.dark` class on `<html>`, set before first paint by `public/theme-init.js`.

## Behaviour worth knowing

- **Links:** the details dialog is addressed by `#slug` and is a real history entry; old slugs listed in an artifact's `aliases` open the same dialog. Filters are `?q=&kind=&tag=&installable=1&sort=` and use `replaceState`, so they are shareable but do not fill the Back button.
- **Preferences:** theme and sort are remembered in `localStorage` (wrapped in try/catch). Filters are never remembered.
- **Featured:** shown above the grid only while nothing is filtered and only if some, but not all, artifacts set `featured`.
