# Deployment

The site is live at <https://ariffurrhmn.github.io/shelf/>. A push to `main` validates, builds and publishes it to GitHub Pages. Pushes to other branches and pull requests run the same checks but do not publish.

## One-time setup

1. In the GitHub repository, open **Settings → Pages** and set **Source** to **GitHub Actions**.
2. Merge to `main`. The `Validate, build and deploy` workflow publishes the site. Its URL appears in the workflow summary, usually `https://<user>.github.io/shelf/`.
3. Optional, for a custom domain or a subdomain of the portfolio: add a repository variable `SHELF_CNAME` (for example `shelf.example.com`), create the matching DNS record, and set the domain under **Settings → Pages**.

## What the workflow does

1. Runs the validator and build unit tests.
2. Installs the Playwright Chromium browser for thumbnails.
3. Runs `python tools/build/build.py --install`, which validates every artifact and fails the run on any error.
4. On `main`, uploads `site/` and deploys it.

## Building locally

```bash
cd gallery && npm ci && cd ..                 # once
python tools/validate/shelf_validate.py       # validate only
python tools/build/build.py --no-thumbnails   # build into site/
python -m http.server 8000 --directory site   # preview at http://localhost:8000
```

For thumbnails locally, run `npm ci` in `tools/build` and `npx playwright install chromium`. Set `SHELF_CHROMIUM` to use an existing Chromium binary.

## Installable apps

Artifacts with `install: true` need HTTPS (GitHub Pages and most hosts provide it; `localhost` also counts). After the first deploy, check each one on the live URL: open `artifacts/<slug>/#install`, install it, switch the network off and reopen it. GitHub Pages cannot set custom headers, so the service worker is registered with the default scope of its own folder, which is all the build needs.

## Another host

`site/` is plain static files with relative URLs. Upload it to Cloudflare Pages, Netlify or any web server. No server code is needed.
