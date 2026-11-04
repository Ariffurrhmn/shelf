# Security

The repository and the deployed site are both public. Anything committed here can be read by anyone, so the rules below exist to keep mistakes from becoming leaks. This page also says plainly what is **not** protected.

## Threat model

An artifact is a web page the author did not write line by line: often AI-generated, always arbitrary JavaScript. Three things can go wrong:

1. **An artifact leaks something**: a secret in its source, or visitor data sent to a server it never mentioned.
2. **An artifact misbehaves toward other artifacts or the gallery**: reads their storage, replaces their content, redirects visitors.
3. **Build tooling runs a malicious artifact**: the thumbnail step and the tests open artifact HTML in a headless browser on the CI runner.

Shelf is a personal collection with one author, so the working assumption is: *you publish only things you made or have read.* The measures below reduce what a mistake or a bad generation can do. They do not make hostile code safe.

## What is enforced

| Measure | Where | What it stops |
| --- | --- | --- |
| Secret and personal-data scan | validator | Credentials, tokens, email addresses in any artifact file (also in drafts). Pattern-based: a safety net, not a guarantee. |
| Declared storage and network | validator | `localStorage`, cookies, `fetch`… used without being declared in the metadata. |
| Pinned CDN allowlist | validator | Scripts from unknown hosts or unpinned versions. |
| Redirect and base checks | validator | `<meta http-equiv="refresh">` to another site and an external `<base href>` are errors; scripted navigation, `window.top`/`parent` access and `eval` are warnings. |
| **Content-Security-Policy per artifact** | build (`tools/build/harden.py`) | The browser refuses requests to any host not in the artifact's `network` list (fetch, XHR, WebSocket, images, media, frames, form posts). Plugins and `<base>` rewriting are off. Tested in a real browser (`e2e`). |
| Strict CSP on the gallery | build (`seo.py`) | No inline scripts, no third-party requests from the gallery page itself. |
| No third-party requests from the gallery | design | Fonts are self-hosted; no analytics. |
| Request allowlist while taking screenshots | `thumbnails.cjs` | A page being screenshotted can only reach the local server and its declared hosts; popups are closed, downloads and permissions are off. |
| Least-privilege CI | workflow | The build job has `contents: read` and no secrets; only the deploy job (main only) can publish. |
| Scan before write | `shelf add --clipboard` | Pasted HTML is parsed and validated (secrets, undeclared storage/network) before any file is created or committed. |
| Guarded write access | `ingest.yml` | The one workflow with write permission runs only for same-repo PRs by the owner, checks that only `inbox/` and `artifacts/` changed *before* running any repository code, and never executes uploaded HTML. Everything from an upload is code-formatted in its PR comment. |
| Safe CLI | `shelf add` | Slug and path traversal, overwriting without `--force`, symlinks that leave the folder, half-written artifacts (staged and moved in one step). |
| Link rendering | gallery | External `source` links render only for `http(s)` and with `rel="noopener noreferrer"`. |

## What is not protected (be aware)

- **Artifacts share one origin.** Everything is served from the same origin (`<user>.github.io`). A script in one artifact can read and overwrite another artifact's `localStorage`, IndexedDB and cookies, the gallery's theme and sort preference, and can open the gallery in a window and script it. The CSP limits *network*, not *storage or DOM access*. Slug-prefixed keys prevent accidents, not attacks.
- **Navigation is not blocked.** CSP cannot stop a script from sending the page to another site (`location = …`). The validator warns about the obvious forms; obfuscated code can avoid the pattern.
- **Direct opening is on the trusted origin.** A sandboxed iframe protects a page that *embeds* an artifact, but a visitor can always open `…/<code>/` directly, where no sandbox applies. For that reason the gallery does not embed artifacts live: it shows a static screenshot and links to the artifact.
- **Pattern scans miss things.** Secrets split across strings, encoded data, or personal information in images are not detected.
- **Declared domains are trusted.** If an artifact declares `api.example.com`, the CSP allows it, including for sending data there.
- **Screenshots execute the page** in headless Chromium on the CI runner (Playwright's default launch options, which do not enable the Chromium sandbox). The runner is ephemeral and holds no secrets, and the request allowlist limits what the page can reach, but it is not a hardened sandbox.
- **The inbox commits before it scans.** A file uploaded to `inbox/` is in a public repository the moment it is committed, even on an unmerged branch. A secret in it would be caught (and block the PR) but would already be in git history: delete the branch and rotate the key. The clipboard route has no such window.
- **Drafts are public.** `draft: true` only hides an artifact from the site; the file is in the public repository.

## Isolating untrusted artifacts properly

If Shelf ever hosts anything you did not write, the real fix is a **separate origin** for artifacts (for example a second Pages site or `artifacts.example.com`), so the browser's same-origin policy keeps them away from the gallery and from each other. That needs a second deployment target and changes how installable apps and short links resolve, so it is deliberately not part of this version. Until then, the policy is: **trusted publishing only**; run `shelf validate`, read the diff, and do not publish artifacts that ask for a `network` domain you do not recognise.

When embedding an artifact in another site (a portfolio), use `<iframe sandbox="allow-scripts" …>` and do **not** add `allow-same-origin`: that combination lets the framed page remove its own sandbox when it is same-origin with the embedder. Without `allow-same-origin` the artifact gets an opaque origin, so a `storage: local` artifact will not be able to save data inside such a frame; open those directly instead.

## Secret and personal-data scanning

The validator scans every text file in each artifact folder and fails the build when it finds:

- cloud and API credentials: AWS keys, GitHub tokens, Anthropic and OpenAI-style keys, Stripe live keys, Slack tokens, Google API keys, private key blocks, JSON web tokens;
- hard-coded assignments such as `apiKey = "..."` or `password: "..."`;
- email addresses, except `example.com`, `example.org`, `example.net`, reserved test domains and `noreply@` addresses.

Phone-number-like text produces a warning. Secrets and email addresses are errors even in drafts. `python shelf add` runs the same scan before anything is written.

## Installed apps

Service workers are added only by the build, only for artifacts with `install: true`, and each is limited to its own folder. They cache the artifact's files and approved pinned CDN files, never user data. Installed apps use the same storage as the website.

## Reporting a problem

Open an issue on the repository, or contact the owner privately for anything involving a leaked secret (and rotate the secret first).
