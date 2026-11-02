# Shelf artifact spec (v0)

This is the set of rules an artifact must follow to be accepted by Shelf. The validator (planned, not yet written) will check these rules and fail with readable errors. Fields referenced here are defined in [METADATA.md](METADATA.md).

The words MUST, MUST NOT, and SHOULD are used in their usual sense: MUST rules fail validation, SHOULD rules are preferences.

## 1. Layout

- An artifact is a folder `artifacts/<slug>/`.
- The entry point is `artifacts/<slug>/index.html`. It MUST exist.
- A single self-contained file is preferred.
- Extra local assets (images, fonts, scripts, stylesheets) MAY live in the same folder and MUST be referenced by relative path. Nothing outside the artifact folder may be referenced.
- `<slug>` follows the naming rules in [`../artifacts/README.md`](../artifacts/README.md).

## 2. Dependencies

- No build step. The files in the folder are exactly what gets served.
- External scripts and stylesheets MUST come from a CDN with the exact version in the URL. `latest`, version ranges, and unversioned URLs are not allowed.
- Remote images are not allowed unless their domains are declared in the `network` field of the metadata.
- Which CDN hosts are acceptable is TBD and will be decided together with the validator.

## 3. Metadata

- The page MUST contain a JSON block in the HTML `<head>` with the id `shelf-meta`.
- The fields, their types, and which are required are defined in [METADATA.md](METADATA.md).
- Example of the block, with placeholder values:

```html
<script type="application/json" id="shelf-meta">
{
  "title": "Example artifact",
  "description": "One line describing what it does.",
  "created": "2000-01-01",
  "tool": "TBD",
  "kind": "app"
}
</script>
```

## 4. Storage

- The default is `storage: none`.
- Unless the metadata declares `storage: local`, the artifact MUST NOT use `localStorage`, `sessionStorage`, IndexedDB, cookies, or service workers.
- With `storage: local`, those APIs may be used, and the data stays in the visitor's own browser.
- Nothing is ever sent to a server.

## 5. Network

- The artifact MUST NOT make network requests (fetch, XHR, WebSocket, beacons, form posts to external hosts) unless the metadata lists the allowed domains in `network`.
- Loading pinned CDN scripts (section 2) is separate from runtime requests, but the CDN host SHOULD still be listed in `network` so the artifact's external reach is visible in one place.

## 6. Secrets and personal data

- No API keys, tokens, passwords, or other credentials anywhere in the artifact, including comments and example data.
- No personal data (real names, email addresses, phone numbers, addresses, private documents) unless it is deliberately public and the artifact is not a draft.
- The repository and the deployed site are public. See [`../docs/security.md`](../docs/security.md).

## 7. Required HTML

- The `<html>` element MUST have a `lang` attribute.
- A viewport meta tag MUST be present.
- A non-empty `<title>` MUST be present.
- The layout MUST be responsive down to phone width, with no horizontal scrolling at a narrow viewport.

## 8. Presentations

An artifact with `kind: presentation` MUST also:

- Navigate with the arrow keys and the space bar.
- Toggle fullscreen with `F`.
- Include print CSS that outputs one slide per page.
- Work without a network connection, apart from pinned CDN dependencies.

## 9. Drafts

- `draft: true` in the metadata excludes the artifact from the build and from the public site.
- Drafts still live in the repository, so they are still public on GitHub. Do not put anything in a draft that must stay private.

## Versioning

This is spec v0. It will change while the validator is being designed. Changes are recorded in the git history of this file.
