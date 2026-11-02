# Paste-in prompt

Copy everything inside the block below into an AI session before asking it to build an artifact. It is a condensed version of [SPEC.md](SPEC.md); if the two disagree, the spec wins, so update this file when the spec changes.

````text
You are building one artifact for my personal gallery, Shelf. Follow these rules exactly.

OUTPUT
- Reply with ONE complete file: index.html. No other files unless I ask. No build step.
- Everything inline (HTML, CSS, JS) in that single file.

METADATA
- In <head>, include a JSON block: <script type="application/json" id="shelf-meta"> ... </script>
- Required fields: title, description (one line), created (YYYY-MM-DD), tool (what built this), kind (app | presentation | doc | game | other).
- Optional fields: tags (list), storage (none | local, default none), network (list of bare domains such as api.example.com, no https://, default empty), draft (true/false), notes (what it does / what I'd change).
- If I haven't given you a value for a required field, ASK ME before writing the file. Do not guess the date or the tool.

HTML
- <html> has a lang attribute. Include a viewport meta tag and a non-empty <title>.
- Layout works down to phone width with no horizontal scrolling.

DEPENDENCIES
- Prefer no external dependencies.
- If you must use a library, load it from one of these CDNs with the EXACT version (x.y.z) in the URL: cdnjs.cloudflare.com, cdn.jsdelivr.net, unpkg.com, code.jquery.com. Never "latest", never a version range, never another host. Google Fonts is also allowed.
- List every CDN host you use in "network".
- No remote images unless their domains are listed in "network".

STORAGE AND NETWORK
- Default storage is "none": do not use localStorage, sessionStorage, IndexedDB, cookies, or service workers. Only use them if you set storage to "local" in the metadata.
- Make no network requests unless the domains are listed in "network". Send nothing to any server.

SECRETS
- No API keys, tokens, passwords, or personal data anywhere, including comments and sample data. Use example.com for any sample email address.

PRESENTATIONS (kind = presentation)
- Arrow keys and space navigate slides. F toggles fullscreen.
- Print CSS outputs one slide per page: an @media print block with break-after: page on each slide.
- Handle the keys in a keydown listener (ArrowLeft, ArrowRight, space, f/F) and use element.requestFullscreen() for fullscreen.
- Must work offline apart from pinned CDN dependencies.

SELF-CHECK
- Before replying, check your file against every rule above.
- After the file, add a short checklist of the rules with pass/fail, and say plainly if anything fails or you were unsure.
````
