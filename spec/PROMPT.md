# Paste-in prompt

Give this to an AI assistant (Claude, ChatGPT, anything) before asking it to build an artifact, so the file it writes is ready for `shelf add`. Print it with `./shelf prompt`. It is a condensed version of [SPEC.md](SPEC.md); if the two disagree, the spec wins. A test checks that it mentions every metadata field, so it cannot silently fall behind.

````text
You are building one artifact for my personal gallery, Shelf. Follow these rules exactly.

OUTPUT
- Reply with ONE complete file: index.html. No other files unless I ask. No build step, no npm, no bundler.
- Everything inline (HTML, CSS, JS) in that single file. It is served from a static web server inside its own folder, so use only relative URLs for any local file, never absolute paths like /logo.png.

METADATA
- In <head>, include a JSON block: <script type="application/json" id="shelf-meta"> ... </script>
- Required fields: title (80 chars max), description (ONE line, 200 chars max), created (YYYY-MM-DD), tool (what built this, e.g. Claude), kind (app | presentation | doc | game | other).
- Optional fields (leave out anything you are not sure about, do not invent values):
  - tags: list of short lowercase labels.
  - status: "experiment" or "finished".
  - why: one or two sentences on why I made it (only if I told you).
  - notes: what it does in more detail, and what I would change.
  - storage: "none" (default) or "local".
  - network: list of bare domains such as api.example.com (no https://, no path). Default empty.
  - featured: true/false. Leave it out; I decide that myself.
  - draft: true/false (true keeps it off the public site).
  - updated: YYYY-MM-DD of the last meaningful change, only when you revise an existing artifact.
  - source: an https:// link to the conversation or repository it came from, only if I give you one.
  - thumbnail: file name of a cover image in the same folder. Leave it out; Shelf takes a screenshot.
  - aliases: earlier slugs of this artifact. Leave it out; the shelf CLI manages it.
  - short: a memorable short-link code (2-32 chars: lowercase letters, digits, single hyphens). Leave it out unless I ask.
  - install: true/false (default false). Ask me if it should be installable as an offline app. If true, keep every asset local or on a pinned CDN and prefix any storage keys with the slug.
  - color: hex such as #3563e9, only together with install.
- If I haven't given you a value for a required field, ASK ME before writing the file. Do not guess the date or the tool.

HTML
- <html> has a lang attribute. Include <meta name="viewport" content="width=device-width, initial-scale=1"> and a non-empty <title>.
- Responsive layout that works from 320px wide up, with no horizontal scrolling. Touch targets at least 44px. Respect prefers-color-scheme and prefers-reduced-motion where practical.
- Make it usable with a keyboard and with visible focus styles; give buttons and inputs labels.

DEPENDENCIES
- Prefer no external dependencies.
- If you must use a library, load it from one of these CDNs with the EXACT version (x.y.z) in the URL: cdnjs.cloudflare.com, cdn.jsdelivr.net, unpkg.com, code.jquery.com. Never "latest", never a version range, never another host. Google Fonts is also allowed.
- List every CDN host you use in "network", and tell me which libraries you used and why.
- No remote images unless their domains are listed in "network". Prefer inline SVG or CSS.

STORAGE AND NETWORK (declare them honestly: Shelf enforces what you declare)
- Default storage is "none": do not use localStorage, sessionStorage, IndexedDB, cookies, or service workers. Only use them if you set storage to "local" in the metadata, and then prefix every key with the slug, for example pomodoro-timer:settings.
- Make no network requests (fetch, XHR, WebSocket, beacons, form posts, remote images) unless the domains are listed in "network". Send nothing to any server. The published page blocks undeclared requests with a Content-Security-Policy, so an undeclared request simply fails.
- Never redirect the page elsewhere, never touch window.top or window.parent, never use eval or new Function.

SECRETS
- No API keys, tokens, passwords, or personal data anywhere, including comments and sample data. If the app needs a key, make the user paste it at runtime and keep it in memory only. Use example.com for any sample email address.

PRESENTATIONS (kind = presentation)
- Arrow keys and space navigate slides. F toggles fullscreen.
- Print CSS outputs one slide per page: an @media print block with break-after: page on each slide.
- Handle the keys in a keydown listener (ArrowLeft, ArrowRight, space, f/F) and use element.requestFullscreen() for fullscreen.
- Must work offline apart from pinned CDN dependencies.

SELF-CHECK
- Before replying, check your file against every rule above.
- After the file, add a short checklist of the rules with pass/fail, and say plainly if anything fails or you were unsure.
````

## After the AI replies

```bash
python shelf add --clipboard     # copy the code block (or the whole reply), then run this
python shelf preview <slug>      # look at it in the real gallery
```

No computer handy? Paste the HTML into a new `inbox/anything.html` on GitHub in a pull request; see [`../inbox/README.md`](../inbox/README.md).
