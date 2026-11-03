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
- **Why:** the validator is the part that must be easy to run and trust, so it has no dependencies. The gallery needs a UI toolkit, and shadcn/ui was the chosen one. Playwright's Node package is the same library the browser tooling already uses, so thumbnails need no second runtime.

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
- The build tries to screenshot each artifact. If Playwright or a browser is unavailable, or one artifact fails to load, the gallery shows an icon placeholder and the build still succeeds.
- **Why:** a screenshot must never block publishing.

## Generated output is not committed

- **Status:** decided
- `site/` is ignored by git and built in CI. The gallery reads `artifacts.json` at runtime.
- **Why:** it avoids noisy diffs and merge conflicts in generated files.
