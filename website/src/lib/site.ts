export const REPO_URL = 'https://github.com/juniorterin/fliperOS';

export const LINKS = {
  github: REPO_URL,
  docs: `${REPO_URL}/wiki`,
  releases: `${REPO_URL}/releases`,
  issues: `${REPO_URL}/issues`,
  instagram: 'https://www.instagram.com/juniorter.in/',
} as const;

export const AUTHOR_HANDLE = '@juniorter.in';
export const AUTHOR = { name: 'juniorterin', url: 'https://github.com/juniorterin' } as const;

export const FLIPEROS_VERSION = '0.7';

// Domínio oficial ainda não existe: canonical, Open Graph e sitemap usam
// NEXT_PUBLIC_SITE_URL, lido no build (no Coolify, variável de build).
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000').replace(/\/+$/, '');

export const SECTION_IDS = ['features', 'screenshots', 'emulators', 'crt', 'setup', 'open-source'] as const;
export type SectionId = (typeof SECTION_IDS)[number];

export const SCREENSHOT_IDS = ['setup', 'install', 'video', 'attract-mode', 'es-de', 'desktop', 'crt'] as const;
export const HERO_SCREENSHOT = 'hero';
export const SCREENSHOT_EXTENSIONS = ['avif', 'webp', 'png', 'jpg'] as const;
