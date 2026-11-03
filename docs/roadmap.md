# Roadmap

The short version is in the README. This file tracks detail.

## Done

- [x] Spec v0 and the paste-in prompt
- [x] Validator: layout, metadata, HTML basics, pinned CDNs, storage, network, secrets and personal data, presentation rules, drafts (40 tests)
- [x] Build script: validate, gallery, copy, thumbnails, manifest
- [x] Gallery UI with search, kind and tag filters, details dialog, dark mode
- [x] GitHub Pages workflow
- [x] Three sample artifacts and one draft
- [x] Installable artifacts (PWA): `install: true`, offline service worker, generated icons, install panel on each gallery card

## Next

- [ ] Turn on GitHub Pages (Settings → Pages → GitHub Actions) and merge to `main`
- [ ] Replace the sample artifacts with 8 to 12 real ones, each with a short note
- [ ] Choose the final subdomain and set `SHELF_CNAME`
- [ ] Generate `spec/PROMPT.md` from the spec so they cannot drift
- [ ] Add a sandboxed-iframe snippet for the portfolio embed, once permissions are decided
- [ ] After the first deploy, install each sample on a real iPhone and Android phone and on desktop Chrome and Safari, and confirm GitHub Pages serves `.webmanifest` correctly

## Later, only if used

- [ ] Make the gallery itself installable (a separate service worker for the whole shelf)
- [ ] Let an artifact supply its own icon instead of the generated one
- [ ] Publish CLI that saves a pasted file as a new artifact
- [ ] Offline copies of pinned libraries inside an artifact, for conference use
- [ ] Per-artifact `og:image` pages for nicer link previews
