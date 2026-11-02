# Architecture

Shelf is a spec, a validator and a build step that turn a folder of HTML files into a static site.

```mermaid
flowchart LR
    A["artifacts/&lt;slug&gt;/index.html"] --> V["tools/validate<br/>shelf_validate.py"]
    V -- "errors" --> X["Build stops,<br/>readable messages"]
    V -- "ok" --> B["tools/build<br/>build.py"]
    G["gallery/<br/>React + shadcn/ui"] --> B
    B --> T["thumbnails.cjs<br/>Playwright"]
    B --> S["site/"]
    T --> S
    S --> D["GitHub Pages"]
```

## Pieces

| Piece | Path | Role |
| --- | --- | --- |
| Spec | `spec/` | Rules, metadata reference and the paste-in prompt. |
| Validator | `tools/validate/shelf_validate.py` | Checks one or all artifacts. Standard library only. Exit code 1 on errors. |
| Build script | `tools/build/build.py` | Validates, builds the gallery, copies non-draft artifacts, makes thumbnails, writes `artifacts.json`. |
| Thumbnails | `tools/build/thumbnails.cjs` | Screenshots each artifact to `site/thumbnails/<slug>.jpg`. Optional. |
| Gallery | `gallery/` | Vite + React + Tailwind v4 + shadcn/ui. Reads `artifacts.json`, shows search, filters and details. |
| Deploy | `.github/workflows/deploy.yml` | Tests, builds on every push, and deploys to Pages from `main`. |

## Output layout (`site/`)

```text
site/
├── index.html, assets/      gallery UI
├── artifacts.json           manifest the gallery reads
├── artifacts/<slug>/        copied artifact folders (drafts excluded)
├── thumbnails/<slug>.jpg    optional
└── .nojekyll, CNAME?
```

## Manifest (`artifacts.json`)

`{ generated, repo?, artifacts: [ { slug, title, description, created, tool, kind, tags, storage, network, notes, url, thumbnail } ] }`, sorted newest first. All URLs are relative.

## Boundaries

- Artifacts are served as they are. The gallery links to them; it does not embed them.
- The gallery needs only the manifest, so any static host works.
