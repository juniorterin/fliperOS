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
- **Domain:** [fliperos.juniorter.in](https://fliperos.juniorter.in). The canonical URL, `hreflang`, Open Graph URLs, `sitemap.xml` and `robots.txt` use it; `NEXT_PUBLIC_SITE_URL` (available at build time) overrides it for another environment.

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

Each language has its own URL, rendered on the server and prerendered at build time: `/en` and `/pt`, each with its own `<html lang>`, title, description, keywords, canonical, `hreflang` alternates (plus `x-default` pointing to `/`), Open Graph/Twitter card (`/en/opengraph-image/card`, `/pt/opengraph-image/card`) and JSON-LD. The root `/` is a 307 redirect chosen in `src/proxy.ts`: the `fliperos-lang` cookie written by the `EN | PT` switch wins, then `Accept-Language` (any `pt` variant opens in Portuguese, anything else in English; crawlers without the header get English). The switch is a plain link between the two pages, so crawlers follow it too. Any other path is the bilingual 404 in `src/app/global-not-found.tsx`. `sitemap.xml` lists both pages with their alternates. Every visible string lives in `src/i18n`; TypeScript rejects a `pt-BR.ts` that is missing a key.

## Screenshots

Only real FliperOS captures. Drop `setup.webp`, `install.webp`, `video.webp`, `attract-mode.webp`, `es-de.webp`, `desktop.webp`, `crt.webp` or `hero.webp` into `public/screenshots` (AVIF, PNG and JPG also work) and rebuild: the matching placeholder becomes the image, with a lightbox.

## GitHub stats

Stars, forks and the latest release come from the public GitHub API, refreshed hourly (ISR). If the API fails or is rate-limited, the stats are simply not shown and the rest of the page is unaffected.
