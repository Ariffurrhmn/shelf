import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// base "./" keeps every asset URL relative, so the site works from any
// subdomain or sub-path (GitHub Pages project sites, Cloudflare Pages, a
// portfolio subdomain) without configuration.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  build: { outDir: "../site", emptyOutDir: true },
})
