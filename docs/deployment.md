# Deployment

The site is live at <https://ariffurrhmn.github.io/shelf/>. A push to `main` validates, builds and publishes it to GitHub Pages. Pushes to other branches and pull requests run the same checks but do not publish.

## One-time setup

1. In the GitHub repository, open **Settings → Pages** and set **Source** to **GitHub Actions**.
2. Merge to `main`. The `Validate, build and deploy` workflow publishes the site. Its URL appears in the workflow summary, usually `https://<user>.github.io/shelf/`.
3. Optional, for a custom domain or a subdomain of the portfolio: add a repository variable `SHELF_CNAME` (for example `shelf.example.com`), create the matching DNS record, and set the domain under **Settings → Pages**.

## Short links and the domain

Short links are `<site>/<code>`. On GitHub Pages that is `https://<user>.github.io/shelf/<code>`. Setting `SHELF_CNAME` to a short domain, say `go.example.com`, gives `https://go.example.com/<code>`, which is the shortest form Shelf can offer on static hosting.

After each build the workflow summary lists every short link. Before publishing, `python shelf links` (or `python tools/build/shortlinks.py <slug>`) prints the one an artifact will get. Set `SHELF_BASE_URL` in your shell to override the address that command prints.

## What the workflow does

The `build` job has read-only permissions and no secrets, because it opens artifact HTML in a headless browser. Only the `deploy` job (main only) can publish.

1. Python tests: validator, build, CLI (`python -m unittest discover -s tools/<x>/tests`).
2. `python shelf validate --strict`: every artifact, warnings count as errors.
3. On branches and pull requests: `python shelf links --compare origin/main` fails if a link that was public on `main` would stop working (a removed artifact, a renamed one without an alias, a lost short code).
4. Gallery: type check, Vitest, colour-contrast check.
5. Thumbnail cache restore (keyed by a hash of `artifacts/`), Playwright Chromium install.
6. `python tools/build/build.py --strict`: validates again, builds the gallery, copies artifacts, adds CSPs, renders thumbnails (only for artifacts whose files changed), writes redirects, sitemap and manifest.
7. End-to-end tests against the built site (`cd tools/build && npm run e2e`).
8. A bundle-size table in the run summary; on `main`, upload `site/` and deploy.

## Building locally

```bash
cd gallery && npm ci && cd ..                 # once
python shelf validate                         # validate only
python tools/build/build.py --no-thumbnails   # build into site/
python shelf preview                          # build if needed, then serve at http://127.0.0.1:8000/shelf/
```

`python shelf preview` serves under `/shelf/` on purpose: that is how GitHub Pages lays out a project site, so base-path bugs show up locally. Use `--base /` to serve at the root.

For thumbnails locally, run `npm ci` in `tools/build` and `npx playwright install chromium` (or set `SHELF_CHROMIUM` to an existing Chromium binary), then `python tools/build/build.py`. Rendered thumbnails are cached in `.shelf-cache/thumbnails/` by content hash; delete the folder to force a re-render.

## Installable apps

Artifacts with `install: true` need HTTPS (GitHub Pages and most hosts provide it; `localhost` also counts). After the first deploy, check each one on the live URL: open `artifacts/<slug>/#install`, install it, switch the network off and reopen it. GitHub Pages cannot set custom headers, so the service worker is registered with the default scope of its own folder, which is all the build needs.

## Another host

`site/` is plain static files with relative URLs. Upload it to Cloudflare Pages, Netlify or any web server. No server code is needed.
