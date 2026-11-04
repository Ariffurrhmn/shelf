# Decisions

A running log of design decisions for Shelf, newest at the bottom. Each entry says what was decided, whether it is final or tentative, and why.

## Personal scope

- **Status:** decided
- Shelf is a personal tool for one person. It is not a platform: no accounts, no cloud storage, no moderation.
- **Why:** the goal is to keep my own artifacts in one place and open them by link. Anything beyond that adds work and risk without helping that goal.

## Static hosting

- **Status:** decided
- The gallery and the artifacts are served as static files. There is no server-side code and no database.
- **Why:** it keeps hosting simple and cheap, and a push to the repository can be the deploy.

## Ephemeral by default

- **Status:** decided
- Artifacts keep no data by default (`storage: none`). Browser storage is allowed only when an artifact declares `storage: local`, and nothing is sent to a server.
- **Why:** the repository and site are public, and an artifact should not quietly collect or leak anything.

## Tooling languages

- **Status:** decided (replaces the earlier "Python for tooling" entry)
- The validator and build script are Python 3.9+ using only the standard library, so they run anywhere with no install step. The gallery UI is React, Tailwind CSS v4 and shadcn/ui (Vite). Thumbnails use Playwright from Node.
- **Why:** the validator is the part that must be easy to run and trust, so it has no dependencies. The gallery needs a UI toolkit, and shadcn/ui was the chosen one. Playwright's Node package is the same library the browser tooling already uses, so thumbnails need no second runtime. The CLI (`shelf`) is Python for the same reason as the validator: it runs anywhere with no install step.

## Host: GitHub Pages

- **Status:** decided, easy to change
- The deploy workflow publishes `site/` to GitHub Pages from the `main` branch. The site uses only relative URLs (`base: "./"`), so it works at `<user>.github.io/shelf/`, on a custom domain, or on a subdomain of my portfolio without changes. Set the repository variable `SHELF_CNAME` to write a `CNAME` file.
- **Why:** it needs no extra account, deploys from the repository, and costs nothing. Cloudflare Pages remains an option: upload the same `site/` folder.

## Approved CDNs

- **Status:** decided
- External scripts and stylesheets may come from `cdnjs.cloudflare.com`, `cdn.jsdelivr.net`, `unpkg.com` and `code.jquery.com`, with an exact `x.y.z` version in the URL. Google Fonts is allowed without a version. Everything else is rejected.
- **Why:** a short list is easy to audit, and each of these serves immutable versioned files. Copying a library into the artifact folder is always allowed for anything not on the list.

## Metadata strictness

- **Status:** decided
- Unknown metadata fields are ignored with a warning. `network` entries are bare domains.
- **Why:** a typo should be visible without blocking a build. Bare domains are easy to compare against hosts found in the HTML.

## Personal data checks

- **Status:** decided
- Secrets and email addresses are errors, including in drafts. Phone-number-like text is a warning. Addresses at `example.com`, `example.org`, `example.net`, reserved test domains and `noreply@` are allowed.
- **Why:** the repo is public. False positives on emails are cheap to fix by using an example address; a leaked address is not.

## Thumbnails are best effort

- **Status:** decided
- The build tries to screenshot each artifact. If Playwright or a browser is unavailable, or one artifact fails to load or renders blank, the gallery shows a placeholder and the build still succeeds. See "Thumbnail pipeline" below.
- **Why:** a screenshot must never block publishing.

## Generated output is not committed

- **Status:** decided
- `site/` is ignored by git and built in CI. The gallery reads `artifacts.json` at runtime.
- **Why:** it avoids noisy diffs and merge conflicts in generated files.

## Short links

- **Status:** decided
- Every published artifact gets a short link at the site root (`<site>/<code>`), and `links.json` can add short links to any `http(s)` address. Shelf generates a redirect page per code at build time. The code is derived from the slug (4 characters, no look-alike letters) unless the artifact sets `short`. Clashes fail the build; codes are never renumbered.
- **Why:** the artifact URL (`<user>.github.io/shelf/artifacts/<slug>/`) is too long to type or put on a slide. Deriving the code from the slug needs no stored state and always gives the same answer, so a printed link cannot change by accident. Static hosting rules out server redirects, so redirect pages are the only option that keeps Shelf serverless.
- **Trade-offs:** the visitor goes through one extra page load, there are no click statistics, and the host part of the link is as long as the host (`ariffurrhmn.github.io/shelf/`). A custom domain (`SHELF_CNAME`, for example `go.example.com`) shortens it to `go.example.com/<code>`. The `url-shortener` artifact helps write `links.json` entries but cannot publish them, because Shelf has no server.
## Installable artifacts (PWA)

- **Status:** decided
- An artifact opts in with `install: true`. The build, not the author, adds a manifest, generated icons and a service worker to the served copy, and injects the tags into the served `index.html`. The source file is not changed and the validator still forbids service workers in artifact code. Each artifact is its own installable app, scoped to its folder. The gallery lists them in an "Install to your device" section; its Install button opens the artifact with `#install`, which shows a one-off install prompt.
- **Why:** it gives offline use on the room machine or phone with no server, and keeps authors out of service worker code. Injecting into the page itself (not a separate install page) is what iOS needs, because Add to Home Screen works from the page you are on.
- **Trade-offs:** the served file differs from the source by one block. Per-artifact scopes share one origin, so storage keys must be slug-prefixed. Icons are generated patterns from the slug (stdlib PNG, no Playwright), not drawn artwork. The gallery itself is not a PWA.

## Gallery redesign (Shelf 2.0)

- **Status:** decided
- Editorial layout with image-first cards; design tokens in CSS variables; Space Grotesk (headings) and Geist (body) self-hosted, latin subset; system monospace for technical metadata. shadcn/ui, Radix toggles, `class-variance-authority`, `tailwind-merge` and `tw-animate-css` were removed; only `@radix-ui/react-dialog` stays, because focus trapping and `aria-modal` are worth not re-implementing.
- **Why:** the gallery is the product. Fewer dependencies made the JS bundle smaller (about 94 KB gzip, from about 105 KB) and the markup easier to reason about for accessibility.
- **Trade-off:** no component library to pull new widgets from; each new control is written against the tokens.

## Discovery and links in the URL

- **Status:** decided
- Filters (`?q=&kind=&tag=&installable=&sort=`) live in the URL and use `replaceState`; the details dialog is `#slug` and uses `pushState`. Only theme and sort are remembered between visits; filters never are.
- **Why:** shareable, refresh-safe views and a Back button that does what people expect, without a router and with static hosting. Remembering filters would make the site open on a surprising subset of the collection.

## Featured projects

- **Status:** decided
- `featured: true` in metadata. Featured projects show above the grid only while nothing is filtered, are not repeated in the grid, and the strip is skipped when none or all are featured. Nothing is featured by default.

## Metadata v0.3

- **Status:** decided
- Added optional `featured`, `status` (`experiment` | `finished`), `why`, `updated`, `source`, `thumbnail`, `aliases`. `kind` remains the category: a second `category` field would only duplicate it. No field is required, so older artifacts load unchanged.

## Permanent links and renames

- **Status:** decided
- `aliases` keeps old `artifacts/<slug>/` addresses alive with redirect pages. `shelf rename` moves the folder, appends the alias and pins the old automatic short code as `short` (the automatic code is derived from the slug, so it would otherwise change). `shelf links --compare origin/main` runs in CI and fails when a published address or short code would disappear.
- **Trade-off:** redirect pages cost one extra request; removing an artifact on purpose needs a deliberate choice rather than happening silently.

## Artifact isolation: CSP now, separate origin later

- **Status:** decided, partial by design
- The build adds a Content-Security-Policy to each served artifact that enforces its declared `network` list. Artifacts are not embedded live in the gallery. A separate origin for untrusted artifacts is documented as the real fix and not built, because it needs a second deployment target and changes installable apps and short links. See [security.md](security.md).
- **Why:** CSP is cheap, static and actually blocks exfiltration over the network, which is the most likely harm from a bad generation. It does not stop storage or DOM access across artifacts, and the documentation says so.

## Thumbnail pipeline

- **Status:** decided
- Chromium via Playwright, pages served from a local HTTP server (not `file://`), all requests outside the local server and the artifact's approved hosts aborted. Capture waits for load, fonts and two identical frames. Blank (uniform) captures are rejected. WebP output via the browser's own canvas encoder, at 1280×800 and 640×400, named with a content hash (cache-busting for free) and cached in `.shelf-cache/thumbnails/` by a hash of the artifact's files. `thumbnail` metadata overrides the screenshot but goes through the same resize.
- **Limits:** apps that need a click, a login, a network call to an undeclared host, or a long start-up show their initial state or a placeholder; use a manual `thumbnail` for those.

## Social previews on static hosting

- **Status:** decided
- Crawlers ignore client-side meta changes, so the gallery has one high-quality site-level card, and each artifact's short-link page (plain HTML) carries its own Open Graph/Twitter tags with the thumbnail. Share short links for rich previews. The in-gallery `#slug` view cannot have its own preview.

## Artifacts live at their short address

- **Status:** decided (replaces "a redirect page per code" for artifacts)
- Each artifact is built into `site/<code>/` and served there directly; `artifacts/<slug>/` and every alias are redirects to it. Links from the gallery, the copied link and the address bar are all the short form. `links.json` entries are still redirects.
- **Why:** a redirect leaves the long address in the address bar, and a link such as `/shelf/74ng#4` should *be* the address. Static hosting cannot rewrite URLs, so the folder itself has to be the short name.
- **Trade-offs:** the code is now the folder name, so the code is part of an installed app's scope; renaming an artifact pins the old code (`short`), which `shelf rename` already did. Anyone who installed an app from the old long address would have to reinstall. `base-path + 4 characters` is as short as GitHub Pages allows; a shorter host needs `SHELF_CNAME`.

## Intentional removals: retired.json

- **Status:** decided
- The permanent-link check fails when a published address or short code disappears. `retired.json` (`{"artifacts": [...], "codes": [...]}`) lists what was removed on purpose; retiring a slug also retires its short code.
- **Why:** removing something should be a visible, reviewed decision in the diff, not a silent break and not an escape flag in CI.

## "Spec + prompt" button

- **Status:** decided
- The build writes `shelf-spec.txt` (prompt block + SPEC + METADATA) from `spec/`, and the button copies it with a clipboard write that receives a promise, so it works inside the click gesture on Safari too. `shelf prompt --full` prints the same text. Nothing is duplicated by hand, so it cannot drift.

## Wording and a quieter first screen

- **Status:** decided
- The gallery says "artifact" everywhere (the repo's own word); the hero's statistics line and the footer's count/date line were removed. Result counts (for example "3 of 4 artifacts match") stay because they are feedback for search and filters.
