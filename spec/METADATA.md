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
| `install` | boolean | no | `false` | If `true`, the build makes the artifact installable as a PWA that works offline, see SPEC section 10. |
| `color` | string | no | from slug | Hex colour such as `#d64933`: theme colour and icon background of the installed app. Only used with `install`. |

## Notes

- Unknown fields are ignored with a warning, so a typo such as `tgas` is visible but does not break the build.
- `description` is a single line, no line breaks.
- `network` entries are bare domains (for example the host part of a URL), not full URLs. Entries with a scheme, path or port are rejected.
- `kind: presentation` triggers the extra rules in SPEC section 8.
