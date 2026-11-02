# Metadata fields

Every artifact carries a JSON block in its HTML `<head>` with the id `shelf-meta`. This file lists the fields it may contain. See [SPEC.md](SPEC.md) for where the block goes.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `title` | string | yes | | Display name shown in the gallery. |
| `description` | string | yes | | One line describing the artifact. |
| `created` | string | yes | | Creation date as `YYYY-MM-DD`. |
| `tool` | string | yes | | What built it (the AI tool or editor used). |
| `kind` | string | yes | | One of `app`, `presentation`, `doc`, `game`, `other`. |
| `tags` | list of strings | no | `[]` | Free-form labels for filtering in the gallery. |
| `storage` | string | no | `none` | `none` or `local`. `local` permits browser storage APIs, see SPEC section 4. |
| `network` | list of strings | no | `[]` | Domains the artifact is allowed to contact, see SPEC section 5. |
| `draft` | boolean | no | `false` | If `true`, the artifact is excluded from the build and the public site. |
| `notes` | string | no | | What it does, and what I would change. |

## Notes

- Unknown fields are TBD: whether the validator rejects or ignores them has not been decided.
- `description` is a single line, no line breaks.
- `network` entries are bare domains (for example the host part of a URL), not full URLs. The exact format will be fixed together with the validator.
- `kind: presentation` triggers the extra rules in SPEC section 8.
