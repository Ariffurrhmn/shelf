# Shelf gallery

The gallery UI: Vite, React, Tailwind CSS v4 and shadcn/ui components (`src/components/ui`). It reads `artifacts.json` at runtime and builds into `../site`.

```bash
npm ci
npm run dev      # needs gallery/public/artifacts.json; run tools/build/build.py once to create it
npm run build    # type-checks, then builds into ../site
```

`tools/build/build.py` runs this build for you. `components.json` is set up for the shadcn CLI, so `npx shadcn@latest add <component>` works.
