# FliperOS website

The official FliperOS site in Next.js (App Router, server-rendered and statically prerendered), Tailwind CSS 4 and Lucide icons, in English and Brazilian Portuguese: a short home page and one detail page per subject.

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

## Pages

| URL | What it has |
| --- | --- |
| `/en`, `/pt` | The home: the hero with its carousel and the technical highlights, "how it works" in four steps, the highlights as a grid of tiles, what's new in the latest releases, the presentation video, a strip of screens, the features as cards that link to their page, what to know before downloading, GitHub, FAQ and support |
| `/{lang}/frontend` | The FliperOS frontend, commercial mode |
| `/{lang}/setup` | The Setup menu and the desktop |
| `/{lang}/games` | ROM filter, downloader, BIOS, scraper, network shares |
| `/{lang}/video` | CRT, 15 kHz, Switchres, latency, vertical, multi-monitor |
| `/{lang}/web-panel` | The web panel, the controller overlay for OBS, Lab mode |
| `/{lang}/emulators` | Emulators, frontends and extras |
| `/{lang}/hardware` | Requirements, LED displays, open hardware |
| `/{lang}/install` | Writing the USB stick, the boot menu, the output test, first boot, updates, Recovery Mode |
| `/{lang}/controls` | Button mapping, keyboard encoders, GunCon 2, wheel and pedals, parallel port |
| `/{lang}/cards` | AMD, NVIDIA and Intel video cards, Vulkan, what the Setup marks as unsupported |

A detail page is a short hero, then blocks with the text on one side and a screenshot or animation on the other (`pages.<slug>.rows` in `src/i18n`), then the sections that live on that subject, "All screens", the wiki page and the next page. The list of pages, the wiki page of each and which screenshots go where are in `src/lib/site.ts`.

## Structure

| Path | What it is |
| --- | --- |
| `src/app` | Layout with SEO metadata and JSON-LD, the home (`[lang]/page.tsx`), the detail pages (`[lang]/[page]/page.tsx`), `sitemap.ts`, `robots.ts`, the favicon and the Open Graph card |
| `src/sections` | One component per section: Hero, BadgeBar, HowItWorks, Highlights, WhatsNew, VideoBlock, Gallery (the strip of screens), Features, KeyFacts, PageHero, FeatureRows, PageEnd and the subject sections (WebPanel, Emulators, Crt, MultiMonitor, Setup, Requirements, Pixelcade, OpenHardware...) |
| `src/components` | Header (menu of pages, mobile menu), language switch, carousel, screen frame, grid and lightbox, reveal animation, logo |
| `src/i18n` | `en-US.ts` (source of truth for the shape), `pt-BR.ts` (typed against it), the provider |
| `src/lib` | Links, pages, GitHub stats, screenshot lookup and media |
| `public/screenshots` | Real screenshots and animations; see its README |
| `public/art` | The two isometric pixel-art rooms (a Super Punch-Out!! cabinet and a three-screen racing cabinet), made by `node tools/site-art/iso-arcade.mjs` |

A new release goes in three places of the home: `FLIPEROS_VERSION` and `RELEASES` in `src/lib/site.ts`, and its three notes in `whatsNew.notes` (both languages). `npm run build` first runs `scripts/check-media.mjs`, which fails on an empty file in `public/`.

## Languages

Each language has its own URLs, rendered on the server and prerendered at build time: `/en` and `/pt` and the same page slugs under each (`/en/video`, `/pt/video`), each with its own `<html lang>`, title, description, canonical, `hreflang` alternates, Open Graph/Twitter card and JSON-LD. The root `/` is a 307 redirect chosen in `src/proxy.ts`: the `fliperos-lang` cookie written by the `EN | PT` switch wins, then `Accept-Language` (any `pt` variant opens in Portuguese, anything else in English; crawlers without the header get English). The switch is a plain link to the same page in the other language, so crawlers follow it too. Any other path is the bilingual 404 in `src/app/global-not-found.tsx`. `sitemap.xml` lists every page in both languages with their alternates. Every visible string lives in `src/i18n`; TypeScript rejects a `pt-BR.ts` that is missing a key.

## Screenshots

Only real FliperOS captures, still or animated (animated WebP or GIF). See `public/screenshots/README.md`.

## GitHub stats

Stars, forks and the latest release come from the public GitHub API, refreshed hourly (ISR). If the API fails or is rate-limited, the stats are simply not shown and the rest of the page is unaffected.
