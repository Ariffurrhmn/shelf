# The collection

The gallery is only as good as what is on it. This page is about curating it honestly.

## Current state

The repository ships four published sample artifacts (`pomodoro-timer`, `snake-game`, `shelf-intro-slides`, `url-shortener`) and one draft (`wip-example`). They are labelled as samples in their tags and notes. Shelf 2.0 did **not** add, remove or re-describe any of them, and nothing is marked `featured`: those choices (and any claim about how they were made) are yours.

## Recommendations (nothing here is done for you)

- **Replace samples with real work** as it exists. Delete a sample with `git rm -r artifacts/<slug>` only after checking `python shelf links --compare origin/main`; if you have shared its link, keep it by adding the slug to the `aliases` of its replacement.
- **Feature 1–3 projects**: the ones you would show a stranger first. `python shelf add … --featured`, or set `"featured": true`. More than three dilutes the strip.
- **Mark maturity honestly** with `status`: `finished` for things you use, `experiment` for things you tried. Leave it out when unsure.
- **Write the one-line description for a stranger**: what it does, not what it is built with. Put the story in `why` and `notes`; both show in the details view.
- **Keep tags few and reused.** A tag used once is not a filter. Aim for 5–15 tags across the collection; lowercase, singular (`timer`, not `Timers`). `shelf list` and the gallery's Tags panel show counts.
- **Categories (`kind`)** are `app`, `game`, `presentation`, `doc`, `other`. Prefer a real category over `other`.
- **Check the thumbnail** of each project in `python shelf preview`. Anything that needs a click to show its best state (a game in progress, a chart after loading data) should get a manual `thumbnail` image. Use a 8:5 image around 1280×800.
- **Add real creations over time**; ideas of the kind Shelf was made for: a tool you use weekly, a deck from a talk, a small game, a visualisation you made while learning something.

## Repository About and topics

Set these in the GitHub repository settings (this change does not touch repository settings; that needs your account).

**Description:** `A personal digital shelf for small HTML apps, games, slides and experiments: validated, searchable, installable and shareable as a static site. Built for AI-generated creations.`

**Website:** `https://ariffurrhmn.github.io/shelf/`

**Topics:** `personal-website`, `portfolio`, `static-site`, `github-pages`, `react`, `vite`, `tailwindcss`, `pwa`, `html`, `ai-generated`, `claude`, `creative-coding`, `digital-garden`, `link-shortener`
