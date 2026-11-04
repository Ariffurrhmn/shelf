# Roadmap

The short version is in the README. This file tracks detail.

## Done

- [x] Spec v0 → v0.3, the paste-in prompt, validator (65 tests), build script, Pages workflow
- [x] Short links, `links.json`, installable artifacts (PWA) with offline use
- [x] Shelf 2.0 gallery: design system, image-first cards, Explore Shelf (search, category, tags, installable, sort), featured artifacts, details dialog with history, bottom sheet on phones, dark mode, accessibility pass
- [x] Metadata v0.3 (`featured`, `status`, `why`, `updated`, `source`, `thumbnail`, `aliases`)
- [x] `shelf` CLI: add, validate, list, preview, rename, links, doctor, prompt
- [x] Thumbnails: request-allowlisted capture, settle and blank detection, manual override, WebP pairs, content-hash cache
- [x] Security: per-artifact CSP, redirect/base/navigation checks, gallery CSP, documented limits
- [x] SEO and sharing: canonical, Open Graph, Twitter cards, favicon, social image, sitemap, robots, share cards on short links, 404 page
- [x] Tests: Python (validator, build, CLI), Vitest (gallery logic), Playwright end-to-end; CI runs all of them
- [x] Permanent-link protection (`aliases`, `shelf rename`, `shelf links --compare`, `retired.json` for intentional removals)
- [x] Artifacts served at 4-character addresses (no redirect), "Spec + prompt" button, "artifact" wording, URL shortener sample removed

## Next

- [ ] Turn on GitHub Pages (Settings → Pages → GitHub Actions) if not yet done
- [ ] Replace or supplement the sample artifacts with real ones (see [collection.md](collection.md))
- [ ] Choose the final subdomain and set `SHELF_CNAME` (also makes short links shorter)
- [ ] After the first deploy, install each sample on a real iPhone and Android phone and on desktop Chrome and Safari, and confirm GitHub Pages serves `.webmanifest` correctly
- [ ] Set the repository About text and topics (suggestions in [collection.md](collection.md#repository-about-and-topics))

## Later, only if used

- [ ] A separate origin for artifacts, if Shelf ever hosts things its owner did not write (see [security.md](security.md))
- [ ] Make the gallery itself installable
- [ ] Let an artifact supply its own app icon instead of the generated one
- [ ] Offline copies of pinned libraries inside an artifact, for conference use
- [ ] A `shelf thumbnail <slug>` command to capture a manual cover image interactively
