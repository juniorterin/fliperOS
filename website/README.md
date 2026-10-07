# FliperOS website

The official FliperOS landing page: a single page in Next.js (App Router, server-rendered and statically prerendered), Tailwind CSS 4 and Lucide icons, in English and Brazilian Portuguese.

## Commands

```bash
cd website
npm ci              # install
npm run dev         # http://localhost:3000, with hot reload
npm run build       # production build (standalone server in .next/standalone)
npm start           # serve the production build
npm run typecheck   # TypeScript only
npm run i18n:check  # fails if a component has visible text outside src/i18n
```

## Deploying on Coolify

- **Build pack:** Dockerfile. **Base directory:** `/website`. **Port:** 3000.
- **Environment:** `NEXT_PUBLIC_SITE_URL=https://your-domain` (available at build time). It sets the canonical URL, Open Graph URLs, `sitemap.xml` and `robots.txt`; without it they point to `http://localhost:3000`.

The image (`Dockerfile`) builds with `npm ci && npm run build` and runs `node server.js` from the standalone output as a non-root user.

## Structure

| Path | What it is |
| --- | --- |
| `src/app` | Layout with SEO metadata and JSON-LD, the page, `sitemap.ts`, `robots.ts`, the favicon (`icon.svg`) and the Open Graph card (`opengraph-image.tsx`) |
| `src/sections` | One component per section: Hero, BadgeBar, Features, Screenshots, Emulators, Crt, Setup, OpenSource, Footer |
| `src/components` | Header (active section, mobile menu), language switch, CRT frame, reveal animation, logo |
| `src/i18n` | `en-US.ts` (source of truth for the shape), `pt-BR.ts` (typed against it), the provider |
| `src/lib` | Links, GitHub stats, screenshot lookup |
| `public/screenshots` | Real screenshots; see its README for the expected file names |

## Languages

On the first visit the language comes from `navigator.language`: any `pt` variant opens in Portuguese, anything else in English. The `EN | PT` switch in the header overrides it and is saved in `localStorage` (`fliperos-lang`); switching doesn't reload the page. The server renders English, which is what crawlers index. Every visible string lives in `src/i18n`; TypeScript rejects a `pt-BR.ts` that is missing a key.

## Screenshots

Only real FliperOS captures. Drop `setup.webp`, `install.webp`, `video.webp`, `attract-mode.webp`, `es-de.webp`, `desktop.webp`, `crt.webp` or `hero.webp` into `public/screenshots` (AVIF, PNG and JPG also work) and rebuild: the matching placeholder becomes the image, with a lightbox.

## GitHub stats

Stars, forks and the latest release come from the public GitHub API, refreshed hourly (ISR). If the API fails or is rate-limited, the stats are simply not shown and the rest of the page is unaffected.
