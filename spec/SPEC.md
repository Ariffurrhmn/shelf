# Shelf artifact spec (v0)

This is the set of rules an artifact must follow to be accepted by Shelf. The validator (`tools/validate/shelf_validate.py`) checks these rules and fails with readable errors. Fields referenced here are defined in [METADATA.md](METADATA.md).

The words MUST, MUST NOT, and SHOULD are used in their usual sense: MUST rules fail validation, SHOULD rules are preferences.

## 1. Layout

- An artifact is a folder `artifacts/<slug>/`.
- The entry point is `artifacts/<slug>/index.html`. It MUST exist.
- A single self-contained file is preferred.
- Extra local assets (images, fonts, scripts, stylesheets) MAY live in the same folder and MUST be referenced by relative path. Nothing outside the artifact folder may be referenced.
- `<slug>` follows the naming rules in [`../artifacts/README.md`](../artifacts/README.md).

## 2. Dependencies

- No build step. The files in the folder are what gets served, with one exception: for artifacts that set `install: true`, the site build adds PWA files and tags to the served copy (section 10). The source folder is never changed.
- External scripts and stylesheets MUST come from a CDN with the exact version in the URL. `latest`, version ranges, and unversioned URLs are not allowed.
- Remote images are not allowed unless their domains are declared in the `network` field of the metadata.
- Approved CDN hosts: `cdnjs.cloudflare.com`, `cdn.jsdelivr.net`, `unpkg.com`, `code.jquery.com`. Their URLs MUST contain an exact `x.y.z` version.
- Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) are also allowed; their URLs are not versioned.
- Any other host is rejected. Inline the code, or copy the file into the artifact folder.
- Remote images are checked in HTML (`img`, `source`, `video`, `audio`, `iframe`) and in CSS (`url()`, `@import`).

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
- Unless the metadata declares `storage: local`, the artifact MUST NOT use `localStorage`, `sessionStorage`, IndexedDB, cookies, or service workers. Artifacts never register their own service worker, even with `storage: local`; the build adds one for installable artifacts (section 10).
- With `storage: local`, those APIs may be used, and the data stays in the visitor's own browser.
- All artifacts are served from one origin, so they share browser storage. Prefix every key with the slug, for example `pomodoro-timer:settings`, so artifacts do not overwrite each other's data.
- Nothing is ever sent to a server.

## 5. Network

- The artifact MUST NOT make network requests (fetch, XHR, WebSocket, beacons, form posts to external hosts) unless the metadata lists the allowed domains in `network`.
- Loading pinned CDN scripts (section 2) is separate from runtime requests, but the CDN host SHOULD still be listed in `network` so the artifact's external reach is visible in one place. The validator reports a warning when it is not.
- `network` entries are bare domains such as `api.example.com`: no scheme, path or port.

## 6. Secrets and personal data

- No API keys, tokens, passwords, or other credentials anywhere in the artifact, including comments and example data.
- No personal data (real names, email addresses, phone numbers, addresses, private documents) unless it is deliberately public and the artifact is not a draft.
- The validator fails on credentials and on email addresses (except `example.com`, `example.org`, `example.net`, reserved test TLDs and `noreply@`), and warns on phone-number-like text. It scans every text file in the folder.
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
- The validator still checks drafts: most problems are reported as warnings, but metadata errors, secrets and personal data stay errors, because drafts are public in the repository.
- Drafts still live in the repository, so they are still public on GitHub. Do not put anything in a draft that must stay private.

## 10. Installable artifacts (PWA)

An artifact can be installed on a desktop or phone and keep working offline. It is opt-in.

- Set `"install": true` in the metadata. Optionally set `"color"` (a hex colour such as `"#d64933"`) for the app's theme colour and icon background. The default is a colour derived from the slug.
- The build, not the author, adds: `manifest.webmanifest`, `icon-192.png`, `icon-512.png` and `sw.js` in the served folder, and a block before `</head>` in the served `index.html` that links the manifest, registers the service worker and shows an install prompt when the URL ends in `#install`. These file names are reserved: an installable artifact MUST NOT contain them.
- The artifact MUST NOT link its own web app manifest or register its own service worker. The build stops if it finds a manifest link.
- Everything in the folder is cached when the app is installed, so all assets MUST be local files or approved pinned CDN files. Approved CDN and font responses are cached the first time they load. Requests to any other domain in `network` need a connection, and the validator warns about them.
- Each installed app is scoped to its own folder and updates when its files change (the cache name carries a content hash). A new version takes effect after the app is closed and opened again.

## Versioning

This is spec v0.2 (adds section 10). The validator now enforces it, so rule changes should change the validator and its tests in the same commit. Changes are recorded in the git history of this file.
