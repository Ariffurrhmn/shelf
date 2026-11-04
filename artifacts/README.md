# artifacts

Each artifact lives in its own folder:

```
artifacts/<slug>/index.html
```

`index.html` is the entry point. A single self-contained file is preferred. Extra local assets (images, fonts, a script) may sit in the same folder and be referenced with relative paths.

## Naming rules for `<slug>`

- Lowercase letters, digits, and hyphens only (`a-z`, `0-9`, `-`).
- Starts with a letter or digit; no leading, trailing, or doubled hyphens.
- Descriptive and short, for example `pomodoro-timer` or `kafka-intro-slides`.
- Unique within this directory. The slug becomes part of the public URL, so do not rename by hand: `python shelf rename <old> <new>` moves the folder and keeps the old address (`aliases`) and the old short link (`short`) working.

## Adding one

```bash
python shelf add my-app.html
```

See [`../docs/ai-workflow.md`](../docs/ai-workflow.md).

## What goes in a folder

- `index.html` with the metadata block described in [`../spec/METADATA.md`](../spec/METADATA.md).
- Optional local assets used by that page, and an optional cover image named in the `thumbnail` field.

Nothing outside the artifact folder may be referenced. The full rules are in [`../spec/SPEC.md`](../spec/SPEC.md).

## Drafts

Set `draft: true` in an artifact's metadata to keep it out of the build and the public site while it is still being worked on.
