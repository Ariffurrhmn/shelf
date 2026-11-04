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
| `featured` | boolean | no | `false` | Shows the artifact in the gallery's Featured strip. Nothing is featured unless you set this. |
| `status` | string | no | | `experiment` or `finished`. Shown on cards when set. |
| `why` | string | no | | Why it was made, 400 characters at most. Shown in the details view. |
| `updated` | string | no | | Date of the last meaningful change as `YYYY-MM-DD`; not before `created`. |
| `source` | string | no | | `http(s)` link to the conversation or repository it came from. |
| `thumbnail` | string | no | screenshot | A plain file name in the artifact folder (`.png`, `.jpg`, `.jpeg`, `.webp`, 2 MB at most) used instead of the automatic screenshot. It is resized to the same 8:5 format. |
| `aliases` | list of strings | no | `[]` | Earlier slugs. `artifacts/<old>/` keeps redirecting to this artifact's short address. `shelf rename` maintains it. |

## Example

```json
{
  "title": "Focus Timer",
  "description": "A 25-minute focus timer with a soft chime.",
  "created": "2026-10-20",
  "updated": "2026-11-02",
  "tool": "Claude",
  "kind": "app",
  "status": "finished",
  "tags": ["productivity", "timer"],
  "why": "I kept losing track of my breaks.",
  "notes": "Sample note. I would add a session counter.",
  "storage": "local",
  "network": [],
  "install": true,
  "featured": true,
  "source": "https://claude.ai/chat/example",
  "thumbnail": "cover.png",
  "aliases": ["pomodoro"]
}
```

Only the five required fields matter for an artifact to be accepted; every other field can be left out.

## Notes

- Unknown fields are ignored with a warning, so a typo such as `tgas` is visible but does not break the build. They are not copied to the gallery.
- Dates are strict `YYYY-MM-DD` (zero-padded) so they sort correctly as text; `2026-1-2` is rejected.
- `kind` is the category shown in the gallery; there is no separate category field.
- `description` is a single line, no line breaks.
- `network` entries are bare domains (for example the host part of a URL), not full URLs. Entries with a scheme, path or port are rejected.
- `kind: presentation` triggers the extra rules in SPEC section 8.

## Short links

Every published artifact is served at a short address, `https://<site>/<code>`. The address bar stays short because the artifact itself lives there (it is not a redirect); the long address `artifacts/<slug>/` redirects to it. Add `#3` to link to a slide or section.

- **Automatic code:** 4 characters taken from a hash of the slug, using letters and digits without look-alikes (no `i`, `l`, `o`, `0`, `1`). The same slug always gives the same code, with no stored state. Renaming the slug changes the code.
- **Your own code:** set `short` in the metadata when you want something you can say aloud, such as `kafka`. It then stays whatever the slug does.
- **Clashes:** two artifacts, or an artifact and a `links.json` entry, cannot share a code. The build fails and names both. Codes are never renumbered silently, so a link printed on a slide keeps working.
- **Drafts** get no short link.
- **Any other address:** `links.json` at the repository root maps a code to an `http://` or `https://` URL, for example `{"repo": "https://github.com/ariffurrhmn/shelf"}`. Those links are published the same way.

Print the link before you publish with `python shelf links`.
