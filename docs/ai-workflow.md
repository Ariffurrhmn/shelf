# From an AI conversation to a shared link

```text
Create in Claude / ChatGPT → save the HTML → shelf add → preview → git push → share the short link
```

## 1. Ask the AI for a Shelf-ready file

Press **Spec + prompt** on the site (header or hero): it copies the prompt, the full spec and the metadata reference in one go. The same text is `python shelf prompt --full`; `python shelf prompt` prints just the short prompt. Paste it at the start of the conversation (or into the assistant's project/custom instructions so every new artifact follows them):

```bash
python shelf prompt --full   # same text as the button; pipe it to your clipboard tool
```

Then describe what you want. The assistant asks for anything it does not know (date, tool), writes one `index.html` with the metadata block, declares storage and network honestly, and finishes with a self-check list.

You can also skip the metadata block: `shelf add` will ask you for it.

## 2. Add it

Save the reply as `my-app.html`, then:

```bash
python shelf add my-app.html
```

It reads the `<title>` and description, asks for what is missing, picks a safe slug, validates, and creates `artifacts/<slug>/index.html`. Nothing is written if validation fails.

Everything can be given as flags, which is what to use in scripts:

```bash
python shelf add my-app.html --yes \
  --title "Focus Timer" --category app --tags productivity,timer --tool claude \
  --description "A 25-minute focus timer." --why "I kept losing track of my breaks."
```

| Flag | Meaning |
| --- | --- |
| `--dry-run` | Validate and show the metadata and short link; write nothing. |
| `--fix` | Add a missing `lang` attribute and viewport meta tag (the two things AI output forgets most). |
| `--storage local`, `--network a.example.com` | Declare what the page uses. Without them, the validator tells you which one is missing. |
| `--thumbnail shot.png` | Use your own image instead of an automatic screenshot. |
| `--slug`, `--auto-suffix`, `--force` | Choose the folder name; take `name-2` if the derived one is taken; replace an existing artifact (a backup goes to `.shelf-cache/backups/`). |
| `--install`, `--featured`, `--draft`, `--status experiment\|finished` | Metadata shortcuts. |

A folder works too (`python shelf add my-app/`, needs an `index.html`): local assets are copied, dotfiles are skipped and symbolic links that leave the folder are refused.

## 3. Look at it

```bash
python shelf preview my-app          # builds the site, serves it, shows your artifact's page
python shelf preview my-app --raw    # instant: serves artifacts/ as they are, no build
```

## 4. Publish and share

```bash
git add artifacts/my-app && git commit -m "Add Focus Timer" && git push
```

The workflow validates, builds and deploys `main`. The short link printed by `shelf add` is the one to share; its page carries a title, description and thumbnail for link previews.

## Renaming later

```bash
python shelf rename my-app focus-timer
```

Moves the folder, keeps `artifacts/my-app/` working (an alias) and pins the old short link so printed links do not break.

## Troubleshooting

| Message | Fix |
| --- | --- |
| `Uses localStorage but metadata does not declare "storage": "local"` | Re-run with `--storage local` if that is intended, or ask the AI to remove the storage use. |
| `Uses fetch() but metadata lists no allowed domains` | Re-run with `--network api.example.com`. Undeclared requests are blocked in the browser anyway. |
| `… must pin an exact version` | Ask the AI to pin the CDN URL (`@1.2.3`) or inline the library. |
| `The slug 'x' is already taken` | Pick another `--slug`, add `--auto-suffix`, or `--force` to replace. |
| No `<head>` section | Ask the AI for a complete HTML document. |
