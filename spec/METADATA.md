# Metadata fields

Every artifact carries a JSON block in its HTML `<head>` with the id `shelf-meta`. This file lists the fields it may contain. See [SPEC.md](SPEC.md) for where the block goes.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `title` | string | yes | | Display name shown in the gallery (80 characters at most). |
| `description` | string | yes | | One line describing the artifact (200 characters at most). |
| `created` | string | yes | | Creation date as `YYYY-MM-DD`. |
| `tool` | string | yes | | What built it (the AI tool or editor used). |
| `kind` | string | yes | | One of `app`, `presentation`, `doc`, `game`, `other`. |
| `tags` | list of strings | no | `[]` | Free-form labels for filtering in the gallery. |
| `storage` | string | no | `none` | `none` or `local`. `local` permits browser storage APIs, see SPEC section 4. |
| `network` | list of strings | no | `[]` | Domains the artifact is allowed to contact, see SPEC section 5. |
| `draft` | boolean | no | `false` | If `true`, the artifact is excluded from the build and the public site. |
| `notes` | string | no | | What it does, and what I would change. |
| `short` | string | no | automatic | Your own short-link code, for example `kafka` gives `<site>/kafka`. 2 to 32 characters: lowercase letters, digits and single hyphens, starting and ending with a letter or digit. `artifacts`, `assets`, `thumbnails`, `index` and `404` are reserved. Without it Shelf assigns a stable 4-character code. See [Short links](#short-links). |
| `install` | boolean | no | `false` | If `true`, the build makes the artifact installable as a PWA that works offline, see SPEC section 10. |
| `color` | string | no | from slug | Hex colour such as `#d64933`: theme colour and icon background of the installed app. Only used with `install`. |

## Notes

- Unknown fields are ignored with a warning, so a typo such as `tgas` is visible but does not break the build.
- `description` is a single line, no line breaks.
- `network` entries are bare domains (for example the host part of a URL), not full URLs. Entries with a scheme, path or port are rejected.
- `kind: presentation` triggers the extra rules in SPEC section 8.

## Short links

Every published artifact gets a short link, `https://<site>/<code>`, that redirects to it.

- **Automatic code:** 4 characters taken from a hash of the slug, using letters and digits without look-alikes (no `i`, `l`, `o`, `0`, `1`). The same slug always gives the same code, with no stored state. Renaming the slug changes the code.
- **Your own code:** set `short` in the metadata when you want something you can say aloud, such as `kafka`. It then stays whatever the slug does.
- **Clashes:** two artifacts, or an artifact and a `links.json` entry, cannot share a code. The build fails and names both. Codes are never renumbered silently, so a link printed on a slide keeps working.
- **Drafts** get no short link.
- **Any other address:** `links.json` at the repository root maps a code to an `http://` or `https://` URL, for example `{"repo": "https://github.com/ariffurrhmn/shelf"}`. Those links are published the same way.

Print the link before you publish with `python tools/build/shortlinks.py <slug>`.
