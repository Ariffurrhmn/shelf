# Decisions

A running log of design decisions for Shelf, newest at the bottom. Each entry says what was decided, whether it is final or tentative, and why.

## Personal scope

- **Status:** decided
- Shelf is a personal tool for one person. It is not a platform: no accounts, no cloud storage, no moderation.
- **Why:** the goal is to keep my own artifacts in one place and open them by link. Anything beyond that adds work and risk without helping that goal.

## Static hosting

- **Status:** decided
- The gallery and the artifacts are served as static files. There is no server-side code and no database.
- **Why:** it keeps hosting simple and cheap, and a push to the repository can be the deploy. The exact host (GitHub Pages or Cloudflare Pages) is TBD.

## Python for tooling

- **Status:** tentative
- The validator and build script are planned in Python 3.11+, with Playwright for thumbnails.
- **Why:** TBD. Revisit before writing the first tool.

## Ephemeral by default

- **Status:** decided
- Artifacts keep no data by default (`storage: none`). Browser storage is allowed only when an artifact declares `storage: local`, and nothing is sent to a server.
- **Why:** the repository and site are public, and an artifact should not quietly collect or leak anything.

## License: all rights reserved

- **Status:** decided
- The source is publicly viewable for reference, but no permission is granted to copy, modify, distribute, or use it without written permission. See `LICENSE`.
- **Why:** I want to keep full ownership of this work.
