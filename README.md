# Shelf

A personal shelf for small HTML apps, tools, and presentations: kept in one repo, checked against a spec, and published as a gallery I can open by link from anywhere.

> **Status:** Early stage: scaffold and spec only, nothing implemented yet.

## The problem

I make a lot of small things with AI tools: a one-page calculator, a throwaway game, a slide deck for a talk. Each one is a single HTML file that comes out of a chat window. Then it gets thrown away, or it ends up in a downloads folder, a chat history, or some tool's own preview pane. A few weeks later I can't find it, and if I need it on another machine I'm out of luck.

What I want is simple: every artifact in one place, in a consistent shape, reachable by a link.

## What Shelf is (and isn't)

Shelf is a personal artifact host and gallery. It keeps my artifacts in one repository, validates each one against a small spec, generates a gallery site with thumbnails, and deploys it as static pages. A push is a deploy.

It is just for me. It is shown on GitHub and on my portfolio site as a proof of concept that this can be built.

What it deliberately is not:

- **Not a platform.** It is one person's tool.
- **No accounts.** There is nothing to sign in to.
- **No cloud data.** Artifacts are static files. Nothing is stored on a server and nothing is collected.
- **No moderation.** I am the only author, so there is nothing to moderate.

## How it works

Shelf has five pieces:

1. **Spec:** the rules an artifact must follow.
2. **Paste-in prompt:** the spec written as a prompt I give any AI session, so new artifacts come out conformant.
3. **Validator:** a CLI that checks each artifact against the spec and fails with readable errors.
4. **Build script:** validates, takes a screenshot of each artifact for a thumbnail, and generates the gallery.
5. **Deploy:** the generated site goes to static hosting on a subdomain of my portfolio.

```
  spec/SPEC.md ──► spec/PROMPT.md ──► AI session ──► artifacts/<slug>/index.html
                                                              │
                                                              ▼
                                                       validator (CLI)
                                                              │ pass
                                                              ▼
                                               build: thumbnails + gallery
                                                              │
                                                              ▼
                                                      site/ (static pages)
                                                              │
                                                              ▼
                                            deploy on push (static hosting)
```

The validator and build script are planned. None of this is implemented yet.

## The spec in brief

The full text is in [`spec/SPEC.md`](spec/SPEC.md). In short, an artifact:

- is a folder `artifacts/<slug>/` with an `index.html` entry point, ideally one self-contained file;
- has no build step, and loads external scripts only from CDNs with an exact pinned version;
- carries a JSON metadata block in its head (fields are in [`spec/METADATA.md`](spec/METADATA.md));
- stores nothing and makes no network requests unless its metadata says so;
- contains no API keys, tokens, or personal data;
- has a `lang` attribute, a viewport meta tag, a title, and a layout that works at phone width;
- if it is a presentation, supports arrow keys and space, `F` for fullscreen, and prints one slide per page;
- can be marked `draft: true` to keep it out of the build and the public site.

## The paste-in prompt workflow

1. Open a new AI session.
2. Paste the prompt from [`spec/PROMPT.md`](spec/PROMPT.md).
3. Describe the artifact I want. The session asks me for any metadata it is missing.
4. It replies with one complete `index.html`, with the metadata block filled in and a self-check against the spec.
5. I save it as `artifacts/<slug>/index.html`, run the validator (once it exists), and push.

## Repository structure

```
artifacts/   One folder per artifact: artifacts/<slug>/index.html
spec/        The spec, the metadata reference, and the paste-in prompt
tools/       Planned validator (tools/validate) and build script (tools/build)
site/        Generated gallery output
docs/        Architecture, decisions, deployment, security, and roadmap notes
.github/     Workflows; the deploy workflow comes later
```

## Planned tech

All of this is tentative and may change:

- **Python 3.11+** for the validator and build script.
- **Playwright** for thumbnail screenshots.
- **GitHub Pages or Cloudflare Pages** for hosting, on a subdomain of my portfolio.

Decisions are logged in [`docs/decisions.md`](docs/decisions.md).

## Security and privacy

The repo and the site are public, so I treat everything in them as public.

- **Draft flag:** `draft: true` keeps an artifact out of the build and the site. It is still in the repo, so drafts are not private.
- **Secret scan:** the validator is planned to scan for secrets and personal data. Not implemented yet.
- **Sandboxed embeds:** artifacts embedded in my portfolio site should go in an iframe with the `sandbox` attribute, so a buggy artifact can't affect the host page.
- **Ephemeral by default:** artifacts keep no data and send nothing to a server unless their metadata declares it.

More in [`docs/security.md`](docs/security.md).

## The use case

I'm at a conference and I'm handed a room machine I've never used. My slides are an HTML presentation I made weeks ago. I don't want to sign in to anything or plug in a drive. I open a browser, go to the Shelf address, tap the presentation, and press `F`. Arrow keys move through the slides. The same link works from my phone if the room machine fails.

## Roadmap

- [x] Spec v0
- [ ] Validator
- [ ] Build script and thumbnails
- [ ] Deploy
- [ ] First 8-12 curated artifacts, each with a short note
- [ ] Optional, later: a publish CLI

More detail in [`docs/roadmap.md`](docs/roadmap.md).

## Getting started

Not available yet.

## License

All rights reserved. See [`LICENSE`](LICENSE).

Source is viewable for reference; reuse requires permission.
