# The collection

The gallery is only as good as what is on it. This page is about curating it honestly.

## Current state

Three samples (`pomodoro-timer`, `snake-game`, `shelf-intro-slides`) and one draft (`wip-example`) came with the repository; they are labelled as samples in their tags and notes. The `url-shortener` sample was removed at the owner's request; its addresses are listed in `retired.json`.

Six artifacts were added on request, all made with Claude:

| Artifact | Where it came from | What it is |
| --- | --- | --- |
| `star-wars-watch-order` (Holocron) | Remade from the owner's own Holocron 8.0 file; its data (watch list, 135-fragment Clone Wars log, archive, extras) is kept as supplied | Chronological Star Wars tracker with episode checklists, an "up next" card and a sealed archive of what is already watched |
| `decision-wheel` | Requested by name | A weighted spin wheel; the pick is random first, the animation lands on it |
| `json-explorer` | Requested by name | Lazy tree viewer with search, path jump and exact error locations; saves nothing |
| `168-hours` | Original idea | Paint a week of 168 hourly squares, with weekly targets |
| `premortem` | Original idea | Imagine the project failed, list why, rank by likelihood x impact |
| `review-queue` | Original idea | A small spaced-repetition scheduler (1, 3, 7, 16, 35, 75, 150 day gaps) |

Nothing is marked `featured`: that choice, and any claim about how things were made, is the owner's. Three covers (`168-hours`, `premortem`, `review-queue`) are screenshots of the real tool filled with *example* data (`thumbnail.png` in each folder), because those tools start empty.

## Recommendations (nothing here is done for you)

- **Replace samples with real work** as it exists. Delete a sample with `git rm -r artifacts/<slug>`, then add its slug to `retired.json` (`"artifacts"`) so CI knows the removal is on purpose; if you have shared its link and want it to keep working, add the slug to the `aliases` of its replacement instead.
- **Feature 1–3 artifacts**: the ones you would show a stranger first. `python shelf add … --featured`, or set `"featured": true`. More than three dilutes the strip.
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
