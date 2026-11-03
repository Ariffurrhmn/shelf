# Deployment

The gallery is published with GitHub Pages at <https://ariffurrhmn.github.io/shelf/>.

## How it works

- Every push to `main` runs [`.github/workflows/pages.yml`](../.github/workflows/pages.yml).
- The workflow runs `python tools/build/build.py`, which copies every non-draft artifact from `artifacts/` into `site/<slug>/` and generates `site/index.html`.
- `site/` is uploaded and deployed with the official Pages actions. Generated output is not committed.

## One-time setup

In the repository settings, open **Pages** and set **Source** to **GitHub Actions**.

## Not yet done

- The custom subdomain on the portfolio site.
- Validation and thumbnails in the build (the v0 build script does neither).
